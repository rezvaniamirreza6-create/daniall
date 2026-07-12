from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
import config
from states import BuyFlow, TopUp
from utils import notify_admins, notify_admins_photo, fmt_money

router = Router()


# ---------------- /start ----------------
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    referrer_id = None
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_code = args[1][4:]
        ref_user = await db.get_user_by_ref_code(ref_code)
        if ref_user:
            referrer_id = ref_user["user_id"]

    user = await db.get_or_create_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name,
        referrer_id,
    )

    if user["is_banned"]:
        await message.answer("⛔️ شما توسط ادمین مسدود شده‌اید.")
        return

    if not await check_force_join(message.bot, message.from_user.id):
        return

    is_adm = await db.is_admin(message.from_user.id, config.OWNER_ID)
    await message.answer(
        f"🐉 <b>به Dragon Shop خوش اومدی!</b>\n\n"
        f"از منوی زیر می‌تونی محصولات رو مشاهده و خریداری کنی.\n"
        f"موجودی فعلی کیف پولت: <b>{fmt_money(user['balance'])}</b>",
        reply_markup=kb.main_menu_kb(is_adm),
        parse_mode="HTML",
    )


async def check_force_join(bot: Bot, user_id: int) -> bool:
    channel = await db.get_setting("force_join_channel")
    if not channel:
        return True
    try:
        member = await bot.get_chat_member(f"@{channel}", user_id)
        if member.status in ("left", "kicked"):
            raise Exception("not joined")
        return True
    except Exception:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        b = InlineKeyboardBuilder()
        b.button(text="📢 عضویت در کانال", url=f"https://t.me/{channel}")
        b.button(text="✅ عضو شدم", callback_data="check_join")
        b.adjust(1)
        await bot.send_message(
            user_id,
            "برای استفاده از ربات ابتدا باید عضو کانال ما بشید 👇",
            reply_markup=b.as_markup(),
        )
        return False


@router.callback_query(F.data == "check_join")
async def cb_check_join(call: CallbackQuery, state: FSMContext):
    if await check_force_join(call.bot, call.from_user.id):
        await call.message.delete()
        await cmd_start(call.message, state)
    else:
        await call.answer("هنوز عضو نشدی!", show_alert=True)


# ---------------- منوی محصولات ----------------
@router.message(F.text == "🛍 منوی محصولات")
async def show_products_menu(message: Message):
    cats = await db.list_categories(only_active=True)
    if not cats:
        await message.answer("در حال حاضر محصولی برای فروش موجود نیست.")
        return
    await message.answer("🛍 یکی از دسته‌های زیر رو انتخاب کن:", reply_markup=kb.categories_kb(cats))


