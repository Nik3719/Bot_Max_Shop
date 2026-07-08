import logging
from maxapi import Router
from maxapi.types import MessageCallback
from maxapi.context.context import MemoryContext

from bot.handlers import show_products_page
from bot.states import OrderState
from bot import texts
import db
import config

logger = logging.getLogger(__name__)
router = Router()

@router.message_callback()
async def process_callback(event: MessageCallback, context: MemoryContext):
    payload = event.callback.payload
    user_id = event.callback.user.user_id
    chat_id = event.message.recipient.chat_id or user_id
    
    if payload == "noop":
        return
        
    if payload.startswith("page_"):
        page = int(payload.split("_")[1])
        await show_products_page(event, page)
        
    elif payload.startswith("buy_"):
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
        
    elif payload.startswith("admin_order_"):
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
