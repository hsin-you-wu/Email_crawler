## email_crawler.py
This is the main program that extracts emails by:
  
1. fetch website urls from database through API*.  
    *API returns 100 website urls at a time.    
    *Replace with your own API.
2. extract "contact" pages' url if there are any.  
3. extract emails from the all urls.  
4. filter emails if needed.  
5. post results back to database through API.  
    *Replace with your own API.  
    
### usage:  
```python3 email_crawler.py {keyword} {starting_page} {ending_page} {starting_index} {-f}```  
- ```{starting_index}``` is optional. It is set to 1 at default.  
- ```{-f}``` is optional. It filters service emails if called.    


#### example usage:
```python3 email_crawler5.0.py 泰國 1 3 50 -f``` :   
Extracts emails from page 1's 50th url to page 3's last url.   
It also filters out service emails.   
  
### usage:  
```python3 error.py email_crawler.log {starting_page} {ending_page} ```  
```python3  error.py email_crawler.log -r```