@router.callback_query(F.data.startswith("cat:"))
async def cb_open_category(call: CallbackQuery):
    cat_id = int(call.data.split(":")[1])
    cat = await db.get_category(cat_id)
    if not cat or not cat["is_active"]:
        await call.answer("این دسته دیگر موجود نیست.", show_alert=True)
        return

    if cat["kind"] == "currency":
        products = await db.list_products(cat_id, only_active=True)
        if not products:
            await call.answer("محصولی موجود نیست.", show_alert=True)
            return
        # دسته‌ی ارز: فقط یک نرخ داره، مستقیم مقدار رو می‌پرسیم
        p = products[0]
        await call.message.answer(
            f"💱 <b>{cat['title']}</b>\n"
            f"نرخ هر واحد: {fmt_money(p['price'])}\n\n"
            f"مقدار ارز موردنظرت رو به عدد بفرست (مثلاً 10):",
            parse_mode="HTML",
        )
        await call.answer()
        return

    products = await db.list_products(cat_id, only_active=True)
    if not products:
        await call.answer("محصولی در این دسته موجود نیست.", show_alert=True)
        return
    await call.message.edit_text(
        f"{cat['emoji']} <b>{cat['title']}</b>\nیکی از گزینه‌های زیر رو انتخاب کن:",
        reply_markup=kb.products_kb(products, cat_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "back_categories")
async def cb_back_categories(call: CallbackQuery):
    cats = await db.list_categories(only_active=True)
    await call.message.edit_text("🛍 یکی از دسته‌های زیر رو انتخاب کن:", reply_markup=kb.categories_kb(cats))


@router.callback_query(F.data.startswith("prod:"))
async def cb_open_product(call: CallbackQuery, state: FSMContext):
    prod_id = int(call.data.split(":")[1])
    prod = await db.get_product(prod_id)
    if not prod or not prod["is_active"]:
        await call.answer("این محصول دیگر موجود نیست.", show_alert=True)
        return

    if prod["needs_target"]:
        await state.update_data(product_id=prod_id)
        await state.set_state(BuyFlow.waiting_target)
        prompt = prod["target_prompt"] or "آیدی عددی یا یوزرنیم تلگرام مقصد رو ارسال کن (مثال: @username):"
        await call.message.answer(
            f"📌 <b>{prod['title']}</b>\nقیمت: {fmt_money(prod['price'])}\n\n{prompt}",
            parse_mode="HTML",
        )
        await call.answer()
        return

    text = (
        f"📌 <b>{prod['title']}</b>\n"
        f"{prod['description']}\n\n"
        f"قیمت: <b>{fmt_money(prod['price'])}</b>\n\n"
        f"آیا تایید می‌کنی این مبلغ از کیف پولت کسر و خرید انجام بشه؟"
    )
    await call.message.answer(text, reply_markup=kb.confirm_buy_kb(prod_id), parse_mode="HTML")
    await call.answer()


@router.message(BuyFlow.waiting_target)
async def receive_target(message: Message, state: FSMContext):
    data = await state.get_data()
    prod = await db.get_product(data["product_id"])
    if not prod or not prod["is_active"]:
        await state.clear()
        await message.answer("این محصول دیگر موجود نیست.")
        return
    await state.update_data(target_info=message.text.strip())
    text = (
        f"📌 <b>{prod['title']}</b>\n"
        f"مقصد: <code>{message.text.strip()}</code>\n"
        f"قیمت: <b>{fmt_money(prod['price'])}</b>\n\n"
        f"آیا تایید می‌کنی؟"
    )
    await message.answer(text, reply_markup=kb.confirm_buy_kb(prod["id"]), parse_mode="HTML")


@router.message(BuyFlow.waiting_currency_amount)
async def receive_currency_amount(message: Message, state: FSMContext):
    pass  # این مسیر توسط هندلر پایین (متن آزاد در منوی ارز) پوشش داده می‌شه


# مقدار ارز: چون از callback مستقیم پرسیده شد (بدون FSM رسمی)، این هندلر متن ساده برای دسته ارز رو می‌گیریم
@router.message(F.text.regexp(r"^\d+(\.\d+)?$"))
async def maybe_currency_amount(message: Message):
    cats = await db.list_categories(only_active=True)
    currency_cats = [c for c in cats if c["kind"] == "currency"]
    if not currency_cats:
        return
    cat = currency_cats[0]
    products = await db.list_products(cat["id"], only_active=True)
    if not products:
        return
    p = products[0]
    amount = float(message.text)
    total = int(amount * p["price"])
    text = (
        f"💱 <b>{cat['title']}</b>\n"
        f"مقدار: {amount}\n"
        f"نرخ واحد: {fmt_money(p['price'])}\n"
        f"مبلغ کل: <b>{fmt_money(total)}</b>\n\n"
        f"تایید می‌کنی؟"
    )
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="✅ تایید و پرداخت از کیف پول", callback_data=f"confirm_currency:{p['id']}:{amount}")
    b.button(text="❌ انصراف", callback_data="cancel_buy")
    b.adjust(1)
    await message.answer(text, reply_markup=b.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("confirm_currency:"))
