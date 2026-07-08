import aiosqlite
import logging
from db.queries_sql import *
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

DB_PATH = "db/shop_db.sqlite"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_USERS_TABLE)
        await db.execute(CREATE_PRODUCTS_TABLE)
        await db.execute(CREATE_ORDERS_TABLE)
        await db.execute(CREATE_SYNC_LOG_TABLE)
        await db.commit()

# --- Users ---
async def search_user(max_user_id: int) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(SELECT_USER_BY_ID, (max_user_id,))
            return await cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Ошибка БД при поиске пользователя {max_user_id}: {e}")
        return False

async def get_user_by_id(max_user_id: int) -> dict:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(SELECT_USER_BY_ID, (max_user_id,))
            row = await cursor.fetchone()
            if row:
                return {'max_user_id': row[0], 'full_name': row[1], 'phone': row[2]}
            return None
    except Exception as e:
        logger.error(f"Ошибка БД при поиске пользователя {max_user_id}: {e}")
        return None

async def is_phone_registered(phone: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(SELECT_USER_ID_BY_PHONE, (phone,))
            return await cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Ошибка БД при поиске телефона {phone}: {e}")
        return True

async def add_user(user: dict):
    logger.info(f"Добавление пользователя {user['max_user_id']} в БД")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                INSERT_USER,
                (user["max_user_id"], user["full_name"], user["phone"]),
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка БД при добавлении пользователя: {e}")
        raise e

# --- Products ---
async def upsert_product(product_id: str, name: str, description: str, price: int, category: str, photo_url: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(UPSERT_PRODUCT, (product_id, name, description, price, category, photo_url))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка БД при UPSERT товара {product_id}: {e}")
        raise e

async def deactivate_product(product_id: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(DEACTIVATE_PRODUCT, (product_id,))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка БД при деактивации товара {product_id}: {e}")

async def get_active_products() -> list[dict]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(SELECT_ACTIVE_PRODUCTS)
            rows = await cursor.fetchall()
            return [{'product_id': r[0], 'name': r[1], 'description': r[2], 'price': r[3], 'category': r[4], 'photo_url': r[5]} for r in rows]
    except Exception as e:
        logger.error(f"Ошибка БД при получении товаров: {e}")
        return []

async def get_product_by_id(product_id: str) -> dict:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(SELECT_ACTIVE_PRODUCT_BY_ID, (product_id,))
            r = await cursor.fetchone()
            if r:
                return {'product_id': r[0], 'name': r[1], 'description': r[2], 'price': r[3], 'category': r[4], 'photo_url': r[5]}
            return None
    except Exception as e:
        logger.error(f"Ошибка БД при получении товара {product_id}: {e}")
        return None

# --- Orders ---
async def add_order(max_user_id: int, product_id: str, comment: str) -> int:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(INSERT_ORDER, (max_user_id, product_id, comment))
            await db.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Ошибка БД при создании заказа: {e}")
        return None

async def get_new_orders() -> list[dict]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(SELECT_NEW_ORDERS)
            rows = await cursor.fetchall()
            return [{'id': r[0], 'full_name': r[1], 'phone': r[2], 'product_name': r[3], 'price': r[4], 'status': r[5], 'created_at': r[6], 'comment': r[7]} for r in rows]
    except Exception as e:
        logger.error(f"Ошибка БД при получении новых заявок: {e}")
        return []

async def get_user_orders(max_user_id: int, limit: int = 10) -> list[dict]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(SELECT_USER_ORDERS, (max_user_id, limit))
            rows = await cursor.fetchall()
            return [{'id': r[0], 'product_name': r[1], 'price': r[2], 'status': r[3], 'created_at': r[4]} for r in rows]
    except Exception as e:
        logger.error(f"Ошибка БД при получении заявок пользователя {max_user_id}: {e}")
        return []

async def update_order_status(order_id: int, status: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(UPDATE_ORDER_STATUS, (status, order_id))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка БД при обновлении статуса заявки {order_id}: {e}")

# --- Sync Log ---
async def add_sync_log(status: str, initiator_id: int = None) -> int:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(INSERT_SYNC_LOG, (status, initiator_id))
            await db.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Ошибка БД при создании sync_log: {e}")
        return None

async def update_sync_log(log_id: int, status: str, inserted: int, updated: int, deactivated: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(UPDATE_SYNC_LOG, (status, inserted, updated, deactivated, log_id))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка БД при обновлении sync_log {log_id}: {e}")

async def get_last_sync() -> dict:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(SELECT_LAST_SYNC)
            r = await cursor.fetchone()
            if r:
                return {'finished_at': r[0], 'status': r[1], 'inserted': r[2], 'updated': r[3], 'deactivated': r[4]}
            return None
    except Exception as e:
        logger.error(f"Ошибка БД при получении последнего sync_log: {e}")
        return None

# --- Stats ---
async def get_stats() -> dict:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            admin_ids = ADMIN_IDS if ADMIN_IDS else [0]
            placeholders = ','.join('?' * len(admin_ids))
            query = SELECT_USERS_COUNT.format(placeholders=placeholders)
            cursor = await db.execute(query, admin_ids)
            u = await cursor.fetchone()
            cursor = await db.execute(SELECT_PRODUCTS_COUNT)
            p = await cursor.fetchone()
            cursor = await db.execute(SELECT_ORDERS_COUNT)
            o = await cursor.fetchone()
            return {
                'users': u[0] if u else 0,
                'products': p[0] if p else 0,
                'orders': o[0] if o else 0
            }
    except Exception as e:
        logger.error(f"Ошибка БД при получении статистики: {e}")
        return {'users': 0, 'products': 0, 'orders': 0}
