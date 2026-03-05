import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def run():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=options)
    
    driver.get("https://www.coupang.com/np/search?q=%ED%95%98%EA%B8%B0%EC%8A%A4+%EB%A7%A5%EC%8A%A4%EB%93%9C%EB%9D%BC%EC%9D%B4")
    time.sleep(3)
    
    # Extract list item classes
    items = driver.execute_script("""
        const listItems = Array.from(document.querySelectorAll('li'));
        return listItems.map(li => li.className).filter(c => c && c.length > 0);
    """)
    
    classes = list(set(items))
    print("LI classes found on page:")
    for c in classes:
        if 'product' in c.lower() or 'item' in c.lower() or 'search' in c.lower():
            print("  " + c)
            
    driver.quit()

if __name__ == '__main__':
    run()