async def cb_confirm_currency(call: CallbackQuery):
    _, prod_id, amount = call.data.split(":")
    prod_id = int(prod_id)
    amount = float(amount)
    prod = await db.get_product(prod_id)
    user = await db.get_user(call.from_user.id)
    if not prod or not prod["is_active"]:
        await call.answer("این محصول دیگر موجود نیست.", show_alert=True)
        return
    total = int(amount * prod["price"])
    if user["balance"] < total:
        await call.answer("موجودی کیف پول کافی نیست. لطفاً ابتدا شارژ کن.", show_alert=True)
        return

    await db.add_balance(user["user_id"], -total)
    order_id = await db.create_order(
        user["user_id"], prod_id, f"{prod['title']} x{amount}", total, qty=1, status="pending"
    )
    await handle_referral_commission(call.bot, user, total, order_id)

    await call.message.edit_text(
        f"✅ سفارش شما ثبت شد (کد سفارش #{order_id}).\n"
        f"مبلغ {fmt_money(total)} از کیف پولت کسر شد.\n"
        f"مدیر به‌زودی ارز رو براتون واریز می‌کنه و اطلاع می‌ده."
    )
    await notify_admins(
        call.bot,
        f"💱 سفارش ارز جدید #{order_id}\n"
        f"کاربر: {user['user_id']} (@{call.from_user.username or '-'})\n"
        f"مقدار: {amount}\n"
        f"مبلغ: {fmt_money(total)}\n\n"
        f"برای تحویل به کاربر پیام بدید و بعد وضعیت سفارش رو در دیتابیس تکمیل کنید.",
    )
    await call.answer()


