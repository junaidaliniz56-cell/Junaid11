import telebot
from telebot import types
import sqlite3

# ========= CONFIG =========
TOKEN = "8380662421:AAEP9BOevEPJ5CDDwYesgbkNns4bi4bwrH0"
ADMINS = [7011937754]

METHOD_COST = 7
INVITE_REWARD = 1

# BOT MUST BE ADMIN IN THESE 2 CHANNELS
STRICT_CHANNELS = [
    "@jndtech1",
    "@jndtech1"
]

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ========= DATABASE =========
db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS methods (name TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS channels (username TEXT)")
db.commit()

# ========= HELPERS =========
def is_admin(uid):
    return uid in ADMINS

def add_user(uid):
    cur.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (uid,))
    db.commit()

def get_points(uid):
    cur.execute("SELECT points FROM users WHERE id=?", (uid,))
    r = cur.fetchone()
    return r[0] if r else 0

# ========= CHANNEL CHECK (ONLY FIXED) =========
def check_channels(uid):
    for ch in STRICT_CHANNELS:
        try:
            s = bot.get_chat_member(ch, uid).status
            if s not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ========= JOIN KEYBOARD =========
def join_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)

    # fixed channels (checked)
    for ch in STRICT_CHANNELS:
        kb.add(
            types.InlineKeyboardButton(
                "Join",
                url=f"https://t.me/{ch.replace('@','')}"
            )
        )

    # admin-added channels (no check)
    cur.execute("SELECT username FROM channels")
    for (ch,) in cur.fetchall():
        kb.add(
            types.InlineKeyboardButton(
                "Join",
                url=f"https://t.me/{ch.replace('@','')}"
            )
        )

    kb.add(types.InlineKeyboardButton("✅ Joined", callback_data="joined"))
    return kb

# ========= MENUS =========
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔥 Get Method")
    kb.add("🔗 Referral")
    kb.add("👤 Account")
    return kb

# ========= START =========
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    add_user(uid)

    # referral
    if m.text.startswith("/start "):
        try:
            ref = int(m.text.split()[1])
            if ref != uid:
                cur.execute(
                    "UPDATE users SET points = points + ? WHERE id=?",
                    (INVITE_REWARD, ref)
                )
                db.commit()
        except:
            pass

    if not check_channels(uid):
        bot.send_message(
            uid,
            "🚨 <b>Please join all required channels to continue</b>",
            reply_markup=join_keyboard()
        )
        return

    bot.send_message(uid, "✅ <b>Verified</b>", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: c.data == "joined")
def joined(c):
    if check_channels(c.from_user.id):
        bot.send_message(
            c.message.chat.id,
            "✅ <b>Access Granted</b>",
            reply_markup=main_menu()
        )
    else:
        bot.answer_callback_query(
            c.id,
            "❌ Join mandatory channels first",
            show_alert=True
        )

# ========= GET METHOD =========
@bot.message_handler(func=lambda m: m.text == "🔥 Get Method")
def get_method(m):
    if not check_channels(m.from_user.id):
        start(m)
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cur.execute("SELECT name FROM methods")
    for r in cur.fetchall():
        kb.add(r[0])
    kb.add("⬅ Back")

    bot.send_message(m.chat.id, "🔥 <b>Select Method</b>", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "⬅ Back")
def back(m):
    bot.send_message(m.chat.id, "Menu", reply_markup=main_menu())

# ========= ORDER =========
@bot.message_handler(func=lambda m: True)
def order(m):
    uid = m.from_user.id

    if not check_channels(uid):
        start(m)
        return

    cur.execute("SELECT name FROM methods WHERE name=?", (m.text,))
    if not cur.fetchone():
        return

    if get_points(uid) < METHOD_COST:
        bot.send_message(uid, "❌ Not enough points")
        return

    cur.execute(
        "UPDATE users SET points = points - ? WHERE id=?",
        (METHOD_COST, uid)
    )
    db.commit()

    bot.send_message(uid, f"✅ <b>Order placed:</b> {m.text}")

    for a in ADMINS:
        bot.send_message(
            a,
            f"📥 <b>New Order</b>\nUser: <code>{uid}</code>\nMethod: {m.text}"
        )

