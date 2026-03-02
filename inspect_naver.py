import sys
import io
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=chrome_options)
    
    # Get iframes
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    print("Found iframes count:", len(iframes))
        
    # Title input elements
    print("\n[Searching for publish buttons...]")
    for el in driver.find_elements(By.CSS_SELECTOR, "button, a, span"):
        className = el.get_attribute("class")
        text = str(el.text).strip()
        if "발행" in text:
            print(f"Tag: {el.tag_name}, Class: {className}, Text: {text}")

except Exception as e:
    print("Error:", e)
