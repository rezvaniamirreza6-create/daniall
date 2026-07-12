import aiosqlite
import time
import secrets
from config import DB_PATH

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA foreign_keys = ON")
    return _db


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    phone TEXT,
    is_verified INTEGER NOT NULL DEFAULT 0,
    balance INTEGER NOT NULL DEFAULT 0,
    referrer_id INTEGER,
    ref_code TEXT UNIQUE,
    is_banned INTEGER NOT NULL DEFAULT 0,
    joined_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY,
    added_by INTEGER,
    added_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    emoji TEXT NOT NULL DEFAULT '📦',
    kind TEXT NOT NULL DEFAULT 'normal',   -- normal | currency
    is_active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price INTEGER NOT NULL DEFAULT 0,       -- برای دسته currency: قیمت هر واحد
    needs_target INTEGER NOT NULL DEFAULT 0, -- آیا نیاز به آیدی/یوزرنیم اکانت مقصد داره
    target_prompt TEXT NOT NULL DEFAULT '',  -- متن سوالی که از کاربر پرسیده می‌شه
    is_active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS stock_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    content TEXT NOT NULL,
    is_used INTEGER NOT NULL DEFAULT 0,
    used_by INTEGER,
    used_at INTEGER
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER,
    title_snapshot TEXT NOT NULL,
    price_snapshot INTEGER NOT NULL,
    qty INTEGER NOT NULL DEFAULT 1,
    target_info TEXT,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | delivered | rejected
    delivered_content TEXT,
    admin_note TEXT,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS wallet_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    method TEXT NOT NULL DEFAULT 'card',
    receipt_file_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected
    created_at INTEGER NOT NULL,
    reviewed_by INTEGER,
    reviewed_at INTEGER
);

CREATE TABLE IF NOT EXISTS referral_earnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL,
    from_user_id INTEGER NOT NULL,
    order_id INTEGER,
    amount INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

DEFAULT_SETTINGS = {
    "card_number": "0000-0000-0000-0000",
    "card_holder": "نام صاحب کارت",
    "crypto_address": "",
    "crypto_network": "TRC20 (USDT)",
    "referral_percent": "5",
    "min_topup": "10000",
    "force_join_channel": "",  # یوزرنیم کانال بدون @ ، خالی = غیرفعال
    "shop_name": "Dragon Shop",
    "welcome_message": "به فروشگاه ما خوش اومدی! از منوی زیر می‌تونی محصولات رو مشاهده و خریداری کنی.",
    "support_contact": "@support",
}

DEFAULT_CATEGORIES = [
    # title, emoji, kind
    ("تلگرام پرمیوم", "⭐️", "normal"),
    ("استارز تلگرام", "✨", "normal"),
    ("گیفت استارز", "🎁", "normal"),
    ("گیفت NFT", "💎", "normal"),
    ("وی‌پی‌ان (VPN)", "🛡", "normal"),
    ("ساندکلود پرمیوم", "🎧", "normal"),
    ("اسپاتیفای پرمیوم", "🟢", "normal"),
    ("خرید ارز / کریپتو", "💱", "currency"),
    ("شماره مجازی", "📱", "normal"),
]


async def init_db():
    db = await get_db()
    await db.executescript(SCHEMA)
    await db.commit()

    for k, v in DEFAULT_SETTINGS.items():
        await db.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
        )

    cur = await db.execute("SELECT COUNT(*) c FROM categories")
    row = await cur.fetchone()
    if row["c"] == 0:
        for i, (title, emoji, kind) in enumerate(DEFAULT_CATEGORIES):
            is_active = 0 if title == "شماره مجازی" else 1  # طبق درخواست: فعلاً غیرفعال
            await db.execute(
                "INSERT INTO categories (title, emoji, kind, is_active, sort_order) VALUES (?,?,?,?,?)",
                (title, emoji, kind, is_active, i),
            )
    await db.commit()


# ---------- Settings ----------
async def get_setting(key: str) -> str:
    db = await get_db()
    cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = await cur.fetchone()
    return row["value"] if row else ""


