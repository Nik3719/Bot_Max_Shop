import logging
from maxapi import Router
from maxapi.types import CallbackQueryCreated
from maxapi.context.context import MemoryContext

from bot.handlers import show_products_page
from bot.states import OrderState
from bot import texts
import db
import config

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query_created()
async def process_callback(event: CallbackQueryCreated, context: MemoryContext):
    payload = event.query.payload
    user_id = event.query.sender.user_id
    chat_id = event.query.recipient.chat_id or user_id
    
    if payload == "noop":
        return
        
    if payload.startswith("page_"):
        page = int(payload.split("_")[1])
        await show_products_page(event.query, page)
        
    elif payload.startswith("buy_"):
        pid = payload[4:]
        product = await db.get_product_by_id(pid)
        if not product:
            await event.bot.send_message(chat_id=chat_id, text="Товар не найден или удален.")
            return
            
        await context.update_data(buy_product_id=pid)
        await context.set_state(OrderState.WAIT_COMMENT)
        await event.bot.send_message(
            chat_id=chat_id,
            text=f"Вы оформляете заявку на: {product['name']}\n\n{texts.ASK_COMMENT}"
        )
        
    elif payload.startswith("admin_order_"):
        if user_id not in config.ADMIN_IDS:
            await event.bot.send_message(chat_id=chat_id, text="Нет прав")
            return
            
        parts = payload.split("_")
        action = parts[2]
        order_id = int(parts[3])
        
        status = 'accepted' if action == 'accept' else 'rejected'
        await db.update_order_status(order_id, status)
        
        await event.bot.send_message(chat_id=chat_id, text=f"Заявка #{order_id} переведена в статус {status}.")
