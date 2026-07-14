import logging
from maxapi import Router
from maxapi.types import MessageCallback
from maxapi.context.context import MemoryContext
from magic_filter import F
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types.attachments.buttons import CallbackButton
from bot.utils import ensure_admin_callback, get_status_alert_message, notify_user_order_processed, finalize_order
from bot.views import show_products_page
from bot.states import OrderState
from bot import texts
import db
import config

logger = logging.getLogger(__name__)
router = Router()

@router.message_callback(F.callback.payload == "noop")
async def process_noop_callback(event: MessageCallback, context: MemoryContext):
    return

@router.message_callback(F.callback.payload.startswith("page_"))
async def process_page_callback(event: MessageCallback, context: MemoryContext):
    payload = event.callback.payload
    page = int(payload.split("_")[1])
    
    user_id = event.callback.user.user_id
    chat_id = event.message.recipient.chat_id or user_id
    
    try:
        await event.answer()
    except Exception as e:
        logger.warning(f"Не удалось ответить на коллбэк: {e}")
        
    await show_products_page(event.bot, chat_id, page)

@router.message_callback(F.callback.payload.startswith("buy_"))
async def process_buy_callback(event: MessageCallback, context: MemoryContext):
    payload = event.callback.payload
    user_id = event.callback.user.user_id
    chat_id = event.message.recipient.chat_id or user_id
    
    pid = payload[4:]
    product = await db.get_product_by_id(pid)
    if not product:
        await event.bot.send_message(chat_id=chat_id, text=texts.PRODUCT_NOT_FOUND_OR_DELETED)
        return
        
    await context.update_data(buy_product_id=pid, buy_comment="")
    await context.set_state(OrderState.WAIT_COMMENT)
    await event.answer(notification=texts.ORDERING_PROCESS_NOTIF)
    await event.bot.send_message(
        chat_id=chat_id,
        text=texts.ORDERING_PROMPT.format(p_name=product['name'], ask_comment=texts.ASK_COMMENT)
    )

@router.message_callback(F.callback.payload.startswith("admin_order_"))
async def process_admin_order_callback(event: MessageCallback, context: MemoryContext):
    payload = event.callback.payload
    chat_id = event.message.recipient.chat_id or event.callback.user.user_id
    
    if not await ensure_admin_callback(event, chat_id):
        return
        
    parts = payload.split("_")
    action = parts[2]
    order_id = int(parts[3])
    
    order_info = await db.get_order_by_id(order_id)
    if not order_info:
        await event.answer()
        await event.bot.send_message(chat_id=chat_id, text=texts.ADMIN_ORDER_NOT_FOUND_NOTIF)
        return
        
    current_status = order_info['status']
    if current_status != 'new':
        alert_msg = get_status_alert_message(current_status)
        await event.answer()
        await event.bot.send_message(chat_id=chat_id, text=alert_msg)
        return
    
    status = 'accepted' if action == 'accept' else 'rejected'
    await db.update_order_status(order_id, status)
    
    await notify_user_order_processed(event.bot, order_info['max_user_id'], order_id, order_info['product_name'], status)
    await event.bot.send_message(chat_id=chat_id, text=texts.ADMIN_ORDER_STATUS_CHANGED.format(order_id=order_id, status=status))

@router.message_callback(F.callback.payload.startswith("confirm_buy_"))
async def process_confirm_buy(event: MessageCallback, context: MemoryContext):
    data = await context.get_data()
    pid = data.get('buy_product_id')
    comment = data.get('buy_comment', "")
    user_id = event.callback.user.user_id
    chat_id = event.message.recipient.chat_id or user_id
    
    payload_pid = event.callback.payload.replace("confirm_buy_", "")
    
    if not pid or pid != payload_pid:
        await event.answer()
        await event.bot.send_message(chat_id=chat_id, text=texts.CARD_OUTDATED_NOTIF)
        return
        
    # очищаем контекст до любых await-запросов к БД.
    await context.clear()
    
    # проверка актуальности товара
    product = await db.get_product_by_id(pid)
    if not product:
        await event.bot.send_message(chat_id=chat_id, text=texts.PRODUCT_NOT_FOUND_OR_DELETED)
        return
        
    await finalize_order(event, user_id, chat_id, pid, comment)

@router.message_callback(F.callback.payload.startswith("cancel_buy_"))
async def process_cancel_buy(event: MessageCallback, context: MemoryContext):
    payload_pid = event.callback.payload.replace("cancel_buy_", "")
    data = await context.get_data()
    pid = data.get('buy_product_id')
    
    user_id = event.callback.user.user_id
    chat_id = event.message.recipient.chat_id or user_id
    
    if not pid or pid != payload_pid:
        await event.answer()
        await event.bot.send_message(chat_id=chat_id, text=texts.CARD_OUTDATED_CANCEL_NOTIF)
        return
        
    await context.clear()
    
    await event.answer()
    await event.bot.send_message(chat_id=chat_id, text=texts.ORDER_CANCELLED_MSG)
