import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# آیدی عددی تلگرام مالک اصلی ربات (همیشه دسترسی کامل داره، غیرقابل حذف)
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

DB_PATH = os.getenv("DB_PATH", "/data/dragonshop.db")

CHANNEL_LOCK_ID = os.getenv("CHANNEL_LOCK_ID", "")  # اختیاری: یوزرنیم کانال جوین اجباری، خالی = غیرفعال

CURRENCY = "تومان"

# درصد پورسانت پیش‌فرض سیستم زیرمجموعه‌گیری (قابل تغییر از پنل ادمین)
DEFAULT_REFERRAL_PERCENT = 5

