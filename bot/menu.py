from maxapi import Router
from maxapi.types import Command, MessageCreated
from maxapi.context.context import MemoryContext
from maxapi.types.attachments.buttons import MessageButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from bot import texts

menu_router = Router()

def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        MessageButton(text=texts.MENU_BTN_CATALOG),
        MessageButton(text=texts.MENU_BTN_ORDERS)
    )
    return builder.as_markup()