@router.callback_query(F.data == "cancel_buy")
async def cb_cancel_buy(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ خرید لغو شد.")
    await call.answer()


@router.callback_query(F.data.startswith("confirm_buy:"))
async def cb_confirm_buy(call: CallbackQuery, state: FSMContext):
    prod_id = int(call.data.split(":")[1])
    prod = await db.get_product(prod_id)
    user = await db.get_user(call.from_user.id)
    data = await state.get_data()
    target_info = data.get("target_info")
    await state.clear()

    if not prod or not prod["is_active"]:
        await call.answer("این محصول دیگر موجود نیست.", show_alert=True)
        return
    if user["balance"] < prod["price"]:
        await call.answer("موجودی کیف پول کافی نیست. لطفاً ابتدا شارژ کن.", show_alert=True)
        return

    stock_content = await db.pop_stock_item(prod_id, user["user_id"])
    await db.add_balance(user["user_id"], -prod["price"])

    status = "delivered" if stock_content else "pending"
    order_id = await db.create_order(
        user["user_id"], prod_id, prod["title"], prod["price"],
        target_info=target_info, status=status, delivered_content=stock_content,
    )
    await handle_referral_commission(call.bot, user, prod["price"], order_id)

    if stock_content:
        await call.message.edit_text(
            f"✅ خرید موفق! (سفارش #{order_id})\n\n"
            f"📦 محصول شما:\n<code>{stock_content}</code>",
            parse_mode="HTML",
        )
    else:
        await call.message.edit_text(
            f"✅ سفارش شما ثبت شد (کد سفارش #{order_id}).\n"
            f"مبلغ {fmt_money(prod['price'])} از کیف پولت کسر شد.\n"
            f"⏳ موجودی این محصول فعلاً تموم شده، ادمین به‌زودی به‌صورت دستی براتون تامین و ارسال می‌کنه."
        )
        await notify_admins(
            call.bot,
            f"🆕 سفارش نیازمند تامین دستی #{order_id}\n"
            f"محصول: {prod['title']}\n"
            f"کاربر: {user['user_id']} (@{call.from_user.username or '-'})\n"
            + (f"مقصد: {target_info}\n" if target_info else "")
            + f"مبلغ: {fmt_money(prod['price'])}\n"
            f"موجودی استوک این محصول تموم شده، لطفاً استوک اضافه یا دستی تحویل بدید.",
        )
    await call.answer()


async def handle_referral_commission(bot: Bot, buyer, amount: int, order_id: int):
    if not buyer["referrer_id"]:
        return
    percent = int(await db.get_setting("referral_percent") or 0)
    if percent <= 0:
        return
    commission = amount * percent // 100
    if commission <= 0:
        return
    await db.add_referral_earning(buyer["referrer_id"], buyer["user_id"], order_id, commission)
    try:
        await bot.send_message(
            buyer["referrer_id"],
            f"🤝 پورسانت رفرال: {fmt_money(commission)} از خرید یکی از زیرمجموعه‌هات به کیف پولت اضافه شد!",
        )
    except Exception:
        pass


# ---------------- افزایش موجودی ----------------
@router.message(F.text == "💰 افزایش موجودی")
async def topup_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("روش شارژ کیف پول رو انتخاب کن:", reply_markup=kb.topup_method_kb())


@router.callback_query(F.data.startswith("topup_method:"))
async def cb_topup_method(call: CallbackQuery, state: FSMContext):
    method = call.data.split(":")[1]
    await state.update_data(method=method)
    await state.set_state(TopUp.waiting_amount)
    min_amt = await db.get_setting("min_topup")
    await call.message.answer(f"مبلغ موردنظر برای شارژ رو به تومان وارد کن (حداقل {int(min_amt):,} تومان):")
    await call.answer()


@router.message(TopUp.waiting_amount)
async def topup_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("لطفاً فقط عدد وارد کن.")
        return
    amount = int(message.text)
    min_amt = int(await db.get_setting("min_topup") or 0)
    if amount < min_amt:
        await message.answer(f"حداقل مبلغ شارژ {min_amt:,} تومان است.")
        return
    await state.update_data(amount=amount)
    data = await state.get_data()

    if data["method"] == "card":
        card_number = await db.get_setting("card_number")
        card_holder = await db.get_setting("card_holder")
        text = (
            f"💳 مبلغ <b>{fmt_money(amount)}</b> رو به کارت زیر واریز کن:\n\n"
            f"شماره کارت: <code>{card_number}</code>\n"
            f"به نام: {card_holder}\n\n"
            f"بعد از واریز، عکس رسید رو همینجا ارسال کن."
        )
    else:
        crypto_address = await db.get_setting("crypto_address")
        crypto_network = await db.get_setting("crypto_network")
        text = (
            f"🪙 معادل مبلغ <b>{fmt_money(amount)}</b> رو به آدرس زیر واریز کن:\n\n"
            f"شبکه: {crypto_network}\n"
            f"آدرس: <code>{crypto_address}</code>\n\n"
            f"بعد از واریز، عکس رسید تراکنش رو همینجا ارسال کن."
        )
    await state.set_state(TopUp.waiting_receipt)
    await message.answer(text, parse_mode="HTML")


@router.message(TopUp.waiting_receipt, F.photo)
async def topup_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    req_id = await db.create_wallet_request(
        message.from_user.id, data["amount"], data["method"], message.photo[-1].file_id
    )
    await state.clear()
    await message.answer(
        f"✅ رسید شما ثبت شد (کد #{req_id}). پس از تایید ادمین، کیف پولت شارژ می‌شه."
    )
    await notify_admins_photo(
        message.bot,
        message.photo[-1].file_id,
        f"💳 درخواست شارژ کیف پول #{req_id}\n"
        f"کاربر: {message.from_user.id} (@{message.from_user.username or '-'})\n"
        f"مبلغ: {fmt_money(data['amount'])}\n"
        f"روش: {'کارت به کارت' if data['method']=='card' else 'کریپتو'}",
        reply_markup=kb.wallet_review_kb(req_id),
    )


@router.message(TopUp.waiting_receipt)
async def topup_receipt_invalid(message: Message):
    await message.answer("لطفاً عکس رسید پرداخت رو ارسال کن.")


@router.callback_query(F.data.startswith("wallet_approve:"))
async def cb_wallet_approve(call: CallbackQuery):
    req_id = int(call.data.split(":")[1])
    req = await db.get_wallet_request(req_id)
    if not req or req["status"] != "pending":
        await call.answer("این درخواست قبلاً بررسی شده.", show_alert=True)
        return
    await db.add_balance(req["user_id"], req["amount"])
    await db.update_wallet_request(req_id, status="approved", reviewed_by=call.from_user.id, reviewed_at=0)
    extra = "\n\n✅ تایید شد و کیف پول شارژ شد."
    try:
        if call.message.photo:
            await call.message.edit_caption(caption=(call.message.caption or "") + extra)
        else:
            await call.message.edit_text((call.message.text or "") + extra)
    except Exception:
        await call.message.answer("✅ تایید شد و کیف پول شارژ شد.")
    try:
        await call.bot.send_message(
            req["user_id"], f"✅ کیف پولت به مبلغ {fmt_money(req['amount'])} شارژ شد!"
        )
    except Exception:
        pass
    await call.answer("تایید شد.")


@router.callback_query(F.data.startswith("wallet_reject:"))
async def cb_wallet_reject(call: CallbackQuery):
    req_id = int(call.data.split(":")[1])
    req = await db.get_wallet_request(req_id)
    if not req or req["status"] != "pending":
        await call.answer("این درخواست قبلاً بررسی شده.", show_alert=True)
        return
    await db.update_wallet_request(req_id, status="rejected", reviewed_by=call.from_user.id, reviewed_at=0)
    extra = "\n\n❌ رد شد."
    try:
        if call.message.photo:
            await call.message.edit_caption(caption=(call.message.caption or "") + extra)
        else:
            await call.message.edit_text((call.message.text or "") + extra)
    except Exception:
        await call.message.answer("❌ رد شد.")
    try:
        await call.bot.send_message(req["user_id"], "❌ درخواست شارژ کیف پولت رد شد. با پشتیبانی تماس بگیر.")
    except Exception:
        pass
    await call.answer("رد شد.")


# ---------------- حساب کاربری ----------------
@router.message(F.text == "👤 حساب کاربری")
async def account_info(message: Message):
    user = await db.get_user(message.from_user.id)
    await message.answer(
        f"👤 <b>حساب کاربری</b>\n\n"
        f"آیدی عددی: <code>{user['user_id']}</code>\n"
        f"موجودی کیف پول: <b>{fmt_money(user['balance'])}</b>\n"
        f"تاریخ عضویت: <code>{user['joined_at']}</code>",
        parse_mode="HTML",
    )


# ---------------- زیرمجموعه‌گیری ----------------
@router.message(F.text == "🤝 زیرمجموعه‌گیری")
async def referral_info(message: Message):
    user = await db.get_user(message.from_user.id)
    bot_info = await message.bot.get_me()
    count = await db.get_referrals_count(user["user_id"])
    earnings = await db.get_referral_total_earnings(user["user_id"])
    percent = await db.get_setting("referral_percent")
    link = f"https://t.me/{bot_info.username}?start=ref_{user['ref_code']}"
    await message.answer(
        f"🤝 <b>سیستم زیرمجموعه‌گیری</b>\n\n"
        f"با دعوت دوستانت، از هر خریدشون {percent}٪ پورسانت به کیف پولت اضافه می‌شه!\n\n"
        f"🔗 لینک اختصاصی تو:\n<code>{link}</code>\n\n"
        f"👥 تعداد زیرمجموعه: {count}\n"
        f"💰 مجموع پورسانت دریافتی: {fmt_money(earnings)}",
        parse_mode="HTML",
    )


# ---------------- تاریخچه سفارشات ----------------
@router.message(F.text == "🧾 تاریخچه سفارشات")
async def order_history(message: Message):
    orders = await db.list_user_orders(message.from_user.id)
    if not orders:
        await message.answer("هنوز هیچ سفارشی ثبت نکردی.")
        return
    status_map = {"pending": "⏳ در انتظار", "delivered": "✅ تحویل شد", "rejected": "❌ رد شد"}
    lines = ["🧾 <b>آخرین سفارشات تو:</b>\n"]
    for o in orders:
        lines.append(
            f"#{o['id']} | {o['title_snapshot']} | {fmt_money(o['price_snapshot'])} | {status_map.get(o['status'], o['status'])}"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


# ---------------- پشتیبانی ----------------
@router.message(F.text == "🆘 پشتیبانی")
async def support_info(message: Message):
    await message.answer(
        "🆘 برای ارتباط با پشتیبانی، پیامتو همینجا بنویس تا به ادمین ارسال بشه.\n"
        "(یا مستقیماً با ادمین از طریق آیدی که در بیو ربات هست تماس بگیر.)"
    )
