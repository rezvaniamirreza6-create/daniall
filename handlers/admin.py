from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
import config
from states import AdminCategory, AdminProduct, AdminSettings, AdminBroadcast, AdminManage
from utils import fmt_money

router = Router()


async def admin_only(user_id: int) -> bool:
    return await db.is_admin(user_id, config.OWNER_ID)


@router.message(Command("admin"))
@router.message(F.text == "⚙️ پنل مدیریت")
async def open_admin_panel(message: Message, state: FSMContext):
    if not await admin_only(message.from_user.id):
        return
    await state.clear()
    await message.answer("⚙️ <b>پنل مدیریت Dragon Shop</b>", reply_markup=kb.admin_main_kb(), parse_mode="HTML")


@router.callback_query(F.data == "adm_cancel")
async def cb_admin_cancel(call: CallbackQuery, state: FSMContext):
    if not await admin_only(call.from_user.id):
        return
    await state.clear()
    try:
        await call.message.edit_text("❌ لغو شد.\n\n⚙️ <b>پنل مدیریت Dragon Shop</b>", reply_markup=kb.admin_main_kb(), parse_mode="HTML")
    except Exception:
        await call.message.answer("⚙️ <b>پنل مدیریت Dragon Shop</b>", reply_markup=kb.admin_main_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "adm_back")
async def cb_admin_back(call: CallbackQuery, state: FSMContext):
    if not await admin_only(call.from_user.id):
        return
    await state.clear()
    await call.message.edit_text("⚙️ <b>پنل مدیریت Dragon Shop</b>", reply_markup=kb.admin_main_kb(), parse_mode="HTML")
    await call.answer()


# =============== دسته‌ها ===============
@router.callback_query(F.data == "adm_cats")
async def cb_admin_cats(call: CallbackQuery):
    if not await admin_only(call.from_user.id):
        return
    cats = await db.list_categories(only_active=False)
    await call.message.edit_text(
        "📂 <b>مدیریت دسته‌ها</b>\n🟢 فعال | 🔴 غیرفعال\nروی هرکدوم بزن برای مدیریت:",
        reply_markup=kb.admin_categories_kb(cats), parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "adm_cat_add")
async def cb_admin_cat_add(call: CallbackQuery, state: FSMContext):
    if not await admin_only(call.from_user.id):
        return
    await state.set_state(AdminCategory.waiting_title)
    await call.message.answer("نام دسته‌ی جدید رو بفرست:", reply_markup=kb.cancel_inline_kb("adm_cats"))
    await call.answer()


@router.message(AdminCategory.waiting_title)
async def admin_cat_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AdminCategory.waiting_emoji)
    await message.answer("یه ایموجی برای این دسته بفرست (مثلاً 🎁):", reply_markup=kb.cancel_inline_kb("adm_cancel"))


@router.message(AdminCategory.waiting_emoji)
async def admin_cat_emoji(message: Message, state: FSMContext):
    data = await state.get_data()
    cat_id = await db.create_category(data["title"], message.text.strip())
    await state.clear()
    await message.answer(f"✅ دسته «{data['title']}» ساخته شد.")
    cats = await db.list_categories(only_active=False)
    await message.answer("📂 مدیریت دسته‌ها:", reply_markup=kb.admin_categories_kb(cats))


