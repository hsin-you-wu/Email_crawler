import argparse
import logging
import os
import re
import requests
from requests_html import HTMLSession
from tenacity import retry, stop_after_attempt, wait_fixed
import time
from urllib.parse import urljoin, urlparse

# NEW: navigation timeout: 10000
# NEW: report length of error urls
# NEW: add retry mechanisim
# NEW: add filter flag


def main(keyword, starting_page, ending_page, starting_index):

    # configure logging
    configure_logging()

    # loop through each page
    for page in range(starting_page, ending_page + 1, 1):
        process_page(page, keyword, starting_index)
        starting_index = 1


def configure_logging():
    try:
        filename = os.path.splitext(os.path.basename(__file__))[0]
        logging.basicConfig(filename=f"{filename}.log", level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s - %(message)s')
        logging.getLogger('pyppeteer').setLevel(logging.WARNING)
        logging.getLogger('websockets').setLevel(logging.WARNING)
    except Exception as e:
        logging.error(f"Failed to configure logging: {e}")


def process_page(page, keyword, starting_index):
    # APIs
        try:
            get_url = f"https://path/keyword={keyword}&page={page}" # change this to your own API
            urls = get_urls(get_url)
            sliced_urls = list(urls.keys())
            post_url = "https://path" # change this to your own API
            logging.critical(f"Starting page {page}") 
        except Exception as e:
            logging.error(f"Failed to fetch API: {e}")

        error_urls = {}

        # loop through each url
        for i, id in enumerate(sliced_urls[starting_index-1:]):
            url = urls[id]
            process_url(url, id, i, page, starting_index, post_url, error_urls)
            time.sleep(2)
            
        logging.critical(f"##################################### Finished Page {page} ####################################")
        logging.info(f"Unsuccessful urls ({len(error_urls)}):")
        for id in error_urls:
            logging.info(f'{id}: {error_urls[id]}\n')


def process_url(url, id, i, page, starting_index, post_url, error_urls):
    filtered_emails = []
    all_emails = set()
    visited_urls = set()
    logging.info(f"##################################### page {page} ({starting_index+i}) #####################################")
    logging.info(f"visiting ID: {id} ({url})")

    # scrape and filter emails
    try:
        if url:
            error_urls = scrape_websites(url, visited_urls, all_emails, error_urls, id)
            if args.f:
                hotel_name = scrape_hotel_name(url)
                filtered_emails = list(filter_emails(all_emails, hotel_name))
            else:
                filtered_emails = list(all_emails) 
            found_count = len(all_emails)
            filtered_count = len(all_emails) - len(filtered_emails)
        else:
            filtered_emails = []
            found_count = 0
            filtered_count = 0

        logging.info(f"Found: {found_count} | Filtered: {filtered_count} | Written: {len(filtered_emails)}")
        post_to_database(post_url, filtered_emails, id)

    except Exception as e:
        logging.error(f"Failed to scrape url: {e}")


def post_to_database(post_url, filtered_emails, id):
    result = {}
    result["id"] = int(id) 
    result["email_4"] = filtered_emails[0] if len(filtered_emails) > 0 else " "
    result["email_5"] = filtered_emails[1] if len(filtered_emails) > 1 else " "
    result["email_6"] = filtered_emails[2] if len(filtered_emails) > 2 else " "

    try:
        response = requests.post(post_url, json=result) 
        response.raise_for_status()
        logging.info(response.text)
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to post: {e}")


def get_urls(get_url: str) -> dict:
    "Given an API url, return a dict of 100 {id: urls}."

    urls = {}
    res = requests.get(get_url)
    if res.status_code == 200:
        data = res.json()
    for item in data:
        urls[item["id"]] = item["website"]

    return urls


def scrape_hotel_name(url: str) -> str:
    "Scrape url for hotel's english name."
    
    hostname = urlparse(url).hostname
    path = urlparse(url).path

    # edge case: owlting
    if "owlting" in hostname:
        pattern = re.compile(r'(?<=/)[^/]+')
    # normal cases
    else:
        pattern = re.compile(r'[^\.]+(?=\.com)', re.IGNORECASE)
    
    match = pattern.search(path if "owlting" in hostname else hostname)
    hotel_name = match.group(0) if match else ""

    return hotel_name


def filter_emails(all_emails, hotel_name):
    """Remove non-personal emails from the set."""

    keywords = [hotel_name, "reservation", "booking", "service", "info", "hotel", "hotels",
                "stay", "bnb", "hostel", "inn", "resort", "house", "room", "sentry", "customer",
                "feedback", "contact", "taipei", "example", "name", "residence", "guest", "villa",
                "motel", "domain", ".jp"]
    pattern = re.compile(r'(' + '|'.join(keywords) + r')', re.IGNORECASE)
    
    filtered_emails = set()
    for email in all_emails:
        if not pattern.search(email):
            filtered_emails.add(email)

    return filtered_emails


def log_before_retry(retry_state):
    logging.warning(f"Retrying {retry_state.fn} in {retry_state.next_action.sleep} seconds...")

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), before_sleep=log_before_retry)
def scrape_websites(url: str, visited_urls: set, all_emails: set, error_urls: dict, id: int) -> dict:
    """
    Scrape homepage and "contact us" page.
    """
    try:
        # create a session
        session = HTMLSession()

        # load dynamic webpage
        res = session.get(url, timeout=30)
        res.html.render(timeout=30) # problems here
        page_content = res.html.html

    except Exception as err:
        error = f"Failed to load {url}: {err}"
        logging.error(error)
        error_urls[id] = error
        session.close()
        return error_urls
    
    # go to homepage
    emails, contactUs_urls = scrape_email(url, visited_urls, page_content)
    all_emails.update(emails)

    # go to "contact" pages
    if contactUs_urls:
        count = 0
        for url in contactUs_urls:
            if count > 5:
                break
            if url not in visited_urls:
                emails_2, _ = scrape_email(url, visited_urls, page_content)
                all_emails.update(emails_2)
                count += 1
    
    # close session
    session.close()
    return error_urls
    

def scrape_email(url: str, visited_urls: set, page_content):
    """
    1. Given an url, scrape emails on that page.
    2. Find "Contact Us" page urls if any exists.
    3. Return 1. and 2. as a set.
    """
    if url in visited_urls:
        return set(), [] 
    visited_urls.add(url)
    
    # find emails
    email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?!png|jpg|jpeg|gif|bmp|svg|webp)[a-zA-Z]{2,14}"
    emails = set(re.findall(email_regex, page_content))

    # find "contact us" page urls
    contactUs_urls = set()
    contact_regex = r'(?i)<a[^>]*href=["\']([^"\']*contact[^"\']*)["\'][^>]*>|<a[^>]*href=["\']([^"\']*)["\'][^>]*>[^<]*contact(?:\s*us)?[^<]*</a>'
    matches = re.findall(contact_regex, page_content)
    for match in matches:
        for url_match in match:
            if url_match:
                contactUs_urls.add(urljoin(url, url_match))

    return emails, contactUs_urls


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("keyword", type=str)
    parser.add_argument("starting_page", type=int)
    parser.add_argument("ending_page", type=int)
    parser.add_argument("starting_index", type=int, nargs='?', default=1)
    parser.add_argument('-f', action='store_true', help='Enable filtering emails')
    args = parser.parse_args()

    main(args.keyword, args.starting_page, args.ending_page, args.starting_index)




