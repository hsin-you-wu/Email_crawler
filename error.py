import argparse
import re
from collections import defaultdict

def extract_unsuccessful_urls(log_file_path):
    with open(log_file_path, 'r') as file:
        log_content = file.read()

    # Regular expression to find the relevant sections and capture page numbers
    section_pattern = re.compile(
        r'Finished Page (\d+).*?Unsuccessful urls:(.*?)Starting page \d+', 
        re.DOTALL
    )

    # Regular expression to extract IDs, URLs, and error messages
    url_pattern = re.compile(
        r'INFO - (\d+): Failed to load (https?://[^\s]+): (.+)'
    )

    unsuccessful_urls = defaultdict(list)

    # Find all sections that match the pattern
    sections = section_pattern.findall(log_content)
    for page_number, section in sections:
        # Find all URLs, IDs, and error messages in the section
        urls = url_pattern.findall(section)
        for id, url, error in urls:
            unsuccessful_urls[page_number].append((id, url, error))

    return unsuccessful_urls

if __name__ == "__main__":
    # Define CLI arguments
    parser = argparse.ArgumentParser(description='Process log file to extract unsuccessful URLs.')
    parser.add_argument('log_file', type=str, help='Path to the log file')
    parser.add_argument('start_page', type=int, nargs='?', default=None, help='Starting page number')
    parser.add_argument('end_page', type=int, nargs='?', default=None, help='Ending page number')
    parser.add_argument('-range', action='store_true', help='Show the range of pages in the log file')

    # Parse CLI arguments
    args = parser.parse_args()

    # Use the parsed log file path
    log_file_path = args.log_file
    unsuccessful_urls = extract_unsuccessful_urls(log_file_path)
    
    # Determine the range of pages
    all_pages = sorted(unsuccessful_urls.keys(), key=int)
    start_page = int(all_pages[0])
    end_page = int(all_pages[-1])

    # Show the range of pages if -range flag is specified
    if args.range:
        print(f"Containing results from page {start_page} to {end_page} (Total pages: {len(all_pages)})")
    else:
        # Determine the range of pages to display
        display_start_page = args.start_page if args.start_page is not None else start_page
        display_end_page = args.end_page if args.end_page is not None else end_page

        # Show information about the page range
        print(f"Results from page {display_start_page} to {display_end_page} (Total pages: {len(all_pages)})")

        # Print the results within the specified range
        for page_number in range(display_start_page, display_end_page + 1):
            page_str = str(page_number)
            if page_str in unsuccessful_urls:
                print(f'##################################### Page {page_str} ####################################')
                for id, url, error in unsuccessful_urls[page_str]:
                    print(f"ID: {id}")
                    print(f"URL: {url}")
                    print(f"Error: {error}")
                    print()