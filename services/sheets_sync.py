import logging
import gspread_asyncio
from google.oauth2.service_account import Credentials
from config import SPREADSHEET_ID, GOOGLE_CREDENTIALS_FILE
import db

logger = logging.getLogger(__name__)

def get_creds():
    try:
        creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE)
        scoped = creds.with_scopes([
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ])
        return scoped
    except Exception as e:
        logger.error(f"Ошибка загрузки credentials: {e}")
        return None

agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)

async def sync_from_sheets(admin_user_id=None) -> dict:
    if not SPREADSHEET_ID:
        raise ValueError("SPREADSHEET_ID не задан")
    
    agc = await agcm.authorize()
    sh = await agc.open_by_key(SPREADSHEET_ID)
    try:
        ws = await sh.worksheet("Товары")
    except Exception:
        raise ValueError("Лист 'Товары' не найден")
    
    rows = await ws.get_all_records()
    
    inserted, updated, deactivated = 0, 0, 0
    
    active_products_db = await db.get_active_products()
    db_product_ids = {str(p['product_id']) for p in active_products_db}
    sheet_product_ids = set()
    
    for i, row in enumerate(rows, start=2):
        pid = str(row.get('product_id', '')).strip()
        name = str(row.get('name', '')).strip()
        price = row.get('price', 0)
        
        if not pid or not name or not price:
            logger.warning(f"Пропущена строка {i}: не хватает обязательных полей")
            continue
            
        try:
            price = int(price)
        except ValueError:
            logger.warning(f"Пропущена строка {i}: цена должна быть числом")
            continue
            
        desc = str(row.get('description', '')).strip()
        cat = str(row.get('category', '')).strip()
        photo = str(row.get('photo_url', '')).strip()
        
        sheet_product_ids.add(pid)
        
        existing = await db.get_product_by_id(pid)
        await db.upsert_product(pid, name, desc, price, cat, photo)
        
        if existing:
            updated += 1
        else:
            inserted += 1
            
    for pid in db_product_ids:
        if pid not in sheet_product_ids:
            await db.deactivate_product(pid)
            deactivated += 1
            
    log_id = await db.add_sync_log('success', admin_user_id)
    if log_id:
        await db.update_sync_log(log_id, 'success', inserted, updated, deactivated)
        
    return {
        "inserted": inserted,
        "updated": updated,
        "deactivated": deactivated
    }

async def sync_to_sheets(admin_user_id=None):
    if not SPREADSHEET_ID:
        raise ValueError("SPREADSHEET_ID не задан")
        
    agc = await agcm.authorize()
    sh = await agc.open_by_key(SPREADSHEET_ID)
    try:
        ws = await sh.worksheet("Заявки")
    except Exception:
        raise ValueError("Лист 'Заявки' не найден")
        
    orders = await db.get_new_orders()
    if not orders:
        return 0
        
    rows_to_append = []
    for o in orders:
        rows_to_append.append([
            o['id'],
            o['full_name'],
            o['phone'],
            o['product_name'],
            o['price'],
            o['status'],
            o['created_at']
        ])
        
    await ws.append_rows(rows_to_append)
    
    for o in orders:
        await db.update_order_status(o['id'], 'viewed')
        
    return len(orders)
