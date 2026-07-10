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
