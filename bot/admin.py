import logging
from maxapi.types import Command, MessageCreated
from maxapi import Router
from maxapi.context.context import MemoryContext
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types.attachments.buttons import CallbackButton

import config
from bot import texts
import db
from services.sheets_sync import sync_from_sheets, sync_to_sheets

logger = logging.getLogger(__name__)
admin_router = Router()


def admin_only(func):
    async def wrapper(event: MessageCreated, context: MemoryContext):
        if event.message.sender.user_id not in config.ADMIN_IDS:
            await event.message.answer(texts.ADMIN_ONLY)
            return
        return await func(event, context)
    return wrapper


@admin_router.message_created(Command("help"))
@admin_only
async def cmd_admin_help(event: MessageCreated, context: MemoryContext):
    await event.message.answer(texts.HELP_ADMIN)


@admin_router.message_created(Command("sync_from_sheets"))
@admin_only
async def cmd_sync_from(event: MessageCreated, context: MemoryContext):
    await event.message.answer(texts.SYNC_STARTED)
    try:
        res = await sync_from_sheets(event.message.sender.user_id)
        await event.message.answer(f"✅ Синхронизация завершена\nДобавлено: {res['inserted']}\nОбновлено: {res['updated']}\nСкрыто: {res['deactivated']}")
    except Exception as e:
        await event.message.answer(f"Ошибка: {e}")


@admin_router.message_created(Command("sync_to_sheets"))
@admin_only
async def cmd_sync_to(event: MessageCreated, context: MemoryContext):
    await event.message.answer("Выгрузка заявок...")
    try:
        count = await sync_to_sheets(event.message.sender.user_id)
        await event.message.answer(f"✅ Выгружено заявок: {count}")
    except Exception as e:
        await event.message.answer(f"Ошибка: {e}")


@admin_router.message_created(Command("sync_status"))
@admin_only
async def cmd_sync_status(event: MessageCreated, context: MemoryContext):
    log = await db.get_last_sync()
    if log:
        await event.message.answer(f"Последняя синхронизация:\nВремя: {log['finished_at']}\nСтатус: {log['status']}\nДобавлено: {log['inserted']}\nОбновлено: {log['updated']}\nСкрыто: {log['deactivated']}")
    else:
        await event.message.answer("Синхронизаций еще не было.")


@admin_router.message_created(Command("stats"))
@admin_only
async def cmd_stats(event: MessageCreated, context: MemoryContext):
    stats = await db.get_stats()
    await event.message.answer(f"Статистика:\nПользователей: {stats['users']}\nТоваров: {stats['products']}\nЗаявок: {stats['orders']}")


@admin_router.message_created(Command("orders"))
@admin_only
async def cmd_orders(event: MessageCreated, context: MemoryContext):
    orders = await db.get_new_orders()
    if not orders:
        await event.message.answer("Новых заявок нет.")
        return
    for o in orders:
        text = texts.format_order_admin(o)
        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="✅ Принять", payload=f"admin_order_accept_{o['id']}"),
            CallbackButton(text="❌ Отклонить", payload=f"admin_order_reject_{o['id']}")
        )
        await event.message.answer(text, attachments=[builder.as_markup()])
