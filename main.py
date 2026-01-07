import telebot
from telebot import types
import sqlite3

TOKEN = "8380662421:AAEP9BOevEPJ5CDDwYesgbkNns4bi4bwrH0"
ADMINS = [7011937754]

FIXED_CHANNELS = [
    "@jndtech1",
    "@jndtech1"
]

METHOD_COST = 7
INVITE_REWARD = 1

bot = telebot.TeleBot(TOKEN)
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

# ================= DB =================
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, points INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS channels (username TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS methods (name TEXT)")
db.commit()

# ================= UTILS =================
def is_admin(uid):
    return uid in ADMINS

def user(uid):
    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)", (uid, 0))
    db.commit()

# ================= CHANNEL UI =================
def send_channels(uid):
    kb = types.InlineKeyboardMarkup(row_width=2)

    chs = cur.execute("SELECT username FROM channels").fetchall()

    for c in chs:
        try:
            bot.get_chat(c[0])
            kb.add(types.InlineKeyboardButton("Join", url=f"https://t.me/{c[0][1:]}"))
        except:
            cur.execute("DELETE FROM channels WHERE username=?", (c[0],))
            db.commit()

    for fc in FIXED_CHANNELS:
        kb.add(types.InlineKeyboardButton("Join", url=f"https://t.me/{fc[1:]}"))

    kb.add(types.InlineKeyboardButton("✅ Joined", callback_data="check"))

    bot.send_message(
        uid,
        "🚨 Please join all required channels before using the bot!",
        reply_markup=kb
    )

# ================= JOIN CHECK =================
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(c):
    uid = c.from_user.id

    for ch in FIXED_CHANNELS:
        try:
            s = bot.get_chat_member(ch, uid).status
            if s not in ["member", "administrator", "creator"]:
                send_channels(uid)
                return
        except:
            send_channels(uid)
            return

    bot.send_message(uid, "✅ Verified")
    main_menu(uid)

# ================= MENUS =================
def main_menu(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔥 Get Method")
    kb.add("👤 Account", "🔗 Referral")
    bot.send_message(uid, "Welcome!", reply_markup=kb)

def admin_menu(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Method", "📋 Method List")
    kb.add("➕ Add Channel", "📢 Channel List")
    kb.add("➕ Add Points", "➖ Cut Points")
    kb.add("❌ Close")
    bot.send_message(uid, "🛠 Admin Panel", reply_markup=kb)

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    user(m.chat.id)
    send_channels(m.chat.id)

# ================= ADMIN =================
@bot.message_handler(commands=["admin"])
def admin(m):
    if not is_admin(m.chat.id): return
    admin_menu(m.chat.id)

# ================= ADD CHANNEL =================
@bot.message_handler(func=lambda m: m.text == "➕ Add Channel")
def add_channel(m):
    if not is_admin(m.chat.id): return
    msg = bot.send_message(m.chat.id, "Send channel username (@channel)")
    bot.register_next_step_handler(msg, save_channel)

def save_channel(m):
    if not m.text.startswith("@"):
        bot.send_message(m.chat.id, "❌ Invalid username")
        return
    cur.execute("INSERT INTO channels VALUES (?)", (m.text,))
    db.commit()
    bot.send_message(m.chat.id, "✅ Channel added")

# ================= ADD METHOD =================
@bot.message_handler(func=lambda m: m.text == "➕ Add Method")
def add_method(m):
    if not is_admin(m.chat.id): return
    msg = bot.send_message(m.chat.id, "Send method name")
    bot.register_next_step_handler(msg, save_method)

def save_method(m):
    cur.execute("INSERT INTO methods VALUES (?)", (m.text,))
    db.commit()
    bot.send_message(m.chat.id, "✅ Method added")

# ================= GET METHOD =================
@bot.message_handler(func=lambda m: m.text == "🔥 Get Method")
def get_method(m):
    uid = m.chat.id
    p = cur.execute("SELECT points FROM users WHERE id=?", (uid,)).fetchone()[0]
    if p < METHOD_COST:
        bot.send_message(uid, "❌ Not enough points")
        return

    methods = cur.execute("SELECT name FROM methods").fetchall()
    if not methods:
        bot.send_message(uid, "❌ No methods available")
        return

    cur.execute("UPDATE users SET points=points-? WHERE id=?", (METHOD_COST, uid))
    db.commit()

    bot.send_message(uid, "🔥 Available Methods:\n\n" + "\n".join([x[0] for x in methods]))

    for a in ADMINS:
        bot.send_message(a, f"📥 New Order\nUser: {uid}")

# ================= REFERRAL =================
@bot.message_handler(func=lambda m: m.text == "🔗 Referral")
def ref(m):
    bot.send_message(
        m.chat.id,
        f"🔗 Your link:\nhttps://t.me/{bot.get_me().username}?start={m.chat.id}"
    )

# ================= ACCOUNT =================
@bot.message_handler(func=lambda m: m.text == "👤 Account")
def acc(m):
    p = cur.execute("SELECT points FROM users WHERE id=?", (m.chat.id,)).fetchone()[0]
    bot.send_message(m.chat.id, f"👤 ID: {m.chat.id}\n💰 Points: {p}")

# ================= RUN =================
bot.infinity_polling()
