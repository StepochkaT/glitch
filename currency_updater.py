import os
import json
import requests
from datetime import datetime, timedelta

DATA_FILE = "data/currency_data.json"
API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
CURRENCIES = ["USD", "EUR", "CNY", "TRY", "AED", 'BYN']


def load_data():
    if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def clean_old_entries(data):
    now = datetime.utcnow()
    one_day_ago = now - timedelta(days=1)
    for currency, records in data.items():
        data[currency] = {
            date: value for date, value in records.items()
            if datetime.fromisoformat(date) >= one_day_ago
        }
    return data


def fetch_rates():
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        return response.json().get("Valute", {})
    except Exception as e:
        print(f"Ошибка с запросом: {e}")
        return None


def update_currency_data():
    data = load_data()
    rates = fetch_rates()
    if rates is None:
        return

    now = datetime.utcnow().isoformat()

    for code in CURRENCIES:
        if code in rates:
            rub_value = rates[code]["Value"]
            if code not in data:
                data[code] = {}
            data[code][now] = rub_value

    data['RUB'][now] = 1

    data = clean_old_entries(data)
    save_data(data)
    print("Обновлено")


if __name__ == "__main__":
    update_currency_data()