async def set_setting(key: str, value: str):
    db = await get_db()
    await db.execute(
        "INSERT INTO settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    await db.commit()


# ---------- Users ----------
async def get_or_create_user(user_id: int, username: str, full_name: str, referrer_id: int | None = None):
    db = await get_db()
    cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = await cur.fetchone()
    if row:
        await db.execute(
            "UPDATE users SET username=?, full_name=? WHERE user_id=?",
            (username, full_name, user_id),
        )
        await db.commit()
        return row
    ref_code = secrets.token_hex(4)
    if referrer_id == user_id:
        referrer_id = None
    await db.execute(
        "INSERT INTO users (user_id, username, full_name, balance, referrer_id, ref_code, joined_at) VALUES (?,?,?,0,?,?,?)",
        (user_id, username, full_name, referrer_id, ref_code, int(time.time())),
    )
    await db.commit()
    cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return await cur.fetchone()


async def get_user(user_id: int):
    db = await get_db()
    cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return await cur.fetchone()


async def get_user_by_ref_code(ref_code: str):
    db = await get_db()
    cur = await db.execute("SELECT * FROM users WHERE ref_code=?", (ref_code,))
    return await cur.fetchone()


async def add_balance(user_id: int, amount: int):
    db = await get_db()
    await db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    await db.commit()


async def set_ban(user_id: int, banned: bool):
    db = await get_db()
    await db.execute("UPDATE users SET is_banned=? WHERE user_id=?", (1 if banned else 0, user_id))
    await db.commit()


async def verify_user_phone(user_id: int, phone: str):
    db = await get_db()
    await db.execute("UPDATE users SET phone=?, is_verified=1 WHERE user_id=?", (phone, user_id))
    await db.commit()


async def count_users() -> int:
    db = await get_db()
    cur = await db.execute("SELECT COUNT(*) c FROM users")
    return (await cur.fetchone())["c"]


async def get_referrals_count(user_id: int) -> int:
    db = await get_db()
    cur = await db.execute("SELECT COUNT(*) c FROM users WHERE referrer_id=?", (user_id,))
    return (await cur.fetchone())["c"]


async def get_referral_total_earnings(user_id: int) -> int:
    db = await get_db()
    cur = await db.execute(
        "SELECT COALESCE(SUM(amount),0) s FROM referral_earnings WHERE referrer_id=?", (user_id,)
    )
    return (await cur.fetchone())["s"]


# ---------- Admins ----------
async def is_admin(user_id: int, owner_id: int) -> bool:
    if user_id == owner_id:
        return True
    db = await get_db()
    cur = await db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,))
    return (await cur.fetchone()) is not None


async def add_admin(user_id: int, added_by: int):
    db = await get_db()
    await db.execute(
        "INSERT OR IGNORE INTO admins (user_id, added_by, added_at) VALUES (?,?,?)",
        (user_id, added_by, int(time.time())),
    )
    await db.commit()


async def remove_admin(user_id: int):
    db = await get_db()
    await db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
    await db.commit()


async def list_admins():
    db = await get_db()
    cur = await db.execute("SELECT * FROM admins ORDER BY added_at")
    return await cur.fetchall()


# ---------- Categories ----------
async def list_categories(only_active=True):
    db = await get_db()
    q = "SELECT * FROM categories"
    if only_active:
        q += " WHERE is_active=1"
    q += " ORDER BY sort_order, id"
    cur = await db.execute(q)
    return await cur.fetchall()


async def get_category(cat_id: int):
    db = await get_db()
    cur = await db.execute("SELECT * FROM categories WHERE id=?", (cat_id,))
    return await cur.fetchone()


async def create_category(title: str, emoji: str, kind: str = "normal"):
    db = await get_db()
    cur = await db.execute("SELECT COALESCE(MAX(sort_order),0)+1 s FROM categories")
    sort_order = (await cur.fetchone())["s"]
    cur = await db.execute(
        "INSERT INTO categories (title, emoji, kind, sort_order) VALUES (?,?,?,?)",
        (title, emoji, kind, sort_order),
    )
    await db.commit()
    return cur.lastrowid


async def update_category(cat_id: int, **fields):
    if not fields:
        return
    db = await get_db()
    sets = ", ".join(f"{k}=?" for k in fields)
    await db.execute(f"UPDATE categories SET {sets} WHERE id=?", (*fields.values(), cat_id))
    await db.commit()


async def toggle_category(cat_id: int):
    db = await get_db()
    await db.execute("UPDATE categories SET is_active = 1 - is_active WHERE id=?", (cat_id,))
    await db.commit()


async def delete_category_hard(cat_id: int):
    db = await get_db()
    await db.execute("DELETE FROM categories WHERE id=?", (cat_id,))
    await db.commit()


# ---------- Products ----------
async def list_products(category_id: int, only_active=True):
    db = await get_db()
    q = "SELECT * FROM products WHERE category_id=?"
    if only_active:
        q += " AND is_active=1"
    q += " ORDER BY sort_order, id"
    cur = await db.execute(q, (category_id,))
    return await cur.fetchall()


async def get_product(product_id: int):
    db = await get_db()
    cur = await db.execute("SELECT * FROM products WHERE id=?", (product_id,))
    return await cur.fetchone()


async def create_product(category_id: int, title: str, price: int, description: str = "", needs_target: bool = False, target_prompt: str = ""):
    db = await get_db()
    cur = await db.execute("SELECT COALESCE(MAX(sort_order),0)+1 s FROM products WHERE category_id=?", (category_id,))
    sort_order = (await cur.fetchone())["s"]
    cur = await db.execute(
        "INSERT INTO products (category_id, title, description, price, needs_target, target_prompt, sort_order) VALUES (?,?,?,?,?,?,?)",
        (category_id, title, description, price, 1 if needs_target else 0, target_prompt, sort_order),
    )
    await db.commit()
    return cur.lastrowid


