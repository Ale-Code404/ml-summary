import argparse
import functools
import os.path
import json
import re
from typing import List
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement 
from selenium.webdriver.common.by import By

class MLSummaryParser:
    def __init__(self, cookies: dict):
        # Main driver
        self._driver = None
        self._per_page = 10
        self._purchases_count = None
        self._cookies = cookies

        self._driver = self._init_webdriver()
        self._driver_main = self._driver.current_window_handle
    
    def get_pruchases(self, page: int = 1):
        purchases_urls = []
        print(f"🚀 Loading purchases, page ({page})..")
        self._driver.get(f"https://myaccount.mercadolibre.com.co/my_purchases/list?page={page}")

        page_purchases_container = self._driver.find_element(by=By.CSS_SELECTOR, value=".list-item-container")
        page_purchases = page_purchases_container.find_elements(by=By.CSS_SELECTOR, value=".list-item-grouper")

        print(f" Found {len(page_purchases)} purchases")
        
        for purchase in page_purchases:
            purchase_anchor = purchase.find_element(by=By.CSS_SELECTOR, value="a.andes-button--loud")
            purchase_url = purchase_anchor.get_attribute('href')

            purchase_status = purchase.find_element(by=By.CSS_SELECTOR, value=".list-item__intro span.bf-ui-rich-text")
            purchase_status = purchase_status.text.strip()

            purchases_urls.append({
                'url': purchase_url,
                'status': purchase_status
            })

        return purchases_urls

    def get_purchase_details(self, purshase_url):
        print(f"🚀 Loading purchase details..")
        print(f"URL: {purshase_url}")    

        # Load a new driver
        self._driver.switch_to.new_window('tab')
        self._driver.get(purshase_url)
        # Get the purchase id and date
        date_id = self._driver.find_element(by=By.CSS_SELECTOR, value=".bf-ui-ticket__subtitle > span:nth-child(1)")
        date_id_parts = date_id.text.split('|')  

        date = date_id_parts[0].strip()
        id = date_id_parts[1].strip()        

        total = self._driver.find_element(by=By.CSS_SELECTOR, value="meta[itemprop=price]").get_attribute('content')
        total = float(total.replace('.', ''))

        pay_method = self._driver.find_element(by=By.CSS_SELECTOR, value=".bf-ui-ticket-row__right-column--secondary-text > span:nth-child(2)")
        pay_method = pay_method.text.strip()
        
        details = MLPurchaseInfo(
            id=id,
            date=date,
            total=total,
            pay_method=pay_method,
            items=[]
        )

        self._driver.close()
        # Load main driver
        self._driver.switch_to.window(self._driver_main)

        return details

    def get_purchases_count(self):
        if self._purchases_count is None:
            return self._get_purchases_count()
        
        return self._purchases_count
    
    def _get_purchases_count(self):
        # Load purchases page
        self._driver.get("https://myaccount.mercadolibre.com.co/my_purchases/list")     
        purchases_text = self._driver.find_element(by=By.CSS_SELECTOR, value=".list-header__subtitle > span:nth-child(1)")

        purchases_count = re.search(r"\d+", purchases_text.text)

        if not purchases_count:
            self._purchases_count = 0
        else:
            self._purchases_count = int(purchases_count.group(0))
    
        return self._purchases_count

    def get_total_pages(self):
        is_div = self.get_purchases_count() % self._per_page == 0
        if is_div:
            return self.get_purchases_count() / self._per_page        
        
        return int(self.get_purchases_count() / self._per_page) + 1

    def _init_webdriver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("no-sandbox")
        options.add_argument("headless")
        options.add_argument("disable-gpu")
        options.add_argument("--window-size=1280,720")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)        
        # Loading dump page for add cookies
        driver.get("https://myaccount.mercadolibre.com.co/404")      
        # Add cookies
        for cookie in self._cookies:
            driver.add_cookie({
                'name': cookie["name"],
                'value': cookie["content"]
            })

        return driver

@dataclass
class MLPurchaseItem:
    name: str
    quantity: str
    value: float

@dataclass
class MLPurchaseInfo:
    id: str
    date: str
    total: str
    pay_method: str
    items: List[MLPurchaseItem]

class MLSummary: 
    def __init__(self):
        self._purchases: List[MLPurchaseInfo] = []

    def add_purchase(self, purchase: MLPurchaseInfo):
        self._purchases.append(purchase)

    def get_purchases_total(self):
        return functools.reduce(
            lambda total, purchase: total + purchase.total,
            self._purchases,
        0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cookies", required=True, help="Readeable cookie file in json or txt format")
    args = parser.parse_args()

    print("Welcome to the ML Summary\n")
    print("With this app you can summarize all your buys, get the biggest one, \nthe lowest one, and other stats.\n")

    cookies = _parse_cookies(args.cookies)
    cookies_count = len(cookies)

    print(f"Loading {cookies_count} cookies\n")

    print("🚀 Initializing web...")
    summary = MLSummary()

    parser = MLSummaryParser(cookies)
    total_pages = parser.get_total_pages()
    purchases_count = parser.get_purchases_count()
    # Empty list to store all purchases
    purchases = []
    purchases_status = {
        'pending': [],
        'received': [],
        'canceled': [],
    }

    print(f"🚀 Found ({purchases_count}) purchases\n")

    # Add 1 page to total pages for end page
    for page in range(1, total_pages + 1):
        purchases.extend(parser.get_pruchases(page))

    print("\n")

    # Group by status
    for purchase in purchases:
        if purchase['status'] == 'En camino':
            purchases_status['pending'].append(purchase)
        elif purchase['status'] == 'Entregado':
            purchases_status['received'].append(purchase)
        elif purchase['status'] == 'Compra cancelada':
            purchases_status['canceled'].append(purchase)

    # Print purchases status
    print(f"🚀 Found {len(purchases_status['pending'])} pending purchases")
    print(f"🚀 Found {len(purchases_status['received'])} received purchases")
    print(f"🚀 Found {len(purchases_status['canceled'])} canceled purchases")

    valid_purchases = []
    # Add pending and received purchases
    valid_purchases.extend(purchases_status['pending'])
    valid_purchases.extend(purchases_status['received'])

    print(f"🚀 Found {len(valid_purchases)} valid purchases\n")

    for purchase in valid_purchases:
        summary.add_purchase(parser.get_purchase_details(purchase['url']))

    print("\nStats\n")
    print(f"🚀 Total purchases: {summary.get_purchases_total()}")
    
def _print_error(message):
    print(f"❌ Error: {message}")
    exit(1)

# Validates the cooki file format and the file exists
def _validate_cookies_file(cookies_path):
    if not cookies_path.endswith(".json") and not cookies_path.endswith(".txt"):
        _print_error("Cookies file must be in json or txt format")

    if not os.path.exists(cookies_path):
        _print_error("Cookies file does not exist")

# Returns a dictionary with the cookies
def _parse_cookies(cookies_file):
    # Init empty dictionary
    cookies = {}
    _validate_cookies_file(cookies_file)

    if cookies_file.endswith(".json"):
        with open(cookies_file, "r") as f:
            cookies = json.load(f)

    return cookies

if __name__ == "__main__":
    main()
