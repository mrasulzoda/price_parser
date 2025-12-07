import json
import os
import re

def save_json(data, filename="data/products.json"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(filename="data/products.json"):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def normalize_price(price_str):
    """
    Нормализует цену из строки в целое число (копейки/тиыны игнорируются).
    Примеры:
      "11 999,00" → 11999
      "1 200,50" → 1200
      "999" → 999
      "1.200" → 1200
    """
    if not price_str:
        return 0
    
    # Убираем пробелы, символы валют и другие нецифровые символы, кроме запятой и точки
    cleaned = re.sub(r'[^\d,.]', '', str(price_str))
    
    if not cleaned:
        return 0
    
    # Если есть запятая или точка как десятичный разделитель
    if ',' in cleaned or '.' in cleaned:
        # Заменяем запятую на точку для унификации
        cleaned = cleaned.replace(',', '.')
        
        # Разделяем на целую и дробную части
        parts = cleaned.split('.')
        
        # Берем только целую часть
        integer_part = parts[0]
        
        # Убираем точки как разделители тысяч (если они остались)
        integer_part = integer_part.replace('.', '')
        
        try:
            return int(integer_part) if integer_part else 0
        except ValueError:
            return 0
    
    # Если нет десятичных разделителей, просто убираем все точки (разделители тысяч)
    cleaned = cleaned.replace('.', '')
    
    try:
        return int(cleaned) if cleaned else 0
    except ValueError:
        return 0
