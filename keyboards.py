from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def phone_request_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 ارسال شماره تلفن من", request_contact=True)]],
        resize_keyboard=True,
    )


def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="🛍 منوی محصولات")],
        [KeyboardButton(text="💰 افزایش موجودی"), KeyboardButton(text="👤 حساب کاربری")],
        [KeyboardButton(text="🤝 زیرمجموعه‌گیری"), KeyboardButton(text="🧾 تاریخچه سفارشات")],
        [KeyboardButton(text="🆘 پشتیبانی")],
    ]
    if is_admin:
        kb.append([KeyboardButton(text="⚙️ پنل مدیریت")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def back_kb(text="⬅️ بازگشت") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=text)]], resize_keyboard=True)


def categories_kb(categories) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in categories:
        b.button(text=f"{c['emoji']} {c['title']}", callback_data=f"cat:{c['id']}")
    b.adjust(2)
    return b.as_markup()


def products_kb(products, category_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in products:
        b.button(text=f"{p['title']} — {p['price']:,} تومان", callback_data=f"prod:{p['id']}")
    b.button(text="⬅️ بازگشت به دسته‌ها", callback_data="back_categories")
    b.adjust(1)
    return b.as_markup()


def confirm_buy_kb(product_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ تایید و پرداخت از کیف پول", callback_data=f"confirm_buy:{product_id}")
    b.button(text="❌ انصراف", callback_data="cancel_buy")
    b.adjust(1)
    return b.as_markup()


def topup_method_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="💳 کارت به کارت", callback_data="topup_method:card")
    b.button(text="🪙 کریپتو (USDT)", callback_data="topup_method:crypto")
    b.adjust(1)
    return b.as_markup()


def wallet_review_kb(req_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ تایید و شارژ", callback_data=f"wallet_approve:{req_id}")
    b.button(text="❌ رد کردن", callback_data=f"wallet_reject:{req_id}")
    b.adjust(2)
    return b.as_markup()


# ---------- Admin ----------
def admin_main_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📂 مدیریت دسته‌ها", callback_data="adm_cats")
    b.button(text="💳 درخواست‌های شارژ", callback_data="adm_wallet_reqs")
    b.button(text="📦 مدیریت استوک", callback_data="adm_stock_cats")
    b.button(text="👥 مدیریت ادمین‌ها", callback_data="adm_admins")
    b.button(text="👤 مدیریت کاربران", callback_data="adm_users")
    b.button(text="⚙️ تنظیمات پرداخت", callback_data="adm_settings")
    b.button(text="📊 آمار فروش", callback_data="adm_stats")
    b.button(text="📢 ارسال پیام همگانی", callback_data="adm_broadcast")
    b.adjust(2)
    return b.as_markup()


def admin_categories_kb(categories) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in categories:
        status = "🟢" if c["is_active"] else "🔴"
        b.button(text=f"{status} {c['emoji']} {c['title']}", callback_data=f"adm_cat:{c['id']}")
    b.button(text="➕ افزودن دسته جدید", callback_data="adm_cat_add")
    b.button(text="⬅️ بازگشت", callback_data="adm_back")
    b.adjust(1)
    return b.as_markup()


def admin_category_detail_kb(cat) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📦 محصولات این دسته", callback_data=f"adm_prods:{cat['id']}")
    b.button(text="✏️ ویرایش نام", callback_data=f"adm_cat_edit_title:{cat['id']}")
    b.button(text="🔄 ویرایش ایموجی", callback_data=f"adm_cat_edit_emoji:{cat['id']}")
    label = "🔴 غیرفعال کردن" if cat["is_active"] else "🟢 فعال کردن"
    b.button(text=label, callback_data=f"adm_cat_toggle:{cat['id']}")
    b.button(text="🗑 حذف کامل (دائمی)", callback_data=f"adm_cat_delete_confirm:{cat['id']}")
    b.button(text="⬅️ بازگشت", callback_data="adm_cats")
    b.adjust(1)
    return b.as_markup()


def admin_products_kb(products, cat_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in products:
        status = "🟢" if p["is_active"] else "🔴"
        b.button(text=f"{status} {p['title']} ({p['price']:,})", callback_data=f"adm_prod:{p['id']}")
    b.button(text="➕ افزودن محصول جدید", callback_data=f"adm_prod_add:{cat_id}")
    b.button(text="⬅️ بازگشت به دسته", callback_data=f"adm_cat:{cat_id}")
    b.adjust(1)
    return b.as_markup()


def admin_product_detail_kb(prod) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ ویرایش نام", callback_data=f"adm_prod_edit_title:{prod['id']}")
    b.button(text="💰 ویرایش قیمت", callback_data=f"adm_prod_edit_price:{prod['id']}")
    b.button(text="📝 ویرایش توضیحات", callback_data=f"adm_prod_edit_desc:{prod['id']}")
    target_label = "🔕 غیرفعال کردن دریافت اطلاعات" if prod["needs_target"] else "📥 فعال کردن دریافت اطلاعات از کاربر"
    b.button(text=target_label, callback_data=f"adm_prod_toggle_target:{prod['id']}")
    if prod["needs_target"]:
        b.button(text="✏️ ویرایش متن سوال", callback_data=f"adm_prod_edit_prompt:{prod['id']}")
    b.button(text="📦 افزودن استوک", callback_data=f"adm_prod_add_stock:{prod['id']}")
    label = "🔴 غیرفعال کردن" if prod["is_active"] else "🟢 فعال کردن"
    b.button(text=label, callback_data=f"adm_prod_toggle:{prod['id']}")
    b.button(text="🗑 حذف کامل (دائمی)", callback_data=f"adm_prod_delete_confirm:{prod['id']}")
    b.button(text="⬅️ بازگشت", callback_data=f"adm_prods:{prod['category_id']}")
    b.adjust(1)
    return b.as_markup()


def confirm_delete_kb(yes_cb: str, no_cb: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⚠️ بله، حذف دائمی شود", callback_data=yes_cb)
    b.button(text="انصراف", callback_data=no_cb)
    b.adjust(1)
    return b.as_markup()


def admin_settings_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🏷 نام فروشگاه (برند)", callback_data="adm_set:shop_name")
    b.button(text="💬 متن خوش‌آمدگویی", callback_data="adm_set:welcome_message")
    b.button(text="🆘 آیدی پشتیبانی", callback_data="adm_set:support_contact")
    b.button(text="💳 شماره کارت", callback_data="adm_set:card_number")
    b.button(text="👤 نام صاحب کارت", callback_data="adm_set:card_holder")
    b.button(text="🪙 آدرس کیف پول کریپتو", callback_data="adm_set:crypto_address")
    b.button(text="🌐 شبکه کریپتو", callback_data="adm_set:crypto_network")
    b.button(text="🤝 درصد پورسانت رفرال", callback_data="adm_set:referral_percent")
    b.button(text="💵 حداقل مبلغ شارژ", callback_data="adm_set:min_topup")
    b.button(text="📢 کانال جوین اجباری", callback_data="adm_set:force_join_channel")
    b.button(text="⬅️ بازگشت", callback_data="adm_back")
    b.adjust(1)
    return b.as_markup()


def cancel_inline_kb(cb="adm_back") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="انصراف", callback_data=cb)
    return b.as_markup()
