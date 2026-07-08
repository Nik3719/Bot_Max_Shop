import asyncio
import logging

from config import BOT_TOKEN, SYNC_INTERVAL_HOURS, ADMIN_IDS
from maxapi import Bot, Dispatcher
from maxapi.client.default import DefaultConnectionProperties

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from db import init_db
from bot.handlers import router as handlers_router
from bot.callbacks import router as callbacks_router
from bot.admin import admin_router
from bot.menu import menu_router
from services.sheets_sync import sync_from_sheets

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info("Бот запускается")

bot = Bot(
    BOT_TOKEN,
    default_connection=DefaultConnectionProperties(
        headers={"Authorization": BOT_TOKEN}
    ),
)
bot.params.clear()


dp = Dispatcher()
dp.include_routers(menu_router, admin_router, handlers_router, callbacks_router)

scheduler = AsyncIOScheduler()

async def auto_sync_job():
    logger.info("Запуск автосинхронизации")
    try:
        res = await sync_from_sheets(admin_user_id=None)
        msg = f'🔄 Автосинхронизация завершена:\nДобавлено: {res["inserted"]}\nОбновлено: {res["updated"]}\nСкрыто: {res["deactivated"]}'
        logger.info(msg)
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, text=msg)
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Ошибка автосинхронизации: {e}")

async def main():
    logger.info("Инициализация базы данных")
    await init_db()
    logger.info("База данных успешно инициализирована.")
    
    scheduler.add_job(auto_sync_job, 'interval', hours=SYNC_INTERVAL_HOURS)
    scheduler.start()
    logger.info(f"Планировщик запущен (интервал: {SYNC_INTERVAL_HOURS} ч.)")

    logger.info("Запуск long-polling бота")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка при работе бота: {e}", exc_info=True)
    finally:
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Программа завершена (Ctrl+C)")
