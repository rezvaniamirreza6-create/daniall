from aiogram import Bot
import database as db
import config


async def notify_admins(bot: Bot, text: str, reply_markup=None):
    ids = {config.OWNER_ID}
    for row in await db.list_admins():
        ids.add(row["user_id"])
    for admin_id in ids:
        if not admin_id:
            continue
        try:
            await bot.send_message(admin_id, text, reply_markup=reply_markup)
        except Exception:
            pass


async def notify_admins_photo(bot: Bot, file_id: str, caption: str, reply_markup=None):
    ids = {config.OWNER_ID}
    for row in await db.list_admins():
        ids.add(row["user_id"])
    for admin_id in ids:
        if not admin_id:
            continue
        try:
            await bot.send_photo(admin_id, file_id, caption=caption, reply_markup=reply_markup)
        except Exception:
            pass


def fmt_money(n: int) -> str:
    return f"{n:,} {config.CURRENCY}"
