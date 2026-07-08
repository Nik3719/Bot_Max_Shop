from maxapi import Router
from maxapi.types import Command, MessageCreated
from maxapi.context.context import MemoryContext
from maxapi.types.attachments.buttons import ReplyButton
from maxapi.utils.keyboard import KeyboardBuilder

menu_router = Router()

def get_main_menu():
    builder = KeyboardBuilder()
    builder.row(
        ReplyButton(text="🛍 Лента товаров"),
        ReplyButton(text="📋 Мои заявки")
    )
    return builder.as_markup(resize_keyboard=True)

@menu_router.message_created()
async def process_menu(event: MessageCreated, context: MemoryContext):
    # This will be handled in handlers.py as text messages
    pass
