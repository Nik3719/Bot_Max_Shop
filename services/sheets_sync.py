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


async def _get_worksheet(name: str):
    if not SPREADSHEET_ID:
        raise ValueError("SPREADSHEET_ID не задан")
    agc = await agcm.authorize()
    sh = await agc.open_by_key(SPREADSHEET_ID)
    try:
        return await sh.worksheet(name)
    except Exception:
        raise ValueError(f"Лист '{name}' не найден")


def _parse_row(row: dict, row_num: int) -> dict | None:
    pid = str(row.get('product_id', '')).strip()
    name = str(row.get('name', '')).strip()
    price = row.get('price', 0)

    if pid == '' or name == '' or price == '':
        logger.warning(f"Пропущена строка {row_num}: не хватает обязательных полей")
        return None

    try:
        price = int(price)
    except ValueError:
        logger.warning(f"Пропущена строка {row_num}: цена должна быть числом")
        return None

    return {
        'product_id': pid,
        'name': name,
        'description': str(row.get('description', '')).strip(),
        'price': price,
        'category': str(row.get('category', '')).strip(),
        'photo_url': str(row.get('photo_url', '')).strip(),
    }


def _is_product_changed(existing: dict, new: dict) -> bool:
    fields = ('name', 'description', 'price', 'category', 'photo_url')
    for f in fields:
        e_val = existing.get(f)
        n_val = new.get(f)
        if e_val is None: e_val = ''
        if n_val is None: n_val = ''
        if e_val != n_val:
            return True
    return False


async def _save_product(product: dict):
    p = product
    await db.upsert_product(p['product_id'], p['name'], p['description'],
                            p['price'], p['category'], p['photo_url'])


async def _deactivate_missing(db_ids: set, sheet_ids: set) -> int:
    count = 0
    for pid in db_ids - sheet_ids:
        await db.deactivate_product(pid)
        count += 1
    return count


async def sync_from_sheets(admin_user_id=None) -> dict:
    ws = await _get_worksheet("Товары")
    rows = await ws.get_all_records()

    inserted, updated = 0, 0
    active_products_db = await db.get_active_products()
    db_product_ids = {str(p['product_id']) for p in active_products_db}
    sheet_product_ids = set()

    for i, row in enumerate(rows, start=2):
        product = _parse_row(row, i)
        if not product:
            continue

        pid = product['product_id']
        sheet_product_ids.add(pid)

        existing = await db.get_product_by_id(pid)
        if existing:
            if _is_product_changed(existing, product):
                await _save_product(product)
                updated += 1
        else:
            await _save_product(product)
            inserted += 1

    deactivated = await _deactivate_missing(db_product_ids, sheet_product_ids)

    log_id = await db.add_sync_log('success', admin_user_id)
    if log_id:
        await db.update_sync_log(log_id, 'success', inserted, updated, deactivated)

    return {"inserted": inserted, "updated": updated, "deactivated": deactivated}


async def sync_to_sheets(admin_user_id=None):
    ws = await _get_worksheet("Заявки")

    orders = await db.get_new_orders()
    if not orders:
        return 0

    rows_to_append = [
        [o['id'], o['full_name'], o['phone'], o['product_name'],
         o['price'], o['status'], o['created_at'], o.get('comment', '')]
        for o in orders
    ]

    await ws.append_rows(rows_to_append)

    for o in orders:
        await db.update_order_status(o['id'], 'viewed')

    log_id = await db.add_sync_log('success', admin_user_id)
    if log_id:
        await db.update_sync_log(log_id, 'success', 0, len(orders), 0)

    return len(orders)
