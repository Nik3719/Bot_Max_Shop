import logging
from maxapi import Router
from maxapi.types import MessageCallback
from maxapi.context.context import MemoryContext
from magic_filter import F

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
        await event.answer(notification="Нет прав")
        return
        
    parts = payload.split("_")
    action = parts[2]
    order_id = int(parts[3])
    
    status = 'accepted' if action == 'accept' else 'rejected'
    await db.update_order_status(order_id, status)
    
    order_info = await db.get_order_by_id(order_id)
    if order_info:
        buyer_id = order_info['max_user_id']
        p_name = order_info['product_name']
        if status == 'accepted':
            msg = f"🎉 Ваша заявка #{order_id} на «{p_name}» принята! С вами свяжутся в ближайшее время."
        else:
            msg = f"😔 Заявка #{order_id} на «{p_name}» отклонена. Для уточнения деталей обратитесь к администратору."
        try:
            await event.bot.send_message(user_id=buyer_id, text=msg)
        except Exception as e:
            logger.error(f"Не удалось отправить ответ пользователю {buyer_id}: {e}")
            
    await event.bot.send_message(chat_id=chat_id, text=f"Заявка #{order_id} переведена в статус {status}.")