async def update_product(product_id: int, **fields):
    if not fields:
        return
    db = await get_db()
    sets = ", ".join(f"{k}=?" for k in fields)
    await db.execute(f"UPDATE products SET {sets} WHERE id=?", (*fields.values(), product_id))
    await db.commit()


async def toggle_product(product_id: int):
    db = await get_db()
    await db.execute("UPDATE products SET is_active = 1 - is_active WHERE id=?", (product_id,))
    await db.commit()


async def delete_product_hard(product_id: int):
    db = await get_db()
    await db.execute("DELETE FROM products WHERE id=?", (product_id,))
    await db.commit()


# ---------- Stock ----------
async def add_stock_bulk(product_id: int, lines: list[str]):
    db = await get_db()
    await db.executemany(
        "INSERT INTO stock_items (product_id, content) VALUES (?,?)",
        [(product_id, line) for line in lines],
    )
    await db.commit()


async def count_stock(product_id: int) -> int:
    db = await get_db()
    cur = await db.execute(
        "SELECT COUNT(*) c FROM stock_items WHERE product_id=? AND is_used=0", (product_id,)
    )
    return (await cur.fetchone())["c"]


async def pop_stock_item(product_id: int, user_id: int):
    db = await get_db()
    cur = await db.execute(
        "SELECT id, content FROM stock_items WHERE product_id=? AND is_used=0 ORDER BY id LIMIT 1",
        (product_id,),
    )
    row = await cur.fetchone()
    if not row:
        return None
    await db.execute(
        "UPDATE stock_items SET is_used=1, used_by=?, used_at=? WHERE id=?",
        (user_id, int(time.time()), row["id"]),
    )
    await db.commit()
    return row["content"]


# ---------- Orders ----------
async def create_order(user_id, product_id, title_snapshot, price_snapshot, qty=1, target_info=None, status="pending", delivered_content=None):
    db = await get_db()
    cur = await db.execute(
        """INSERT INTO orders (user_id, product_id, title_snapshot, price_snapshot, qty, target_info, status, delivered_content, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (user_id, product_id, title_snapshot, price_snapshot, qty, target_info, status, delivered_content, int(time.time())),
    )
    await db.commit()
    return cur.lastrowid


async def get_order(order_id: int):
    db = await get_db()
    cur = await db.execute("SELECT * FROM orders WHERE id=?", (order_id,))
    return await cur.fetchone()


async def update_order(order_id: int, **fields):
    db = await get_db()
    sets = ", ".join(f"{k}=?" for k in fields)
    await db.execute(f"UPDATE orders SET {sets} WHERE id=?", (*fields.values(), order_id))
    await db.commit()


async def list_user_orders(user_id: int, limit=20):
    db = await get_db()
    cur = await db.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)
    )
    return await cur.fetchall()


async def sales_stats():
    db = await get_db()
    cur = await db.execute(
        "SELECT COUNT(*) c, COALESCE(SUM(price_snapshot*qty),0) s FROM orders WHERE status='delivered'"
    )
    row = await cur.fetchone()
    return row["c"], row["s"]


async def top_products(limit=5):
    db = await get_db()
    cur = await db.execute(
        """SELECT title_snapshot, COUNT(*) cnt, SUM(price_snapshot*qty) revenue
           FROM orders WHERE status='delivered'
           GROUP BY title_snapshot ORDER BY cnt DESC LIMIT ?""",
        (limit,),
    )
    return await cur.fetchall()


# ---------- Wallet requests ----------
async def create_wallet_request(user_id: int, amount: int, method: str, receipt_file_id: str | None):
    db = await get_db()
    cur = await db.execute(
        "INSERT INTO wallet_requests (user_id, amount, method, receipt_file_id, created_at) VALUES (?,?,?,?,?)",
        (user_id, amount, method, receipt_file_id, int(time.time())),
    )
    await db.commit()
    return cur.lastrowid


async def get_wallet_request(req_id: int):
    db = await get_db()
    cur = await db.execute("SELECT * FROM wallet_requests WHERE id=?", (req_id,))
    return await cur.fetchone()


async def update_wallet_request(req_id: int, **fields):
    db = await get_db()
    sets = ", ".join(f"{k}=?" for k in fields)
    await db.execute(f"UPDATE wallet_requests SET {sets} WHERE id=?", (*fields.values(), req_id))
    await db.commit()


async def list_pending_wallet_requests(limit=20):
    db = await get_db()
    cur = await db.execute(
        "SELECT * FROM wallet_requests WHERE status='pending' ORDER BY id LIMIT ?", (limit,)
    )
    return await cur.fetchall()


# ---------- Referral ----------
async def add_referral_earning(referrer_id: int, from_user_id: int, order_id: int, amount: int):
    db = await get_db()
    await db.execute(
        "INSERT INTO referral_earnings (referrer_id, from_user_id, order_id, amount, created_at) VALUES (?,?,?,?,?)",
        (referrer_id, from_user_id, order_id, amount, int(time.time())),
    )
    await db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, referrer_id))
    await db.commit()
