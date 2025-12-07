import requests
from bs4 import BeautifulSoup
from .utils import normalize_price

HEADERS = {"User-Agent": "Mozilla/5.0"}

def parse_category(category_url):
    items = []
    page = 1
    while True:
        url = category_url.rstrip("/") + f"/page/{page}/"
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 404:
            break
        soup = BeautifulSoup(r.text, "lxml")
        products = soup.select("div.product-inner")
        if not products:
            break
        for p in products:
            try:
                title = p.select_one("h2.woocommerce-loop-product__title").get_text(strip=True)
                price = normalize_price(p.select_one("span.woocommerce-Price-amount bdi").get_text())
                link = p.select_one("a.woocommerce-LoopProduct-link")["href"]
                image = p.select_one("img")["src"]
                items.append({
                    "title": title,
                    "price": price,
                    "link": link,
                    "image": image,
                    "category_url": category_url,
                    "site": "citymebel"
                })
            except Exception:
                continue
        page += 1
    return items

