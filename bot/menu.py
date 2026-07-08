from maxapi import Router
from maxapi.types import Command, MessageCreated
from maxapi.context.context import MemoryContext
from maxapi.types.attachments.buttons import MessageButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

menu_router = Router()

def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        MessageButton(text="🛍 Лента товаров"),
        MessageButton(text="📋 Мои заявки")
    )
    return builder.as_markup()