@router.callback_query(F.data.startswith("adm_cat:"))
async def cb_admin_cat_detail(call: CallbackQuery):
    if not await admin_only(call.from_user.id):
        return
    cat_id = int(call.data.split(":")[1])
    cat = await db.get_category(cat_id)
    if not cat:
        await call.answer("پیدا نشد.", show_alert=True)
        return
    products = await db.list_products(cat_id, only_active=False)
    status = "🟢 فعال" if cat["is_active"] else "🔴 غیرفعال"
    await call.message.edit_text(
        f"{cat['emoji']} <b>{cat['title']}</b>\nوضعیت: {status}\nتعداد محصولات: {len(products)}",
        reply_markup=kb.admin_category_detail_kb(cat), parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_cat_toggle:"))
async def cb_admin_cat_toggle(call: CallbackQuery):
    if not await admin_only(call.from_user.id):
        return
    cat_id = int(call.data.split(":")[1])
    await db.toggle_category(cat_id)
    cat = await db.get_category(cat_id)
    await call.answer("وضعیت تغییر کرد ✅")
    products = await db.list_products(cat_id, only_active=False)
    status = "🟢 فعال" if cat["is_active"] else "🔴 غیرفعال"
    await call.message.edit_text(
        f"{cat['emoji']} <b>{cat['title']}</b>\nوضعیت: {status}\nتعداد محصولات: {len(products)}",
        reply_markup=kb.admin_category_detail_kb(cat), parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("adm_cat_edit_title:"))
async def cb_admin_cat_edit_title(call: CallbackQuery, state: FSMContext):
    if not await admin_only(call.from_user.id):
        return
    cat_id = int(call.data.split(":")[1])
    await state.update_data(cat_id=cat_id)
    await state.set_state(AdminCategory.edit_title)
    await call.message.answer("نام جدید دسته رو بفرست:", reply_markup=kb.cancel_inline_kb(f"adm_cat:{cat_id}"))
    await call.answer()


@router.message(AdminCategory.edit_title)
async def admin_cat_edit_title_recv(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.update_category(data["cat_id"], title=message.text.strip())
    await state.clear()
    await message.answer("✅ نام دسته بروزرسانی شد.")


@router.callback_query(F.data.startswith("adm_cat_edit_emoji:"))
async def cb_admin_cat_edit_emoji(call: CallbackQuery, state: FSMContext):
    if not await admin_only(call.from_user.id):
        return
    cat_id = int(call.data.split(":")[1])
    await state.update_data(cat_id=cat_id)
    await state.set_state(AdminCategory.edit_emoji)
    await call.message.answer("ایموجی جدید رو بفرست:", reply_markup=kb.cancel_inline_kb(f"adm_cat:{cat_id}"))
    await call.answer()


@router.message(AdminCategory.edit_emoji)
async def admin_cat_edit_emoji_recv(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.update_category(data["cat_id"], emoji=message.text.strip())
    await state.clear()
    await message.answer("✅ ایموجی دسته بروزرسانی شد.")


@router.callback_query(F.data.startswith("adm_cat_delete_confirm:"))
async def cb_admin_cat_delete_confirm(call: CallbackQuery):
    if not await admin_only(call.from_user.id):
        return
    cat_id = int(call.data.split(":")[1])
    await call.message.edit_text(
        "⚠️ توجه: حذف دائمی این دسته، تمام محصولات و سابقه‌ی استوک اون رو هم از دیتابیس پاک می‌کنه و قابل بازگشت نیست.\n\n"
        "اگه فقط می‌خوای موقتاً از دید کاربر پنهون بشه، به‌جاش از گزینه‌ی «غیرفعال کردن» استفاده کن.\n\n"
        "مطمئنی؟",
        reply_markup=kb.confirm_delete_kb(f"adm_cat_delete:{cat_id}", f"adm_cat:{cat_id}"),
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_cat_delete:"))
async def cb_admin_cat_delete(call: CallbackQuery):
    if not await admin_only(call.from_user.id):
        return
    cat_id = int(call.data.split(":")[1])
    await db.delete_category_hard(cat_id)
    await call.answer("حذف شد.")
    cats = await db.list_categories(only_active=False)
    await call.message.edit_text("📂 مدیریت دسته‌ها:", reply_markup=kb.admin_categories_kb(cats))


# =============== محصولات ===============
@router.callback_query(F.data.startswith("adm_prods:"))
async def cb_admin_prods(call: CallbackQuery):
    if not await admin_only(call.from_user.id):
        return
    cat_id = int(call.data.split(":")[1])
    products = await db.list_products(cat_id, only_active=False)
    cat = await db.get_category(cat_id)
    await call.message.edit_text(
        f"📦 محصولات دسته‌ی «{cat['title']}»:\n🟢 فعال | 🔴 غیرفعال",
        reply_markup=kb.admin_products_kb(products, cat_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_prod_add:"))
async def cb_admin_prod_add(call: CallbackQuery, state: FSMContext):
    if not await admin_only(call.from_user.id):
        return
    cat_id = int(call.data.split(":")[1])
    await state.update_data(cat_id=cat_id)
    await state.set_state(AdminProduct.waiting_title)
    await call.message.answer("نام محصول جدید رو بفرست (مثلاً «پرمیوم ۳ ماهه»):", reply_markup=kb.cancel_inline_kb(f"adm_prods:{cat_id}"))
    await call.answer()


@router.message(AdminProduct.waiting_title)
async def admin_prod_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AdminProduct.waiting_price)
    await message.answer("قیمت این محصول رو به تومان بفرست (فقط عدد):", reply_markup=kb.cancel_inline_kb("adm_cancel"))


@router.message(AdminProduct.waiting_price)
async def admin_prod_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("لطفاً فقط عدد بفرست.", reply_markup=kb.cancel_inline_kb("adm_cancel"))
        return
    await state.update_data(price=int(message.text))
    await state.set_state(AdminProduct.waiting_description)
    await message.answer("توضیحات محصول رو بفرست (یا بنویس «-» برای رد کردن):", reply_markup=kb.cancel_inline_kb("adm_cancel"))


@router.message(AdminProduct.waiting_description)
async def admin_prod_desc(message: Message, state: FSMContext):
    desc = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(description=desc)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="✅ بله، لازمه", callback_data="adm_newprod_target:yes")
    b.button(text="❌ نه، لازم نیست", callback_data="adm_newprod_target:no")
    b.adjust(1)
    await message.answer(
        "آیا برای این محصول لازمه از کاربر اطلاعاتی بگیریم؟\n"
        "(مثلاً یوزرنیم اکانتی که باید پرمیوم روش فعال بشه، یا شماره کانفیگ VPN)",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data.startswith("adm_newprod_target:"))
async def cb_admin_newprod_target(call: CallbackQuery, state: FSMContext):
    if not await admin_only(call.from_user.id):
        return
    choice = call.data.split(":")[1]
    data = await state.get_data()
    if choice == "no":
        await db.create_product(data["cat_id"], data["title"], data["price"], data["description"])
        await state.clear()
        await call.message.edit_text(f"✅ محصول «{data['title']}» ساخته شد.")
        products = await db.list_products(data["cat_id"], only_active=False)
        await call.message.answer("📦 محصولات:", reply_markup=kb.admin_products_kb(products, data["cat_id"]))
    else:
        await state.set_state(AdminProduct.waiting_target_prompt)
        await call.message.edit_text(
            "متن سوالی که باید از کاربر پرسیده بشه رو بفرست.\n\n"
            "مثال: «یوزرنیم اکانت تلگرامی که می‌خوای پرمیومش کنیم رو بفرست (با @)»",
            reply_markup=kb.cancel_inline_kb("adm_cancel"),
        )
    await call.answer()


@router.message(AdminProduct.waiting_target_prompt)
async def admin_prod_target_prompt(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.create_product(
        data["cat_id"], data["title"], data["price"], data["description"],
        needs_target=True, target_prompt=message.text.strip(),
    )
    await state.clear()
    await message.answer(f"✅ محصول «{data['title']}» ساخته شد و سوال سفارشی تنظیم شد.")
    products = await db.list_products(data["cat_id"], only_active=False)
    await message.answer("📦 محصولات:", reply_markup=kb.admin_products_kb(products, data["cat_id"]))


async def render_product_detail(prod_id: int):
    prod = await db.get_product(prod_id)
    stock_count = await db.count_stock(prod_id)
    status = "🟢 فعال" if prod["is_active"] else "🔴 غیرفعال"
    target_info = f"📥 بله ({prod['target_prompt'] or 'بدون متن سفارشی'})" if prod["needs_target"] else "❌ خیر"
    text = (
        f"📌 <b>{prod['title']}</b>\n"
        f"قیمت: {fmt_money(prod['price'])}\n"
        f"توضیحات: {prod['description'] or '-'}\n"
        f"وضعیت: {status}\n"
        f"دریافت اطلاعات از کاربر: {target_info}\n"
        f"موجودی استوک: {stock_count} عدد"
    )
    return text, kb.admin_product_detail_kb(prod)


@router.callback_query(F.data.startswith("adm_prod:"))
async def cb_admin_prod_detail(call: CallbackQuery):
    if not await admin_only(call.from_user.id):
        return
    prod_id = int(call.data.split(":")[1])
    prod = await db.get_product(prod_id)
    if not prod:
        await call.answer("پیدا نشد.", show_alert=True)
        return
    text, markup = await render_product_detail(prod_id)
    await call.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("adm_prod_toggle:"))
async def cb_admin_prod_toggle(call: CallbackQuery):
    if not await admin_only(call.from_user.id):
        return
    prod_id = int(call.data.split(":")[1])
    await db.toggle_product(prod_id)
    await call.answer("وضعیت تغییر کرد ✅")
    text, markup = await render_product_detail(prod_id)
    await call.message.edit_text(text, reply_markup=markup, parse_mode="HTML")


@router.callback_query(F.data.startswith("adm_prod_toggle_target:"))
async def cb_admin_prod_toggle_target(call: CallbackQuery):
    if not await admin_only(call.from_user.id):
        return
    prod_id = int(call.data.split(":")[1])
    prod = await db.get_product(prod_id)
    await db.update_product(prod_id, needs_target=0 if prod["needs_target"] else 1)
    await call.answer("تغییر کرد ✅")
    text, markup = await render_product_detail(prod_id)
    await call.message.edit_text(text, reply_markup=markup, parse_mode="HTML")


@router.callback_query(F.data.startswith("adm_prod_edit_prompt:"))
async def cb_admin_prod_edit_prompt(call: CallbackQuery, state: FSMContext):
    if not await admin_only(call.from_user.id):
        return
    prod_id = int(call.data.split(":")[1])
    await state.update_data(prod_id=prod_id)
    await state.set_state(AdminProduct.edit_target_prompt)
    await call.message.answer("متن جدید سوال رو بفرست:", reply_markup=kb.cancel_inline_kb(f"adm_prod:{prod_id}"))
    await call.answer()


@router.message(AdminProduct.edit_target_prompt)
async def admin_prod_edit_prompt_recv(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.update_product(data["prod_id"], target_prompt=message.text.strip())
    await state.clear()
    await message.answer("✅ متن سوال بروزرسانی شد.")


@router.callback_query(F.data.startswith("adm_prod_edit_title:"))
async def cb_admin_prod_edit_title(call: CallbackQuery, state: FSMContext):
    if not await admin_only(call.from_user.id):
        return
    prod_id = int(call.data.split(":")[1])
    await state.update_data(prod_id=prod_id)
    await state.set_state(AdminProduct.edit_title)
    await call.message.answer("نام جدید محصول رو بفرست:", reply_markup=kb.cancel_inline_kb(f"adm_prod:{prod_id}"))
    await call.answer()


@router.message(AdminProduct.edit_title)
async def admin_prod_edit_title_recv(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.update_product(data["prod_id"], title=message.text.strip())
    await state.clear()
    await message.answer("✅ نام محصول بروزرسانی شد.")


@router.callback_query(F.data.startswith("adm_prod_edit_price:"))
async def cb_admin_prod_edit_price(call: CallbackQuery, state: FSMContext):
    if not await admin_only(call.from_user.id):
        return
    prod_id = int(call.data.split(":")[1])
    await state.update_data(prod_id=prod_id)
    await state.set_state(AdminProduct.edit_price)
    await call.message.answer("قیمت جدید رو به تومان بفرست (فقط عدد):", reply_markup=kb.cancel_inline_kb(f"adm_prod:{prod_id}"))
    await call.answer()


@router.message(AdminProduct.edit_price)
async def admin_prod_edit_price_recv(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("لطفاً فقط عدد بفرست.")
        return
    data = await state.get_data()
    await db.update_product(data["prod_id"], price=int(message.text))
    await state.clear()
    await message.answer("✅ قیمت محصول بروزرسانی شد.")


@router.callback_query(F.data.startswith("adm_prod_edit_desc:"))
async def cb_admin_prod_edit_desc(call: CallbackQuery, state: FSMContext):
    if not await admin_only(call.from_user.id):
        return
    prod_id = int(call.data.split(":")[1])
    await state.update_data(prod_id=prod_id)
    await state.set_state(AdminProduct.edit_description)
    await call.message.answer("توضیحات جدید رو بفرست:", reply_markup=kb.cancel_inline_kb(f"adm_prod:{prod_id}"))
    await call.answer()


@router.message(AdminProduct.edit_description)
async def admin_prod_edit_desc_recv(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.update_product(data["prod_id"], description=message.text.strip())
    await state.clear()
    await message.answer("✅ توضیحات محصول بروزرسانی شد.")


@router.callback_query(F.data.startswith("adm_prod_add_stock:"))
async def cb_admin_prod_add_stock(call: CallbackQuery, state: FSMContext):
    if not await admin_only(call.from_user.id):
        return
    prod_id = int(call.data.split(":")[1])
    await state.update_data(prod_id=prod_id)
    await state.set_state(AdminProduct.waiting_stock_bulk)
    await call.message.answer(
        "کدها/اکانت‌ها رو بفرست، هرکدوم در یک خط جدا (هرچقدر بخوای):\n\n"
        "مثال:\nkod1\nkod2\nkod3",
        reply_markup=kb.cancel_inline_kb(f"adm_prod:{prod_id}"),
    )
    await call.answer()


@router.message(AdminProduct.waiting_stock_bulk)
async def admin_prod_stock_bulk(message: Message, state: FSMContext):
    data = await state.get_data()
    lines = [l.strip() for l in message.text.split("\n") if l.strip()]
    await db.add_stock_bulk(data["prod_id"], lines)
    await state.clear()
    await message.answer(f"✅ {len(lines)} آیتم به استوک اضافه شد.")


@router.callback_query(F.data.startswith("adm_prod_delete_confirm:"))
async def cb_admin_prod_delete_confirm(call: CallbackQuery):
    if not await admin_only(call.from_user.id):
        return
    prod_id = int(call.data.split(":")[1])
    await call.message.edit_text(
        "⚠️ حذف دائمی این محصول و تمام سوابق استوکش قابل بازگشت نیست.\n"
        "اگه فقط می‌خوای موقتاً پنهون بشه، از «غیرفعال کردن» استفاده کن.\n\nمطمئنی؟",
        reply_markup=kb.confirm_delete_kb(f"adm_prod_delete:{prod_id}", f"adm_prod:{prod_id}"),
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_prod_delete:"))
async def cb_admin_prod_delete(call: CallbackQuery):
    if not await admin_only(call.from_user.id):
        return
    prod_id = int(call.data.split(":")[1])
    prod = await db.get_product(prod_id)
    cat_id = prod["category_id"]
    await db.delete_product_hard(prod_id)
    await call.answer("حذف شد.")
    products = await db.list_products(cat_id, only_active=False)
    await call.message.edit_text("📦 محصولات:", reply_markup=kb.admin_products_kb(products, cat_id))


# =============== مدیریت استوک (میانبر) ===============
@router.callback_query(F.data == "adm_stock_cats")
async def cb_admin_stock_cats(call: CallbackQuery):
    if not await admin_only(call.from_user.id):
        return
    cats = await db.list_categories(only_active=False)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    for c in cats:
        b.button(text=f"{c['emoji']} {c['title']}", callback_data=f"adm_prods:{c['id']}")
    b.button(text="⬅️ بازگشت", callback_data="adm_back")
    b.adjust(1)
    await call.message.edit_text(
        "📦 یه دسته انتخاب کن تا محصولات و موجودی استوکش رو ببینی و مدیریت کنی:",
        reply_markup=b.as_markup(),
    )
    await call.answer()


# =============== درخواست‌های شارژ کیف پول ===============
@router.callback_query(F.data == "adm_wallet_reqs")
async def cb_admin_wallet_reqs(call: CallbackQuery):
    if not await admin_only(call.from_user.id):
        return
    reqs = await db.list_pending_wallet_requests()
    if not reqs:
        await call.answer("درخواست در انتظاری وجود نداره.", show_alert=True)
        return
    await call.answer()
    for r in reqs:
        caption = (
            f"💳 درخواست شارژ #{r['id']}\n"
            f"کاربر: {r['user_id']}\n"
            f"مبلغ: {fmt_money(r['amount'])}\n"
            f"روش: {'کارت به کارت' if r['method']=='card' else 'کریپتو'}"
        )
        if r["receipt_file_id"]:
            await call.message.answer_photo(r["receipt_file_id"], caption=caption, reply_markup=kb.wallet_review_kb(r["id"]))
        else:
            await call.message.answer(caption, reply_markup=kb.wallet_review_kb(r["id"]))


# =============== مدیریت ادمین‌ها ===============
@router.callback_query(F.data == "adm_admins")
async def cb_admin_admins(call: CallbackQuery):
    if call.from_user.id != config.OWNER_ID:
        await call.answer("فقط مالک اصلی ربات می‌تونه ادمین مدیریت کنه.", show_alert=True)
        return
    admins = await db.list_admins()
    text = "👥 <b>لیست ادمین‌ها:</b>\n\n"
    text += f"👑 مالک اصلی: <code>{config.OWNER_ID}</code>\n"
    for a in admins:
        text += f"🔹 <code>{a['user_id']}</code>\n"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="➕ افزودن ادمین", callback_data="adm_admin_add")
    b.button(text="➖ حذف ادمین", callback_data="adm_admin_remove")
    b.button(text="⬅️ بازگشت", callback_data="adm_back")
    b.adjust(1)
    await call.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "adm_admin_add")
async def cb_admin_admin_add(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != config.OWNER_ID:
        return
    await state.update_data(action="add")
    await state.set_state(AdminManage.waiting_admin_id)
    await call.message.answer("آیدی عددی کاربر موردنظر برای افزودن به ادمین‌ها رو بفرست:", reply_markup=kb.cancel_inline_kb("adm_admins"))
    await call.answer()


@router.callback_query(F.data == "adm_admin_remove")
async def cb_admin_admin_remove(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != config.OWNER_ID:
        return
    await state.update_data(action="remove")
    await state.set_state(AdminManage.waiting_admin_id)
    await call.message.answer("آیدی عددی ادمینی که می‌خوای حذف کنی رو بفرست:", reply_markup=kb.cancel_inline_kb("adm_admins"))
    await call.answer()


@router.message(AdminManage.waiting_admin_id)
async def admin_manage_id_recv(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("لطفاً فقط آیدی عددی بفرست.")
        return
    data = await state.get_data()
    target_id = int(message.text)
    if data["action"] == "add":
        await db.add_admin(target_id, message.from_user.id)
        await message.answer(f"✅ کاربر {target_id} به لیست ادمین‌ها اضافه شد.")
    else:
        await db.remove_admin(target_id)
        await message.answer(f"✅ کاربر {target_id} از لیست ادمین‌ها حذف شد.")
    await state.clear()


# =============== مدیریت کاربران ===============
@router.callback_query(F.data == "adm_users")
async def cb_admin_users(call: CallbackQuery):
    if not await admin_only(call.from_user.id):
        return
    total = await db.count_users()
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="💰 تغییر موجودی کاربر", callback_data="adm_user_balance")
    b.button(text="⬅️ بازگشت", callback_data="adm_back")
    b.adjust(1)
    await call.message.edit_text(
        f"👤 <b>مدیریت کاربران</b>\nتعداد کل کاربران: {total}",
        reply_markup=b.as_markup(), parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "adm_user_balance")
async def cb_admin_user_balance(call: CallbackQuery, state: FSMContext):
    if not await admin_only(call.from_user.id):
        return
    await state.set_state(AdminManage.waiting_balance_user_id)
    await call.message.answer("آیدی عددی کاربر موردنظر رو بفرست:", reply_markup=kb.cancel_inline_kb("adm_users"))
    await call.answer()


@router.message(AdminManage.waiting_balance_user_id)
async def admin_balance_user_id_recv(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("لطفاً فقط آیدی عددی بفرست.")
        return
    user = await db.get_user(int(message.text))
    if not user:
        await message.answer("این کاربر تا حالا ربات رو استارت نکرده.")
        await state.clear()
        return
    await state.update_data(target_user_id=user["user_id"])
    await state.set_state(AdminManage.waiting_balance_amount)
    await message.answer(
        f"موجودی فعلی کاربر: {fmt_money(user['balance'])}\n"
        f"مبلغ موردنظر برای افزودن رو بفرست (برای کسر، عدد منفی بفرست، مثلاً -5000):",
        reply_markup=kb.cancel_inline_kb("adm_users"),
    )


@router.message(AdminManage.waiting_balance_amount)
async def admin_balance_amount_recv(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
    except ValueError:
        await message.answer("لطفاً فقط عدد بفرست.")
        return
    data = await state.get_data()
    await db.add_balance(data["target_user_id"], amount)
    await state.clear()
    await message.answer(f"✅ انجام شد. {fmt_money(amount)} به کیف پول کاربر {data['target_user_id']} اعمال شد.")
    try:
        await message.bot.send_message(
            data["target_user_id"], f"💰 موجودی کیف پولت توسط ادمین {fmt_money(amount)} تغییر کرد."
        )
    except Exception:
        pass


# =============== تنظیمات ===============
@router.callback_query(F.data == "adm_settings")
async def cb_admin_settings(call: CallbackQuery):
    if not await admin_only(call.from_user.id):
        return
    await call.message.edit_text("⚙️ <b>تنظیمات پرداخت و سیستم</b>", reply_markup=kb.admin_settings_kb(), parse_mode="HTML")
    await call.answer()


SETTING_STATE_MAP = {
    "card_number": AdminSettings.waiting_card_number,
    "card_holder": AdminSettings.waiting_card_holder,
    "crypto_address": AdminSettings.waiting_crypto_address,
    "crypto_network": AdminSettings.waiting_crypto_network,
    "referral_percent": AdminSettings.waiting_referral_percent,
    "min_topup": AdminSettings.waiting_min_topup,
    "force_join_channel": AdminSettings.waiting_force_channel,
    "shop_name": AdminSettings.waiting_shop_name,
    "welcome_message": AdminSettings.waiting_welcome_message,
    "support_contact": AdminSettings.waiting_support_contact,
}

SETTING_PROMPTS = {
    "card_number": "شماره کارت جدید رو بفرست:",
    "card_holder": "نام صاحب کارت رو بفرست:",
    "crypto_address": "آدرس کیف پول کریپتو رو بفرست:",
    "crypto_network": "نام شبکه رو بفرست (مثلاً TRC20):",
    "referral_percent": "درصد پورسانت رفرال رو بفرست (فقط عدد):",
    "min_topup": "حداقل مبلغ شارژ رو به تومان بفرست (فقط عدد):",
    "force_join_channel": "یوزرنیم کانال رو بدون @ بفرست (برای غیرفعال کردن، «-» بفرست):",
    "shop_name": "نام جدید فروشگاه (برند) رو بفرست:",
    "welcome_message": "متن خوش‌آمدگویی جدید رو بفرست:",
    "support_contact": "آیدی تلگرام پشتیبانی رو بفرست (مثلاً @support):",
}


@router.callback_query(F.data.startswith("adm_set:"))
async def cb_admin_set(call: CallbackQuery, state: FSMContext):
    if not await admin_only(call.from_user.id):
        return
    key = call.data.split(":")[1]
    await state.update_data(key=key)
    await state.set_state(SETTING_STATE_MAP[key])
    current = await db.get_setting(key)
    await call.message.answer(
        f"مقدار فعلی: <code>{current}</code>\n\n{SETTING_PROMPTS[key]}",
        parse_mode="HTML", reply_markup=kb.cancel_inline_kb("adm_settings"),
    )
    await call.answer()


@router.message(AdminSettings.waiting_card_number)
@router.message(AdminSettings.waiting_card_holder)
@router.message(AdminSettings.waiting_crypto_address)
@router.message(AdminSettings.waiting_crypto_network)
@router.message(AdminSettings.waiting_referral_percent)
@router.message(AdminSettings.waiting_min_topup)
@router.message(AdminSettings.waiting_force_channel)
@router.message(AdminSettings.waiting_shop_name)
@router.message(AdminSettings.waiting_welcome_message)
@router.message(AdminSettings.waiting_support_contact)
async def admin_setting_value_recv(message: Message, state: FSMContext):
    data = await state.get_data()
    key = data["key"]
    value = message.text.strip()
    if key == "force_join_channel" and value == "-":
        value = ""
    if key in ("referral_percent", "min_topup") and not value.isdigit():
        await message.answer("لطفاً فقط عدد بفرست.")
        return
    await db.set_setting(key, value)
    await state.clear()
    await message.answer("✅ تنظیمات ذخیره شد.")


# =============== آمار ===============
@router.callback_query(F.data == "adm_stats")
async def cb_admin_stats(call: CallbackQuery):
    if not await admin_only(call.from_user.id):
        return
    count, revenue = await db.sales_stats()
    total_users = await db.count_users()
    top = await db.top_products()
    text = (
        f"📊 <b>آمار فروش</b>\n\n"
        f"👥 تعداد کل کاربران: {total_users}\n"
        f"🧾 تعداد سفارشات تحویل‌شده: {count}\n"
        f"💰 مجموع درآمد: {fmt_money(revenue)}\n\n"
        f"🏆 <b>پرفروش‌ترین‌ها:</b>\n"
    )
    for t in top:
        text += f"• {t['title_snapshot']} — {t['cnt']} فروش — {fmt_money(t['revenue'])}\n"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ بازگشت", callback_data="adm_back")
    await call.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    await call.answer()


# =============== ارسال پیام همگانی ===============
@router.callback_query(F.data == "adm_broadcast")
async def cb_admin_broadcast(call: CallbackQuery, state: FSMContext):
    if not await admin_only(call.from_user.id):
        return
    await state.set_state(AdminBroadcast.waiting_message)
    await call.message.answer("پیامی که می‌خوای برای همه کاربران ارسال بشه رو بفرست:", reply_markup=kb.cancel_inline_kb("adm_back"))
    await call.answer()


@router.message(AdminBroadcast.waiting_message)
async def admin_broadcast_send(message: Message, state: FSMContext):
    await state.clear()
    db_conn = await db.get_db()
    cur = await db_conn.execute("SELECT user_id FROM users")
    rows = await cur.fetchall()
    sent, failed = 0, 0
    status_msg = await message.answer(f"در حال ارسال به {len(rows)} کاربر...")
    for row in rows:
        try:
            await message.bot.copy_message(row["user_id"], message.chat.id, message.message_id)
            sent += 1
        except Exception:
            failed += 1
    await status_msg.edit_text(f"✅ ارسال شد به {sent} نفر. ({failed} ناموفق)")
