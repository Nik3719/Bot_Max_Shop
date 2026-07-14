from maxapi.types import MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types.attachments.buttons import CallbackButton

async def send_long_message(event: MessageCreated, text: str, max_len: int = 3000):
    if len(text) <= max_len:
        await event.message.answer(text)
        return

    paragraphs = text.split('\n')
    current_msg = ""
    for p in paragraphs:
        p_len = len(p) + (1 if current_msg else 0)
        if len(current_msg) + p_len <= max_len:
            current_msg += ("\n" + p) if current_msg else p
        else:
            if current_msg:
                await event.message.answer(current_msg)
                current_msg = ""
            if len(p) > max_len:
                for i in range(0, len(p), max_len):
                    await event.message.answer(p[i : i + max_len])
            else:
                current_msg = p
    if current_msg:
        await event.message.answer(current_msg)

def build_product_keyboard(product_id: str) -> list:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="🛒 Оформить заявку", payload=f"buy_{product_id}"))
    return builder.as_markup()

def build_pagination_keyboard(page: int, total_pages: int) -> list:
    builder = InlineKeyboardBuilder()
    row = []
    if page > 1:
        row.append(CallbackButton(text="← Назад", payload=f"page_{page-1}"))
    row.append(CallbackButton(text=f"Стр. {page} / {total_pages}", payload="noop"))
    if page < total_pages:
        row.append(CallbackButton(text="Вперёд →", payload=f"page_{page+1}"))
    
    builder.row(*row)
    return builder.as_markup()

async def ensure_admin_callback(event, chat_id: str) -> bool:
    import config
    from bot import texts
    if event.callback.user.user_id not in config.ADMIN_IDS:
        await event.answer()
        await event.bot.send_message(chat_id=chat_id, text=texts.ADMIN_NO_ACCESS_NOTIF)
        return False
    return True

def get_status_alert_message(current_status: str) -> str:
    from bot import texts
    if current_status == 'accepted':
        return texts.ADMIN_ORDER_ALREADY_ACCEPTED
    elif current_status == 'rejected':
        return texts.ADMIN_ORDER_ALREADY_REJECTED
    return texts.ADMIN_ORDER_ALREADY_PROCESSED

async def notify_user_order_processed(bot, buyer_id: int, order_id: int, p_name: str, status: str):
    import logging
    from bot import texts
    logger = logging.getLogger(__name__)
    if status == 'accepted':
        msg = texts.USER_ORDER_ACCEPTED.format(order_id=order_id, p_name=p_name)
    else:
        msg = texts.USER_ORDER_REJECTED.format(order_id=order_id, p_name=p_name)
    try:
        await bot.send_message(user_id=buyer_id, text=msg)
    except Exception as e:
        logger.error(f"Не удалось отправить ответ пользователю {buyer_id}: {e}")

async def notify_admins_new_order(bot, order_id: int):
    import logging
    import db
    import config
    from bot import texts
    from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
    from maxapi.types.attachments.buttons import CallbackButton
    
    logger = logging.getLogger(__name__)
    this_order = await db.get_order_by_id(order_id)
    if not this_order:
        return
        
    admin_text = texts.format_order_admin(this_order)
    for aid in config.ADMIN_IDS:
        try:
            builder = InlineKeyboardBuilder()
            builder.row(
                CallbackButton(text="✅ Принять", payload=f"admin_order_accept_{order_id}"),
                CallbackButton(text="❌ Отклонить", payload=f"admin_order_reject_{order_id}")
            )
            await bot.send_message(user_id=aid, text=admin_text, attachments=[builder.as_markup()])
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу {aid}: {e}")

async def finalize_order(event, user_id: int, chat_id: str, pid: str, comment: str):
    import db
    from bot import texts
    
    order_id = await db.add_order(user_id, pid, comment)
    if order_id:
        user_phone = texts.UNKNOWN_PHONE
        user_data = await db.get_user_by_id(user_id)
        if user_data:
            user_phone = user_data['phone']
            
        await event.answer(notification=texts.ORDER_CREATED_NOTIF)
        await event.bot.send_message(
            chat_id=chat_id, 
            text=texts.ORDER_CREATED_MSG.format(order_id=order_id, phone=user_phone)
        )
        
        # Уведомление админов
        await notify_admins_new_order(event.bot, order_id)
    else:
        await event.bot.send_message(chat_id=chat_id, text=texts.ORDER_CREATE_ERROR)