# ========= REFERRAL =========
@bot.message_handler(func=lambda m: m.text == "🔗 Referral")
def referral(m):
    if not check_channels(m.from_user.id):
        start(m)
        return

    link = f"https://t.me/{bot.get_me().username}?start={m.from_user.id}"
    bot.send_message(
        m.chat.id,
        f"🔗 <b>Your Referral Link</b>\n\n{link}\n\n🎁 +1 Point per user"
    )

# ========= ACCOUNT =========
@bot.message_handler(func=lambda m: m.text == "👤 Account")
def account(m):
    if not check_channels(m.from_user.id):
        start(m)
        return

    bot.send_message(
        m.chat.id,
        f"👤 <b>ID:</b> {m.from_user.id}\n"
        f"💰 <b>Points:</b> {get_points(m.from_user.id)}"
    )

# ========= ADMIN PANEL =========
@bot.message_handler(commands=["admin"])
def admin(m):
    if not is_admin(m.from_user.id):
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Channel", "❌ Delete Channel")
    kb.add("➕ Add Method", "➕ Add Points")
    kb.add("📢 Channels", "❌ Close")

    bot.send_message(m.chat.id, "🛠 <b>Admin Panel</b>", reply_markup=kb)

# --- CHANNEL ADD / DELETE (NO CHECK) ---
@bot.message_handler(func=lambda m: m.text == "➕ Add Channel")
def add_channel(m):
    bot.send_message(m.chat.id, "Send channel username:\nExample: @promo_channel")
    bot.register_next_step_handler(m, save_channel)

def save_channel(m):
    ch = m.text.replace("https://t.me/", "")
    if not ch.startswith("@"):
        bot.send_message(m.chat.id, "❌ Invalid channel")
        return
    cur.execute("INSERT INTO channels VALUES (?)", (ch,))
    db.commit()
    bot.send_message(m.chat.id, "✅ Channel added")

@bot.message_handler(func=lambda m: m.text == "❌ Delete Channel")
def del_channel(m):
    bot.send_message(m.chat.id, "Send channel username to delete:")
    bot.register_next_step_handler(m, save_del)

def save_del(m):
    cur.execute("DELETE FROM channels WHERE username=?", (m.text,))
    db.commit()
    bot.send_message(m.chat.id, "✅ Channel deleted")

@bot.message_handler(func=lambda m: m.text == "📢 Channels")
def list_channels(m):
    cur.execute("SELECT username FROM channels")
    data = cur.fetchall()
    bot.send_message(
        m.chat.id,
        "\n".join([c[0] for c in data]) or "No channels"
    )

# --- METHOD ---
@bot.message_handler(func=lambda m: m.text == "➕ Add Method")
def add_method(m):
    bot.send_message(m.chat.id, "Send method name:")
    bot.register_next_step_handler(m, save_method)

def save_method(m):
    cur.execute("INSERT INTO methods VALUES (?)", (m.text,))
    db.commit()
    bot.send_message(m.chat.id, "✅ Method added")

# --- ADD POINTS ---
@bot.message_handler(func=lambda m: m.text == "➕ Add Points")
def add_points(m):
    bot.send_message(m.chat.id, "Send:\nuser_id points")
    bot.register_next_step_handler(m, save_points)

def save_points(m):
    try:
        uid, pts = map(int, m.text.split())
        cur.execute(
            "UPDATE users SET points = points + ? WHERE id=?",
            (pts, uid)
        )
        db.commit()
        bot.send_message(uid, f"🎁 {pts} points added")
        bot.send_message(m.chat.id, "✅ Done")
    except:
        bot.send_message(m.chat.id, "❌ Invalid format")

@bot.message_handler(func=lambda m: m.text == "❌ Close")
def close(m):
    bot.send_message(m.chat.id, "Closed", reply_markup=main_menu())

# ========= RUN =========
bot.infinity_polling()
