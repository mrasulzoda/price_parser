# jysk.py
import requests
from bs4 import BeautifulSoup
from .utils import normalize_price

HEADERS = {"User-Agent": "Mozilla/5.0"}

def parse_category(category_url):
    items = []
    page = 1
    
    try:
        while True:
            # JYSK использует параметр query string для пагинации
            if page == 1:
                url = category_url
            else:
                url = f"{category_url}page/{page}/"
                
            r = requests.get(url, headers=HEADERS, timeout=10)
            
            if r.status_code != 200:
                break
                
            soup = BeautifulSoup(r.text, "lxml")
            
            # Ищем товары - используем правильный селектор
            products = soup.select("li.product")
            
            if not products:
                print(f"На странице {url} товары не найдены, селектор: li.product")
                break
                
            print(f"На странице {page} найдено {len(products)} товаров")
                
            for p in products:
                try:
                    # Название товара
                    title_elem = p.select_one("h2.woocommerce-loop-product__title")
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                    else:
                        continue
                    
                    # Цена
                    price_elem = p.select_one("span.price .woocommerce-Price-amount bdi")
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price = normalize_price(price_text)
                    else:
                        continue
                    
                    # Ссылка на товар
                    link_elem = p.select_one("a.woocommerce-LoopProduct-link")
                    if link_elem and link_elem.get('href'):
                        link = link_elem['href']
                    else:
                        link_elem = p.select_one("a.ast-loop-product__link")
                        if link_elem and link_elem.get('href'):
                            link = link_elem['href']
                        else:
                            continue
                    
                    # Изображение
                    img_elem = p.select_one("img.attachment-woocommerce_thumbnail")
                    if img_elem and img_elem.get('src'):
                        image = img_elem['src']
                    else:
                        image = ""
                    
                    # Категория
                    category_elem = p.select_one("span.ast-woo-product-category")
                    category = category_elem.get_text(strip=True) if category_elem else ""
                    
                    items.append({
                        "title": title,
                        "price": price,
                        "link": link,
                        "image": image,
                        "category": category,  # Добавляем категорию из элемента
                        "category_url": category_url,
                        "site": "jysk",
                        "site_name": "JYSK"
                    })
                    
                    print(f"  ✓ {title} - {price} сом")
                    
                except Exception as e:
                    print(f"  ✗ Ошибка при парсинге товара: {e}")
                    continue
            
            # Проверяем есть ли следующая страница
            next_page = soup.select_one("a.next") or soup.select_one("a[rel='next']")
            if not next_page:
                break
                
            page += 1
            
    except Exception as e:
        print(f"Ошибка при парсинге JYSK категории {category_url}: {e}")
    
    return items
