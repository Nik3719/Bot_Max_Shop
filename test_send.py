import asyncio
from maxapi.bot import Bot
import config

bot = Bot(token=config.BOT_TOKEN)

async def test():
    res = await bot.send_message(user_id=179549879, text="Тестовое сообщение админу")
    print(res)

asyncio.run(test())
