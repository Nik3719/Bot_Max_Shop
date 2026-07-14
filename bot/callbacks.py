import logging
from maxapi import Router
from maxapi.types import MessageCallback
from maxapi.context.context import MemoryContext
from magic_filter import F
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types.attachments.buttons import CallbackButton
from bot.handlers import show_products_page
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
        await event.bot.send_message(chat_id=chat_id, text="Товар не найден или удален.")
        return
        
    await context.update_data(buy_product_id=pid)
    await context.set_state(OrderState.WAIT_COMMENT)
    await event.answer(notification="Оформление заявки...")
    await event.bot.send_message(
        chat_id=chat_id,
        text=f"Вы оформляете заявку на: {product['name']}\n\n{texts.ASK_COMMENT}"
    )

@router.message_callback(F.callback.payload.startswith("admin_order_"))
async def process_admin_order_callback(event: MessageCallback, context: MemoryContext):
    payload = event.callback.payload
    user_id = event.callback.user.user_id
    chat_id = event.message.recipient.chat_id or user_id
    
    if user_id not in config.ADMIN_IDS:
        await event.answer(notification=texts.ADMIN_NO_ACCESS_NOTIF)
        return
        
    parts = payload.split("_")
    action = parts[2]
    order_id = int(parts[3])
    
    order_info = await db.get_order_by_id(order_id)
    if not order_info:
        await event.answer(notification=texts.ADMIN_ORDER_NOT_FOUND_NOTIF)
        return
        
    current_status = order_info['status']
    
    if current_status != 'new':
        if current_status == 'accepted':
            alert_msg = texts.ADMIN_ORDER_ALREADY_ACCEPTED
        elif current_status == 'rejected':
            alert_msg = texts.ADMIN_ORDER_ALREADY_REJECTED
        else:
            alert_msg = texts.ADMIN_ORDER_ALREADY_PROCESSED
        await event.answer(notification=alert_msg)
        return
    
    status = 'accepted' if action == 'accept' else 'rejected'
    await db.update_order_status(order_id, status)
    
    buyer_id = order_info['max_user_id']
    p_name = order_info['product_name']
    if status == 'accepted':
        msg = texts.USER_ORDER_ACCEPTED.format(order_id=order_id, p_name=p_name)
    else:
        msg = texts.USER_ORDER_REJECTED.format(order_id=order_id, p_name=p_name)
    try:
        await event.bot.send_message(user_id=buyer_id, text=msg)
    except Exception as e:
        logger.error(f"Не удалось отправить ответ пользователю {buyer_id}: {e}")
            
    await event.bot.send_message(chat_id=chat_id, text=texts.ADMIN_ORDER_STATUS_CHANGED.format(order_id=order_id, status=status))

@router.message_callback(F.callback.payload == "confirm_buy")
async def process_confirm_buy(event: MessageCallback, context: MemoryContext):
    data = await context.get_data()
    pid = data.get('buy_product_id')
    comment = data.get('buy_comment', "")
    user_id = event.callback.user.user_id
    chat_id = event.message.recipient.chat_id or user_id
    
    if not pid:
        await event.answer(notification=texts.ORDER_NOT_FOUND_NOTIF)
        return
        
    await context.clear()
        
    order_id = await db.add_order(user_id, pid, comment)
    if order_id:
        user_phone = "Неизвестно"
        user_data = await db.get_user_by_id(user_id)
        if user_data:
            user_phone = user_data['phone']
            
        await event.answer(notification=texts.ORDER_CREATED_NOTIF)
        await event.bot.send_message(
            chat_id=chat_id, 
            text=texts.ORDER_CREATED_MSG.format(order_id=order_id, phone=user_phone)
        )
        
        # Уведомление админов
        this_order = await db.get_order_by_id(order_id)
        if this_order:
            admin_text = texts.format_order_admin(this_order)
            for aid in config.ADMIN_IDS:
                try:
                    builder = InlineKeyboardBuilder()
                    builder.row(
                        CallbackButton(text="✅ Принять", payload=f"admin_order_accept_{order_id}"),
                        CallbackButton(text="❌ Отклонить", payload=f"admin_order_reject_{order_id}")
                    )
                    await event.bot.send_message(user_id=aid, text=admin_text, attachments=[builder.as_markup()])
                except Exception as e:
                    logger.error(f"Не удалось отправить уведомление админу {aid}: {e}")
    else:
        await event.bot.send_message(chat_id=chat_id, text=texts.ORDER_CREATE_ERROR)

@router.message_callback(F.callback.payload == "cancel_buy")
async def process_cancel_buy(event: MessageCallback, context: MemoryContext):
    # Очищаем контекст сразу
    data = await context.get_data()
    if not data.get('buy_product_id'):
        await event.answer(notification="Действие уже отменено")
        return
        
    await context.clear()
    
    user_id = event.callback.user.user_id
    chat_id = event.message.recipient.chat_id or user_id
    await event.answer(notification=texts.ORDER_CANCELLED_NOTIF)
    await event.bot.send_message(chat_id=chat_id, text=texts.ORDER_CANCELLED_MSG)
