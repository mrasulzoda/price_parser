from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from parser import citymebel, akram_mebel, hoff, jysk, utils
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
import atexit
import csv
import io

app = Flask(__name__)
CORS(app)

DATA_FILE = "data/products.json"
CATEGORIES_FILE = "data/categories.json"
LAST_PARSED_FILE = "data/last_parsed.txt"
COMPARISON_FILE = "data/comparison.json"

os.makedirs("data", exist_ok=True)

SITES = [
    {
        "parser": citymebel,
        "name": "City Mebel",
        "categories": {
            "Диваны": "https://citymebel.tj/product-category/living_rooms/sofas/"
        }
    },
    {
        "parser": akram_mebel,
        "name": "Akram Mebel",
        "categories": {
            "Стулья": "https://akram-mebel.tj/pc/stulya/",
            "Гардеробные": "https://akram-mebel.tj/pc/garderobnye/",
            "Диваны": "https://akram-mebel.tj/pc/divany/",
            "Кровати": "https://akram-mebel.tj/pc/krovati/",
            "Кухонные гарниры": "https://akram-mebel.tj/pc/kuhonnye-garnitury/",
            "Столы": "https://akram-mebel.tj/pc/stoly/",
            "Сейфы": "https://akram-mebel.tj/pc/sejfy/",
            "Спальные гарнитуры": "https://akram-mebel.tj/pc/spal-garnitura/",
            "Качели": "https://akram-mebel.tj/pc/kacheli/"
        }
    },
    {
        "parser": hoff,
        "name": "HOFF",
        "categories": {
            "Диваны": "https://hoff.ru/catalog/gostinaya/divany/",
            "Шкафы": "https://hoff.ru/catalog/shkafy/",
            "Кровати": "https://hoff.ru/catalog/spalnya/krovati/",
            "Кухонные гарниры": "https://hoff.ru/catalog/kuhnya/kuhonnye_garnitury/gotovie_reshenia/"
        }
    },
    {
        "parser": jysk,
        "name": "JYSK",
        "categories": {
            "Диваны": "https://jysk.tj/product-category/gostinaya/divany/",
            "Стулья": "https://jysk.tj/product-category/gostinaya/kresla/",
            "Кровати": "https://jysk.tj/product-category/gostinaya/divany-krovati/"
        }
    }
]

def get_last_parsed_date():
    """Получить дату последнего парсинга"""
    try:
        if os.path.exists(LAST_PARSED_FILE):
            with open(LAST_PARSED_FILE, "r") as f:
                date_str = f.read().strip()
                if date_str:
                    return datetime.fromisoformat(date_str)
    except Exception:
        pass
    return None

def save_last_parsed_date():
    """Сохранить дату текущего парсинга"""
    try:
        with open(LAST_PARSED_FILE, "w") as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        print(f"Ошибка при сохранении даты парсинга: {e}")

def should_parse_today():
    """Проверить, нужно ли парсить сегодня"""
    last_parsed = get_last_parsed_date()
    if not last_parsed:
        return True  # Никогда не парсили
    
    today = datetime.now().date()
    last_parsed_date = last_parsed.date()
    
    # Парсить только если последний парсинг был не сегодня
    return last_parsed_date != today

