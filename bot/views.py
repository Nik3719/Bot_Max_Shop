import math
from bot import texts
from bot.utils import build_product_keyboard, build_pagination_keyboard
import config
import db

async def show_products_page(bot, chat_id: str, page: int):
    products = await db.get_active_products()
    if not products:
        await bot.send_message(chat_id=chat_id, text=texts.NO_PRODUCTS)
        return
        
    total_pages = math.ceil(len(products) / config.ITEMS_PER_PAGE)
    if page < 1: page = 1
    if page > total_pages: page = total_pages
    
    start_idx = (page - 1) * config.ITEMS_PER_PAGE
    page_products = products[start_idx : start_idx + config.ITEMS_PER_PAGE]
    
    for p in page_products:
        text = texts.format_product(p)
        markup = build_product_keyboard(p['product_id'])
        
        if p['photo_url']:
            msg_text = f"📷 Фото: {p['photo_url']}\n{text}"
        else:
            msg_text = f"📷 Фото недоступно\n{text}"
            
        await bot.send_message(chat_id=chat_id, text=msg_text, attachments=[markup])
        
    nav_markup = build_pagination_keyboard(page, total_pages)
    await bot.send_message(chat_id=chat_id, text="Навигация:", attachments=[nav_markup])
