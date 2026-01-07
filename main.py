import telebot
from telebot import types
import sqlite3

# ========= CONFIG =========
TOKEN = "8380662421:AAEP9BOevEPJ5CDDwYesgbkNns4bi4bwrH0"
ADMINS = [7011937754]     # 👈 apna numeric Telegram ID
METHOD_COST = 7
INVITE_REWARD = 1

# FORCE JOIN CHANNELS (BOT ADMIN HONA ZARURI)
FORCE_CHANNELS = [
    "https://t.me/junaidniz110",
    "https://t.me/jndtech1"
]

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ========= DATABASE =========
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0,
    invited_by INTEGER
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link TEXT
)""")

db.commit()

# ========= HELPERS =========
def is_admin(uid):
    return uid in ADMINS

def get_user(uid):
    cur.execute("SELECT * FROM users WHERE id=?", (uid,))
    u = cur.fetchone()
    if not u:
        cur.execute("INSERT INTO users (id, points) VALUES (?,0)", (uid,))
        db.commit()
        return (uid, 0, None)
    return u

def add_points(uid, p):
    cur.execute("UPDATE users SET points = points + ? WHERE id=?", (p, uid))
    db.commit()

def cut_points(uid, p):
    cur.execute("UPDATE users SET points = points - ? WHERE id=?", (p, uid))
    db.commit()

def check_join(uid):
    for ch in FORCE_CHANNELS:
        username = ch.split("/")[-1]
        try:
            m = bot.get_chat_member(f"@{username}", uid)
            if m.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

# ========= KEYBOARDS =========
def join_kb():
    kb = types.InlineKeyboardMarkup()
    for ch in FORCE_CHANNELS:
        kb.add(types.InlineKeyboardButton("📢 Join Channel", url=ch))
    kb.add(types.InlineKeyboardButton("✅ Join Check", callback_data="join_check"))
    return kb

def user_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔥 Get Method")
    kb.add("👤 Account", "🎁 Referral")
    return kb

def admin_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Method", "❌ Delete Method")
    kb.add("➕ Add Channel", "📋 Channels List")
    kb.add("➕ Add Points", "➖ Cut Points")
    kb.add("❌ Close")
    return kb

# ========= START =========
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    get_user(uid)

    if not check_join(uid):
        bot.send_message(
            uid,
            "🚫 <b>First Join All Channels</b>",
            reply_markup=join_kb()
        )
        return

    bot.send_message(
        uid,
        "✅ <b>Welcome</b>\nSelect option:",
        reply_markup=user_kb()
    )

# ========= JOIN CHECK =========
@bot.callback_query_handler(func=lambda c: c.data == "join_check")
def join_check(c):
    if check_join(c.from_user.id):
        bot.edit_message_text(
            "✅ <b>Join Verified</b>",
            c.message.chat.id,
            c.message.message_id
        )
        bot.send_message(
            c.from_user.id,
            "🎉 Access Granted",
            reply_markup=user_kb()
        )
    else:
        bot.answer_callback_query(
            c.id,
            "❌ Join all channels first",
            show_alert=True
        )

# ========= USER =========
@bot.message_handler(func=lambda m: m.text == "👤 Account")
def account(m):
    u = get_user(m.from_user.id)
    bot.send_message(
        m.chat.id,
        f"👤 <b>Your Account</b>\n\n"
        f"🆔 ID: <code>{u[0]}</code>\n"
        f"💰 Points: <b>{u[1]}</b>"
    )

@bot.message_handler(func=lambda m: m.text == "🎁 Referral")
def referral(m):
    uid = m.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={uid}"
    bot.send_message(
        uid,
        f"🎁 <b>Referral System</b>\n\n"
        f"Invite friends & earn <b>{INVITE_REWARD} point</b>\n\n"
        f"🔗 {link}"
    )

# ========= METHODS =========
@bot.message_handler(func=lambda m: m.text == "🔥 Get Method")
def get_method(m):
    uid = m.from_user.id
    u = get_user(uid)

    if u[1] < METHOD_COST:
        bot.send_message(
            uid,
            f"❌ Not enough points\nRequired: {METHOD_COST}"
        )
        return

    rows = cur.execute("SELECT id,name FROM methods").fetchall()
    if not rows:
        bot.send_message(uid, "❌ No methods available")
        return

    kb = types.InlineKeyboardMarkup()
    for mid, name in rows:
        kb.add(types.InlineKeyboardButton(name, callback_data=f"order_{mid}"))

    bot.send_message(
        uid,
        f"🔥 <b>Select Method</b>\n💰 Fee: {METHOD_COST} Points",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("order_"))
def order(c):
    uid = c.from_user.id
    mid = int(c.data.split("_")[1])

    if get_user(uid)[1] < METHOD_COST:
        bot.answer_callback_query(c.id, "❌ Not enough points", True)
        return

    cut_points(uid, METHOD_COST)

    name = cur.execute(
        "SELECT name FROM methods WHERE id=?", (mid,)
    ).fetchone()[0]

    for a in ADMINS:
        bot.send_message(
            a,
            f"📥 <b>New Order</b>\n\n"
            f"👤 User: <code>{uid}</code>\n"
            f"🔥 Method: <b>{name}</b>\n"
            f"💰 Fee: {METHOD_COST}"
        )

    bot.answer_callback_query(c.id, "✅ Order Placed")
    bot.send_message(uid, "✅ Order successful\nPoints deducted")

# ========= ADMIN =========
@bot.message_handler(commands=["admin"])
def admin(m):
    if not is_admin(m.from_user.id):
        return
    bot.send_message(
        m.chat.id,
        "🛠 <b>Admin Panel</b>",
        reply_markup=admin_kb()
    )

@bot.message_handler(func=lambda m: m.text == "➕ Add Method")
def add_method(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id, "Send method name only")
    bot.register_next_step_handler(msg, save_method)

def save_method(m):
    cur.execute("INSERT INTO methods (name) VALUES (?)", (m.text.strip(),))
    db.commit()
    bot.send_message(m.chat.id, "✅ Method added")

@bot.message_handler(func=lambda m: m.text == "❌ Delete Method")
def del_method(m):
    if not is_admin(m.from_user.id): return
    rows = cur.execute("SELECT id,name FROM methods").fetchall()
    kb = types.InlineKeyboardMarkup()
    for i,n in rows:
        kb.add(types.InlineKeyboardButton(n, callback_data=f"delm_{i}"))
    bot.send_message(m.chat.id, "Select method to delete", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("delm_"))
def delm(c):
    mid = int(c.data.split("_")[1])
    cur.execute("DELETE FROM methods WHERE id=?", (mid,))
    db.commit()
    bot.answer_callback_query(c.id, "Deleted")
    bot.edit_message_text("✅ Method deleted", c.message.chat.id, c.message.message_id)

@bot.message_handler(func=lambda m: m.text == "❌ Close")
def close(m):
    bot.send_message(m.chat.id, "Closed", reply_markup=types.ReplyKeyboardRemove())

# ========= RUN =========
print("Bot running...")
bot.infinity_polling()