def save_comparison_data(data):
    """Сохранить данные сравнения в файл"""
    try:
        data_with_timestamp = {
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        utils.save_json(data_with_timestamp, COMPARISON_FILE)
    except Exception as e:
        print(f"Ошибка при сохранении данных сравнения: {e}")

def load_comparison_data():
    """Загрузить данные сравнения из файла"""
    try:
        if os.path.exists(COMPARISON_FILE):
            return utils.load_json(COMPARISON_FILE)
    except Exception as e:
        print(f"Ошибка при загрузке данных сравнения: {e}")
    return None

def parse_all_sites(force=False):
    """Парсирует все сайты и сохраняет с категориями"""
    # Проверяем, нужно ли парсить сегодня
    if not force and not should_parse_today():
        print(f"[{datetime.now()}] Парсинг уже выполнялся сегодня. Пропускаем.")
        
        # Загружаем существующие данные для возврата
        try:
            products = utils.load_json(DATA_FILE)
            categories_data = utils.load_json(CATEGORIES_FILE)
            
            if isinstance(categories_data, dict):
                categories_count = categories_data.get("categories", {})
            else:
                categories_count = {}
            
            return {
                "status": "skipped", 
                "count": len(products) if isinstance(products, list) else 0, 
                "categories": categories_count,
                "message": "Парсинг уже выполнялся сегодня"
            }
        except Exception as e:
            print(f"Ошибка при загрузке кешированных данных: {e}")
            # Если не удалось загрузить, парсим заново
    
    print(f"[{datetime.now()}] Начало парсинга всех сайтов...")
    
    all_items = []
    categories_count = {}
    
    for site in SITES:
        parser = site["parser"]
        site_name = site["name"]
        for category_name, cat_url in site["categories"].items():
            try:
                items = parser.parse_category(cat_url)
                for item in items:
                    item["category"] = category_name
                    item["site_name"] = site_name
                    print(item["category"], item["site_name"])
                all_items.extend(items)
                
                if category_name not in categories_count:
                    categories_count[category_name] = 0
                categories_count[category_name] += len(items)
            except Exception as e:
                print(f"Ошибка при парсинге {site_name} -> {category_name}: {e}")
                continue
    
    # Сохраняем товары
    utils.save_json(all_items, DATA_FILE)
    
    # Сохраняем статистику категорий
    categories_data = {
        "total_products": len(all_items),
        "categories": categories_count,
        "last_updated": datetime.now().isoformat(),
        "sites_count": len(SITES)
    }
    utils.save_json(categories_data, CATEGORIES_FILE)
    
    # Сохраняем дату парсинга
    save_last_parsed_date()
    
    print(f"[{datetime.now()}] Парсинг завершён. Загружено товаров: {len(all_items)}")
    
    return {"status": "success", "count": len(all_items), "categories": categories_count}

# Настройка автопарсинга
scheduler = BackgroundScheduler()

def scheduled_parse():
    """Функция для автоматического парсинга раз в день"""
    try:
        print(f"[{datetime.now()}] Проверка необходимости автоматического парсинга...")
        if should_parse_today():
            print(f"[{datetime.now()}] Начало автоматического парсинга...")
            result = parse_all_sites(force=True)
            print(f"[{datetime.now()}] Парсинг завершён. Загружено товаров: {result['count']}")
        else:
            print(f"[{datetime.now()}] Автоматический парсинг не требуется (уже выполнялся сегодня)")
    except Exception as e:
        print(f"Ошибка при автоматическом парсинге: {e}")

# Запускаем проверку каждый день в 2:00 утра
scheduler.add_job(func=scheduled_parse, trigger="cron", hour=2, minute=0)
scheduler.start()

# Останавливаем scheduler при выходе
atexit.register(lambda: scheduler.shutdown())

# ========== API ENDPOINTS ==========

@app.route("/fetch", methods=["POST"])
def fetch():
    """Запускает парсинг всех сайтов (принудительно или если не парсили сегодня)"""
    force = request.args.get("force", "false").lower() == "true"
    result = parse_all_sites(force=force)
    return jsonify(result)

@app.route("/last-parsed", methods=["GET"])
def get_last_parsed():
    """Получить дату последнего парсинга"""
    last_parsed = get_last_parsed_date()
    if last_parsed:
        return jsonify({
            "last_parsed": last_parsed.isoformat(),
            "should_parse_today": should_parse_today(),
            "days_since_last_parse": (datetime.now().date() - last_parsed.date()).days
        })
    return jsonify({
        "last_parsed": None,
        "should_parse_today": True,
        "days_since_last_parse": None
    })

@app.route("/stats/by-category", methods=["GET"])
def get_stats_by_category():
    """Получить статистику отдельно для каждой категории"""
    products = utils.load_json(DATA_FILE)
    
    if not isinstance(products, list):
        return jsonify({"categories": []})
    
    # Группируем товары по категориям
    categories_stats = {}
    
    for product in products:
        category = product.get("category", "Без категории")
        price = product.get("price", 0)
        
        if category not in categories_stats:
            categories_stats[category] = {
                "total_products": 0,
                "prices": [],
                "sites": set()
            }
        
        categories_stats[category]["total_products"] += 1
        if price and price > 0:
            categories_stats[category]["prices"].append(price)
        
        site_name = product.get("site_name", "Неизвестно")
        categories_stats[category]["sites"].add(site_name)
    
    # Рассчитываем статистику для каждой категории
    result = []
    for category, stats in categories_stats.items():
        prices = stats["prices"]
        
        category_stats = {
            "category": category,
            "total_products": stats["total_products"],
            "sites_count": len(stats["sites"]),
            "sites": list(stats["sites"]),
            "avg_price": round(sum(prices) / len(prices), 2) if prices else 0,
            "min_price": min(prices) if prices else 0,
            "max_price": max(prices) if prices else 0,
            "price_range": f"{min(prices)}-{max(prices)}" if prices else "0-0"
        }
        
        # Распределение по ценовым диапазонам
        if prices:
            ranges = {
                "До 100": 0,
                "100-500": 0,
                "500-1000": 0,
                "1000-5000": 0,
                "Более 5000": 0
            }
            
            for price in prices:
                if price < 100:
                    ranges["До 100"] += 1
                elif price < 500:
                    ranges["100-500"] += 1
                elif price < 1000:
                    ranges["500-1000"] += 1
                elif price < 5000:
                    ranges["1000-5000"] += 1
                else:
                    ranges["Более 5000"] += 1
            
            # Преобразуем в проценты
            total = len(prices)
            category_stats["price_distribution"] = {
                range_name: round((count / total) * 100, 1)
                for range_name, count in ranges.items()
                if count > 0
            }
        else:
            category_stats["price_distribution"] = {}
        
        result.append(category_stats)
    
    # Сортируем по количеству товаров (по убыванию)
    result.sort(key=lambda x: x["total_products"], reverse=True)
    
    return jsonify({"categories": result})

@app.route("/products", methods=["GET"])
def get_products():
    """Получить все товары"""
    products = utils.load_json(DATA_FILE)
    
    # Возвращаем в формате для фронтенда
    return jsonify({
        "products": products if isinstance(products, list) else [],
        "count": len(products) if isinstance(products, list) else 0,
        "last_updated": get_last_parsed_date().isoformat() if get_last_parsed_date() else None
    })

@app.route("/categories", methods=["GET"])
def get_categories():
    """Получить статистику по категориям"""
    categories = utils.load_json(CATEGORIES_FILE)
    return jsonify(categories)

@app.route("/products/by-category/<category>", methods=["GET"])
def get_by_category(category):
    """Получить товары по категории"""
    products = utils.load_json(DATA_FILE)
    filtered = [p for p in products if p.get("category") == category]
    return jsonify({
        "category": category,
        "products": filtered,
        "count": len(filtered)
    })

@app.route("/products/by-site/<site>", methods=["GET"])
def get_by_site(site):
    """Получить товары по сайту"""
    products = utils.load_json(DATA_FILE)
    filtered = [p for p in products if p.get("site") == site]
    return jsonify({
        "site": site,
        "products": filtered,
        "count": len(filtered)
    })

@app.route("/export", methods=["GET"])
def export_file():
    """Экспортировать товары в JSON"""
    if os.path.exists(DATA_FILE):
        return send_file(
            DATA_FILE,
            as_attachment=True,
            download_name=f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
    return jsonify({"error": "Файл не найден"}), 404

@app.route("/export/stats", methods=["GET"])
def export_stats():
    """Экспортировать статистику по категориям в CSV"""
    try:
        stats_data = get_stats_by_category().get_json()
        categories = stats_data.get("categories", [])
        
        if not categories:
            return jsonify({"error": "Нет данных для экспорта"}), 404
        
        # Создаем CSV в памяти
        output = io.StringIO()
        writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
        # Заголовки
        writer.writerow([
            "Категория", 
            "Товаров", 
            "Сайтов", 
            "Средняя цена (сом)", 
            "Мин. цена (сом)", 
            "Макс. цена (сом)", 
            "Диапазон цен (сом)",
            "Сайты"
        ])
        
        # Данные
        for category in categories:
            writer.writerow([
                category["category"],
                category["total_products"],
                category["sites_count"],
                category["avg_price"],
                category["min_price"],
                category["max_price"],
                category["price_range"],
                ", ".join(category["sites"])
            ])
        
        # Возвращаем CSV файл
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            as_attachment=True,
            download_name=f"stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mimetype='text/csv'
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/export/comparison", methods=["GET"])
def export_comparison():
    """Экспортировать сравнение цен JYSK в CSV"""
    try:
        comparison_data = compare_jysk_prices().get_json()
        
        if "comparison" not in comparison_data:
            return jsonify({"error": "Нет данных для экспорта"}), 404
        
        categories = comparison_data.get("comparison", [])
        summary = comparison_data.get("summary", {})
        
        if not categories:
            return jsonify({"error": "Нет данных для экспорта"}), 404
        
        # Создаем CSV в памяти
        output = io.StringIO()
        writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
        # Заголовки основного файла
        writer.writerow([
            "Категория",
            "Статус",
            "Разница (%)",
            "Разница (сом)",
            "JYSK (средняя, сом)",
            "JYSK (мин, сом)",
            "JYSK (макс, сом)",
            "Товаров JYSK",
            "Рынок (средняя, сом)",
            "Рынок (мин, сом)",
            "Рынок (макс, сом)",
            "Товаров рынка",
            "Всего сайтов"
        ])
        
        # Данные
        for category in categories:
            writer.writerow([
                category["category"],
                category["comparison"]["status"],
                f"{category['comparison']['price_diff_percent']}%",
                category["comparison"]["price_diff"],
                category["jysk_stats"]["avg_price"],
                category["jysk_stats"]["min_price"],
                category["jysk_stats"]["max_price"],
                category["jysk_stats"]["count"],
                category["market_stats"]["avg_price"],
                category["market_stats"]["min_price"],
                category["market_stats"]["max_price"],
                category["market_stats"]["count"],
                category["samples"]["total_sites"]
            ])
        
        # Создаем второй CSV с сводкой
        summary_output = io.StringIO()
        summary_writer = csv.writer(summary_output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
        summary_writer.writerow(["Параметр", "Значение"])
        summary_writer.writerow(["Всего категорий", summary["total_categories"]])
        summary_writer.writerow(["JYSK дешевле", summary["categories_where_cheaper"]])
        summary_writer.writerow(["JYSK дороже", summary["categories_where_expensive"]])
        summary_writer.writerow(["На уровне рынка", summary["categories_where_normal"]])
        summary_writer.writerow(["Средняя разница", f"{summary['avg_price_diff']}%"])
        summary_writer.writerow(["Преимущество JYSK", "Да" if summary["jysk_advantage"] else "Нет"])
        summary_writer.writerow(["Дата экспорта", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        
        # Возвращаем ZIP архив с двумя файлами
        from zipfile import ZipFile
        import tempfile
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            with ZipFile(tmp.name, 'w') as zipf:
                # Добавляем основной файл сравнения
                output.seek(0)
                zipf.writestr(f"jysk_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", output.getvalue())
                
                # Добавляем файл сводки
                summary_output.seek(0)
                zipf.writestr(f"jysk_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", summary_output.getvalue())
            
            # Читаем ZIP файл
            with open(tmp.name, 'rb') as f:
                zip_data = f.read()
        
        # Удаляем временный файл
        os.unlink(tmp.name)
        
        # Возвращаем ZIP архив
        return send_file(
            io.BytesIO(zip_data),
            as_attachment=True,
            download_name=f"jysk_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mimetype='application/zip'
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/export/full-report", methods=["GET"])
def export_full_report():
    """Экспортировать полный отчет в Excel"""
    try:
        import pandas as pd
        from io import BytesIO
        
        # Получаем данные
        products = utils.load_json(DATA_FILE)
        stats_data = get_stats_by_category().get_json()
        comparison_data = compare_jysk_prices().get_json()
        
        if not isinstance(products, list) or not products:
            return jsonify({"error": "Нет данных для экспорта"}), 404
        
        # Создаем Excel writer
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 1. Лист с товарами
            products_df = pd.DataFrame(products)
            if not products_df.empty:
                products_df.to_excel(writer, sheet_name='Товары', index=False)
            
            # 2. Лист со статистикой по категориям
            categories = stats_data.get("categories", [])
            if categories:
                stats_df = pd.DataFrame(categories)
                stats_df.to_excel(writer, sheet_name='Статистика', index=False)
            
            # 3. Лист со сравнением JYSK
            comparison_categories = comparison_data.get("comparison", [])
            if comparison_categories:
                comparison_rows = []
                for cat in comparison_categories:
                    row = {
                        "Категория": cat["category"],
                        "Статус": cat["comparison"]["status"],
                        "Разница (%)": cat["comparison"]["price_diff_percent"],
                        "Разница (сом)": cat["comparison"]["price_diff"],
                        "JYSK_средняя": cat["jysk_stats"]["avg_price"],
                        "JYSK_мин": cat["jysk_stats"]["min_price"],
                        "JYSK_макс": cat["jysk_stats"]["max_price"],
                        "JYSK_количество": cat["jysk_stats"]["count"],
                        "Рынок_средняя": cat["market_stats"]["avg_price"],
                        "Рынок_мин": cat["market_stats"]["min_price"],
                        "Рынок_макс": cat["market_stats"]["max_price"],
                        "Рынок_количество": cat["market_stats"]["count"]
                    }
                    # Добавляем сравнение по сайтам
                    for i, site in enumerate(cat.get("site_comparison", []), 1):
                        row[f"Сайт_{i}"] = site["site"]
                        row[f"Сайт_{i}_цена"] = site["avg_price"]
                        row[f"Сайт_{i}_разница"] = f"{site['diff_percent']}%"
                    comparison_rows.append(row)
                
                comparison_df = pd.DataFrame(comparison_rows)
                comparison_df.to_excel(writer, sheet_name='Сравнение_JYSK', index=False)
            
            # 4. Лист с сводкой
            summary_data = comparison_data.get("summary", {})
            summary_df = pd.DataFrame([{
                "Всего категорий": summary_data.get("total_categories", 0),
                "JYSK дешевле": summary_data.get("categories_where_cheaper", 0),
                "JYSK дороже": summary_data.get("categories_where_expensive", 0),
                "На уровне рынка": summary_data.get("categories_where_normal", 0),
                "Средняя разница (%)": summary_data.get("avg_price_diff", 0),
                "Преимущество JYSK": "Да" if summary_data.get("jysk_advantage", False) else "Нет",
                "Дата отчета": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Последний парсинг": get_last_parsed_date().isoformat() if get_last_parsed_date() else "Нет данных"
            }])
            summary_df.to_excel(writer, sheet_name='Сводка', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name=f"full_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except ImportError:
        return jsonify({"error": "Для экспорта в Excel требуется библиотека pandas. Установите: pip install pandas openpyxl"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/import", methods=["POST"])
def import_file():
    """Импортировать товары из JSON"""
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "Файл не найден"}), 400
    
    try:
        data = json.load(file)
        utils.save_json(data, DATA_FILE)
        
        # Обновляем дату парсинга на текущую
        save_last_parsed_date()
        
        return jsonify({"status": "imported", "count": len(data)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/stats", methods=["GET"])
def get_stats():
    """Получить общую статистику"""
    products = utils.load_json(DATA_FILE)
    categories = utils.load_json(CATEGORIES_FILE)
    
    if not isinstance(products, list):
        products = []
    
    prices = [p.get("price", 0) for p in products if isinstance(p.get("price"), (int, float))]
    
    stats = {
        "total_products": len(products),
        "total_categories": len(categories.get("categories", {})) if isinstance(categories, dict) else 0,
        "total_sites": len(SITES),
        "avg_price": sum(prices) / len(prices) if prices else 0,
        "min_price": min(prices) if prices else 0,
        "max_price": max(prices) if prices else 0,
        "last_parsed": get_last_parsed_date().isoformat() if get_last_parsed_date() else None,
        "should_parse_today": should_parse_today()
    }
    
    return jsonify(stats)

@app.route("/compare/jysk", methods=["GET"])
def compare_jysk_prices():
    """Сравнить СРЕДНИЕ цены JYSK с СРЕДНИМИ ценами других магазинов"""
    products = utils.load_json(DATA_FILE)
    
    if not isinstance(products, list):
        return jsonify({"error": "Нет данных"}), 400
    
    # Группируем товары по категориям
    categories_comparison = {}
    
    for product in products:
        category = product.get("category", "Без категории")
        site_name = product.get("site_name", "")
        price = product.get("price", 0)
        
        # Пропускаем товары без цены
        if not price or price <= 0:
            continue
        
        if category not in categories_comparison:
            categories_comparison[category] = {
                "jysk": {"prices": []},
                "other_sites": {}
            }
        
        # Разделяем по сайтам
        if site_name.lower() == "jysk":
            categories_comparison[category]["jysk"]["prices"].append(price)
        else:
            if site_name not in categories_comparison[category]["other_sites"]:
                categories_comparison[category]["other_sites"][site_name] = []
            categories_comparison[category]["other_sites"][site_name].append(price)
    
    # Рассчитываем статистику и сравнение
    result = []
    
    for category, data in categories_comparison.items():
        jysk_prices = data["jysk"]["prices"]
        
        # Собираем ВСЕ цены с других сайтов
        other_prices = []
        for site_prices in data["other_sites"].values():
            other_prices.extend(site_prices)
        
        # Пропускаем категории с недостаточным количеством данных
        if len(jysk_prices) < 3 or len(other_prices) < 3:
            continue
        
        # ===== ВАЖНО: СЧИТАЕМ СРЕДНИЕ ЦЕНЫ =====
        jysk_avg = sum(jysk_prices) / len(jysk_prices)
        other_avg = sum(other_prices) / len(other_prices)
        
        print(f"\n[{category}]")
        print(f"  JYSK: {len(jysk_prices)} товаров, средняя цена = {jysk_avg:.2f}")
        print(f"  Рынок: {len(other_prices)} товаров, средняя цена = {other_avg:.2f}")
        
        # Определяем разницу в процентах (на основе СРЕДНИХ цен)
        if other_avg > 0:
            price_diff_percent = ((jysk_avg - other_avg) / other_avg) * 100
        else:
            price_diff_percent = 0
        
        print(f"  Разница: {price_diff_percent:.1f}%")
        
        # Определяем статус
        if price_diff_percent > 15:
            status = "значительно дороже"
            status_class = "expensive"
        elif price_diff_percent > 5:
            status = "дороже"
            status_class = "expensive-moderate"
        elif price_diff_percent < -15:
            status = "значительно дешевле"
            status_class = "cheaper"
        elif price_diff_percent < -5:
            status = "дешевле"
            status_class = "cheaper-moderate"
        else:
            status = "на уровне рынка"
            status_class = "normal"
        
        # Сравнение с каждым сайтом отдельно (тоже по средним)
        site_comparison = []
        for site_name, prices in data["other_sites"].items():
            if prices and len(prices) >= 3:
                site_avg = sum(prices) / len(prices)  # СРЕДНЯЯ цена по сайту
                if site_avg > 0:
                    diff = ((jysk_avg - site_avg) / site_avg) * 100
                else:
                    diff = 0
                
                site_comparison.append({
                    "site": site_name,
                    "avg_price": round(site_avg, 2),
                    "product_count": len(prices),
                    "diff_percent": round(diff, 1),
                    "status": "дороже" if diff > 0 else "дешевле"
                })
        
        # Сортируем сайты по разнице
        site_comparison.sort(key=lambda x: x["diff_percent"])
        
        result.append({
            "category": category,
            "jysk_stats": {
                "avg_price": round(jysk_avg, 2),
                "min_price": min(jysk_prices),
                "max_price": max(jysk_prices),
                "count": len(jysk_prices)
            },
            "market_stats": {
                "avg_price": round(other_avg, 2),
                "min_price": min(other_prices),
                "max_price": max(other_prices),
                "count": len(other_prices)
            },
            "comparison": {
                "price_diff": round(jysk_avg - other_avg, 2),
                "price_diff_percent": round(price_diff_percent, 1),
                "status": status,
                "status_class": status_class
            },
            "site_comparison": site_comparison,
            "samples": {
                "jysk_count": len(jysk_prices),
                "market_count": len(other_prices),
                "total_sites": len(data["other_sites"]) + 1
            }
        })
    
    # Сортируем по абсолютной разнице в процентах
    result.sort(key=lambda x: abs(x["comparison"]["price_diff_percent"]), reverse=True)
    
    # Рассчитываем сводную статистику
    total_categories = len(result)
    if total_categories > 0:
        categories_where_cheaper = len([r for r in result if r["comparison"]["price_diff_percent"] < -5])
        categories_where_expensive = len([r for r in result if r["comparison"]["price_diff_percent"] > 5])
        
        # Средняя разница по всем категориям
        avg_price_diff = round(
            sum([r["comparison"]["price_diff_percent"] for r in result]) / total_categories, 
            1
        )
    else:
        categories_where_cheaper = 0
        categories_where_expensive = 0
        avg_price_diff = 0
    
    print(f"\n=== ИТОГОВАЯ СТАТИСТИКА ===")
    print(f"Всего категорий: {total_categories}")
    print(f"JYSK дешевле: {categories_where_cheaper}")
    print(f"JYSK дороже: {categories_where_expensive}")
    print(f"Средняя разница: {avg_price_diff}%")
    
    comparison_result = {
        "comparison": result,
        "summary": {
            "total_categories": total_categories,
            "categories_where_cheaper": categories_where_cheaper,
            "categories_where_expensive": categories_where_expensive,
            "categories_where_normal": total_categories - categories_where_cheaper - categories_where_expensive,
            "avg_price_diff": avg_price_diff,
            "jysk_advantage": avg_price_diff < 0
        }
    }
    
    # Сохраняем данные сравнения
    save_comparison_data(comparison_result)
    
    return jsonify(comparison_result)

@app.route("/health", methods=["GET"])
def health():
    """Проверка здоровья сервиса"""
    return jsonify({
        "status": "ok", 
        "timestamp": datetime.now().isoformat(),
        "data_exists": os.path.exists(DATA_FILE),
        "should_parse_today": should_parse_today(),
        "last_parsed": get_last_parsed_date().isoformat() if get_last_parsed_date() else None
    })

if __name__ == "__main__":
    print("Инициализация парсера...")
    
    # Проверяем, нужно ли выполнить первый парсинг
    if not os.path.exists(DATA_FILE) or should_parse_today():
        try:
            print("Выполнение первого парсинга...")
            parse_all_sites()
            print("Первый парсинг завершён")
        except Exception as e:
            print(f"Ошибка при первом парсинге: {e}")
    else:
        print("Данные уже существуют и сегодня парсинг уже выполнялся. Пропускаем начальный парсинг.")
        print(f"Последний парсинг: {get_last_parsed_date()}")
    
    app.run(debug=True, host="0.0.0.0", port=5001)

