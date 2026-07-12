from aiogram.fsm.state import State, StatesGroup


class BuyFlow(StatesGroup):
    waiting_target = State()          # آیدی/یوزرنیم مقصد برای محصولاتی که نیاز دارن
    waiting_currency_amount = State() # مقدار ارز درخواستی


class TopUp(StatesGroup):
    choosing_method = State()
    waiting_amount = State()
    waiting_receipt = State()


class AdminCategory(StatesGroup):
    waiting_title = State()
    waiting_emoji = State()
    edit_title = State()
    edit_emoji = State()


class AdminProduct(StatesGroup):
    waiting_title = State()
    waiting_price = State()
    waiting_description = State()
    waiting_target_prompt = State()
    edit_title = State()
    edit_price = State()
    edit_description = State()
    edit_target_prompt = State()
    waiting_stock_bulk = State()


class AdminSettings(StatesGroup):
    waiting_card_number = State()
    waiting_card_holder = State()
    waiting_crypto_address = State()
    waiting_crypto_network = State()
    waiting_referral_percent = State()
    waiting_min_topup = State()
    waiting_currency_rate = State()
    waiting_force_channel = State()


class AdminBroadcast(StatesGroup):
    waiting_message = State()


class AdminManage(StatesGroup):
    waiting_admin_id = State()
    waiting_reject_reason = State()
    waiting_balance_user_id = State()
    waiting_balance_amount = State()
