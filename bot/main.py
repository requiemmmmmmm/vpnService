import asyncio

from aiogram import Bot, Dispatcher

from backend.config import get_settings
from bot.handlers import router

settings = get_settings()


async def main():
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
