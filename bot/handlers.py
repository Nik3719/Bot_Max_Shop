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
from bot.utils import send_long_message, build_product_keyboard, build_pagination_keyboard
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

async def ensure_registered(event: MessageCreated, user_id: int) -> bool:
    if user_id in config.ADMIN_IDS:
        return True
    is_registered = await db.search_user(user_id)
    if not is_registered:
        await event.message.answer(texts.ACCESS_DENIED)
        return False
    return True

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

@router.message_created(Command("myorders"))
async def cmd_myorders(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    if not await ensure_registered(event, user_id):
        return
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
    
    if text in texts.ALL_MENU_BUTTONS:
        await context.clear()
        if text == texts.MENU_BTN_CATALOG:
            chat_id_to_send = event.message.recipient.chat_id or event.message.sender.user_id
            await show_products_page(event.bot, chat_id_to_send, 1)
        else:
            await cmd_myorders(event, context)
        return
    
    if text.startswith('/') and text != "/skip":
        await event.message.answer("Пожалуйста, введите текстовый комментарий или /skip.")
        return
        
    if len(text) > 500:
        await event.message.answer("Слишком длинный комментарий (максимум 500 символов). Пожалуйста, сократите его.")
        return
        
    comment = text if text != "/skip" else ""
    
    data = await context.get_data()
    pid = data.get('buy_product_id')
    user_id = event.message.sender.user_id
    
    if pid:
        await context.update_data(buy_comment=comment)
        
        product = await db.get_product_by_id(pid)
        user_data = await db.get_user_by_id(user_id)
        
        if not product or not user_data:
            await event.message.answer(texts.ORDER_DATA_ERROR)
            await context.clear()
            return
            
        final_text = texts.format_final_card(
            product_name=product['name'],
            price=product['price'],
            user_name=user_data['full_name'],
            phone=user_data['phone'],
            comment=comment
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="✅ Подтвердить", payload=f"confirm_buy_{pid}"),
            CallbackButton(text="❌ Отменить", payload=f"cancel_buy_{pid}")
        )
        
        await event.message.answer(final_text, attachments=[builder.as_markup()])
        await context.set_state(OrderState.WAIT_CONFIRM)
    else:
        await context.clear()

@router.message_created(OrderState.WAIT_CONFIRM)
async def process_wait_confirmation(event: MessageCreated, context: MemoryContext):
    await event.message.answer(texts.ORDER_CONFIRM_PROMPT)

@router.message_created()
async def process_text(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id

    is_allowed, should_warn = await check_rate_limit(user_id, event.message.timestamp)
    if not is_allowed:
        if should_warn:
            await event.message.answer(texts.SPAM_WARNING)
        return

    if not await ensure_registered(event, user_id):
        return
        
    text = event.message.body.text or ""
    if text == texts.MENU_BTN_CATALOG:
        chat_id_to_send = event.message.recipient.chat_id or event.message.sender.user_id
        await show_products_page(event.bot, chat_id_to_send, 1)
    elif text == texts.MENU_BTN_ORDERS:
        await cmd_myorders(event, context)
    else:
        if text.startswith('/'):
            await event.message.answer(texts.UNKNOWN_CMD)
