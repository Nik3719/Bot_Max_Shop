import logging
import math
from maxapi.types import BotStarted, Command, MessageCreated
from maxapi import Router
from maxapi.context.context import MemoryContext
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types.attachments.buttons import CallbackButton

import config
from bot import texts
from bot.states import RegState, OrderState
from bot.validators import validate_name, validate_and_clean_phone
from bot.menu import get_main_menu
from bot.utils import send_long_message
import db

logger = logging.getLogger(__name__)
router = Router()

user_last_message_time: dict[int, float] = {}
user_last_warning_time: dict[int, float] = {}

async def check_rate_limit(user_id: int, message_timestamp: int) -> tuple[bool, bool]:
    ts_sec = message_timestamp / 1000
    last_time = user_last_message_time.get(user_id, 0)
    
    if ts_sec - last_time < 3:
        last_warning = user_last_warning_time.get(user_id, 0)
        if ts_sec - last_warning >= 5:
            user_last_warning_time[user_id] = ts_sec
            return False, True
        return False, False

    user_last_message_time[user_id] = ts_sec
    return True, False

@router.bot_started()
async def bot_started(event: BotStarted, context: MemoryContext):
    logger.info(f"Событие bot_started для пользователя {event.user.user_id}")

# --- РЕГИСТРАЦИЯ ---
@router.message_created(Command("start"))
async def cmd_start(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    is_registered = await db.search_user(user_id)

    if is_registered:
        await context.clear()
        await event.message.answer(texts.REG_ALREADY, attachments=[get_main_menu()])
    else:
        await event.message.answer(texts.REG_WELCOME)
        await context.set_state(RegState.WAIT_NAME)

@router.message_created(RegState.WAIT_NAME)
async def process_name(event: MessageCreated, context: MemoryContext):
    text = event.message.body.text or ""
    if not validate_name(text):
        await event.message.answer(texts.REG_INVALID_NAME)
        return
    await context.update_data(full_name=text)
    await event.message.answer(texts.REG_ASK_PHONE)
    await context.set_state(RegState.WAIT_PHONE)

@router.message_created(RegState.WAIT_PHONE)
async def process_phone(event: MessageCreated, context: MemoryContext):
    text = event.message.body.text or ""
    cleaned_phone = validate_and_clean_phone(text)
    if not cleaned_phone:
        await event.message.answer(texts.REG_INVALID_PHONE)
        return

    if await db.is_phone_registered(cleaned_phone):
        await event.message.answer(texts.REG_PHONE_EXISTS)
        return

    data = await context.get_data()
    user_dict = {
        "max_user_id": event.message.sender.user_id,
        "full_name": data["full_name"],
        "phone": cleaned_phone,
    }

    try:
        await db.add_user(user_dict)
        await context.clear()
        await event.message.answer(texts.REG_SUCCESS, attachments=[get_main_menu()])
    except Exception as e:
        logger.error(f"Ошибка при сохранении пользователя: {e}")
        await event.message.answer(texts.REG_ERROR)

@router.message_created(Command("help"))
async def cmd_help(event: MessageCreated, context: MemoryContext):
    await event.message.answer(texts.HELP_USER)

# --- МАГАЗИН ---
async def show_products_page(event, page: int):
    products = await db.get_active_products()
    if not products:
        try:
            await event.message.answer(texts.NO_PRODUCTS)
        except AttributeError:
            await event.bot.send_message(chat_id=event.recipient.chat_id, text=texts.NO_PRODUCTS)
        return
        
    total_pages = math.ceil(len(products) / config.ITEMS_PER_PAGE)
    if page < 1: page = 1
    if page > total_pages: page = total_pages
    
    start_idx = (page - 1) * config.ITEMS_PER_PAGE
    page_products = products[start_idx : start_idx + config.ITEMS_PER_PAGE]
    
    for p in page_products:
        text = texts.format_product(p)
        builder = InlineKeyboardBuilder()
        builder.row(CallbackButton(text="🛒 Оформить заявку", payload=f"buy_{p['product_id']}"))
        markup = builder.as_markup()
        
        chat_id_to_send = None
        try:
            chat_id_to_send = event.message.recipient.chat_id or event.message.sender.user_id
        except AttributeError:
            chat_id_to_send = event.recipient.chat_id or event.sender.user_id
            
        if p['photo_url']:
            await event.bot.send_message(chat_id=chat_id_to_send, text=f"📷 Фото: {p['photo_url']}\n{text}", attachments=[markup])
        else:
            await event.bot.send_message(chat_id=chat_id_to_send, text=f"📷 Фото недоступно\n{text}", attachments=[markup])
            
    # Navigation
    nav_builder = InlineKeyboardBuilder()
    row = []
    if page > 1:
        row.append(CallbackButton(text="← Назад", payload=f"page_{page-1}"))
    row.append(CallbackButton(text=f"Стр. {page} / {total_pages}", payload="noop"))
    if page < total_pages:
        row.append(CallbackButton(text="Вперёд →", payload=f"page_{page+1}"))
    
    nav_builder.row(*row)
    
    try:
        await event.message.answer("Навигация:", attachments=[nav_builder.as_markup()])
    except AttributeError:
        await event.bot.send_message(chat_id=chat_id_to_send, text="Навигация:", attachments=[nav_builder.as_markup()])

@router.message_created(Command("myorders"))
async def cmd_myorders(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    orders = await db.get_user_orders(user_id)
    if not orders:
        await event.message.answer("У вас еще нет заявок.")
        return
    
    res = "📋 Ваши заявки:\n\n"
    for o in orders:
        status_map = {'new': '🕐 Ожидает', 'viewed': '👀 Просмотрена', 'accepted': '✅ Принята', 'rejected': '❌ Отклонена'}
        res += f"#{o['id']} | {o['product_name']} | {o['price']} ₽ | {status_map.get(o['status'], o['status'])} | {o['created_at']}\n"
    await send_long_message(event, res)

@router.message_created(OrderState.WAIT_COMMENT)
async def process_order_comment(event: MessageCreated, context: MemoryContext):
    text = event.message.body.text or ""
    comment = text if text != "/skip" else ""
    
    data = await context.get_data()
    pid = data.get('buy_product_id')
    user_id = event.message.sender.user_id
    
    if pid:
        order_id = await db.add_order(user_id, pid, comment)
        if order_id:
            user_phone = "Неизвестно"
            user_data = await db.get_user_by_id(user_id)
            if user_data:
                user_phone = user_data['phone']
                
            await event.message.answer(f"✅ Заявка #{order_id} оформлена! Мы свяжемся с вами по номеру {user_phone}. Ожидайте звонка.")
            
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
            await event.message.answer("Ошибка при создании заявки.")
            
    await context.clear()

@router.message_created()
async def process_text(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id

    is_allowed, should_warn = await check_rate_limit(user_id, event.message.timestamp)
    if not is_allowed:
        if should_warn:
            await event.message.answer(texts.SPAM_WARNING)
        return

    if user_id not in config.ADMIN_IDS and not await db.search_user(user_id):
        await event.message.answer(texts.ACCESS_DENIED)
        return
        
    text = event.message.body.text or ""
    if text == "🛍 Лента товаров":
        await show_products_page(event, 1)
    elif text == "📋 Мои заявки":
        await cmd_myorders(event, context)
    else:
        if text.startswith('/'):
            await event.message.answer(texts.UNKNOWN_CMD)
