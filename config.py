import os
import json
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Токен бота не найден! Убедитесь, что переменная BOT_TOKEN задана в файле .env")

# Настройки администраторов
admin_ids_str = os.getenv("ADMIN_IDS", "541014469932") # по умолчанию айди владельца или пусто
try:
    ADMIN_IDS = [int(i.strip()) for i in admin_ids_str.split(",") if i.strip()]
except Exception:
    ADMIN_IDS = []

# Google Sheets
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "max-bot-shop-9b86dd3cb881.json")

# Автосинхронизация
SYNC_INTERVAL_HOURS = int(os.getenv("SYNC_INTERVAL_HOURS", 24))

ITEMS_PER_PAGE = int(os.getenv("ITEMS_PER_PAGE", 5))