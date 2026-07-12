import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

import config
import database as db
from handlers import admin, user

logging.basicConfig(level=logging.INFO)


async def main():
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN تنظیم نشده! متغیر محیطی BOT_TOKEN رو ست کن.")
    if not config.OWNER_ID:
        raise RuntimeError("OWNER_ID تنظیم نشده! آیدی عددی تلگرام خودت رو در متغیر محیطی OWNER_ID بذار.")

    os.makedirs(os.path.dirname(config.DB_PATH) or ".", exist_ok=True)
    await db.init_db()

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())

    # ترتیب مهمه: هندلرهای ادمین باید اول چک بشن تا استیت‌های ادمین درست تشخیص داده بشن
    dp.include_router(admin.router)
    dp.include_router(user.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
