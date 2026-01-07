import telebot
from telebot import types
import sqlite3

# ================= CONFIG =================

TOKEN = "8380662421:AAEP9BOevEPJ5CDDwYesgbkNns4bi4bwrH0"
ADMINS = [7011937754]

METHOD_COST = 7
INVITE_REWARD = 1

# Fixed mandatory channels (bot MUST be admin)
STRICT_CHANNELS = ["@jndtech1", "@jndtech1"]

bot = telebot.TeleBot(TOKEN)

# ================= DATABASE =================

db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, points INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS methods (name TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS channels (username TEXT)")
db.commit()

# ================= HELPERS =================

def is_admin(uid):
    return uid in ADMINS

def get_points(uid):
    cur.execute("SELECT points FROM users WHERE id=?", (uid,))
    r = cur.fetchone()
    return r[0] if r else 0

def add_points(uid, p):
    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)", (uid, 0))
    cur.execute("UPDATE users SET points = points + ? WHERE id=?", (p, uid))
    db.commit()

def cut_points(uid, p):
    cur.execute("UPDATE users SET points = points - ? WHERE id=?", (p, uid))
    db.commit()

def check_channels(uid):
    for ch in STRICT_CHANNELS:
        try:
            s = bot.get_chat_member(ch, uid).status
            if s not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ================= KEYBOARDS =================

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔥 Get Method")
    kb.add("👤 Account", "🔗 Referral")
    return kb

def join_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)

    for ch in STRICT_CHANNELS:
        kb.add(types.InlineKeyboardButton("Join", url=f"https://t.me/{ch.replace('@','')}"))

    cur.execute("SELECT username FROM channels")
    for (c,) in cur.fetchall():
        kb.add(types.InlineKeyboardButton("Join", url=f"https://t.me/{c.replace('@','')}"))

    kb.add(types.InlineKeyboardButton("✅ Joined", callback_data="joined"))
    return kb

# ================= START =================

@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    add_points(uid, 0)

    if not check_channels(uid):
        bot.send_message(
            uid,
            "🚫 Please join required channels first",
            reply_markup=join_keyboard()
        )
        return

    # referral
    if m.text.startswith("/start "):
        ref = int(m.text.split()[1])
        if ref != uid:
            add_points(ref, INVITE_REWARD)

    bot.send_message(uid, "✅ Verified", reply_markup=main_menu())

# ================= JOIN CHECK =================

@bot.callback_query_handler(func=lambda c: c.data == "joined")
def joined(c):
    if not check_channels(c.from_user.id):
        bot.answer_callback_query(c.id, "❌ Join all required channels", show_alert=True)
        return

    bot.send_message(c.from_user.id, "✅ Access granted", reply_markup=main_menu())

# ================= USER =================

@bot.message_handler(func=lambda m: m.text == "👤 Account")
def account(m):
    bot.send_message(
        m.chat.id,
        f"👤 ID: {m.from_user.id}\n💰 Points: {get_points(m.from_user.id)}"
    )

@bot.message_handler(func=lambda m: m.text == "🔗 Referral")
def referral(m):
    link = f"https://t.me/{bot.get_me().username}?start={m.from_user.id}"
    bot.send_message(
        m.chat.id,
        f"🔗 Your link:\n{link}\n🎁 +{INVITE_REWARD} point per user"
    )

# ================= METHODS =================

@bot.message_handler(func=lambda m: m.text == "🔥 Get Method")
def get_method(m):
    pts = get_points(m.from_user.id)
    if pts < METHOD_COST:
        bot.send_message(m.chat.id, "❌ Not enough points")
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cur.execute("SELECT name FROM methods")
    for (n,) in cur.fetchall():
        kb.add(n)
    kb.add("❌ Cancel")

    bot.send_message(m.chat.id, "Select method:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text not in ["❌ Cancel"] and get_points(m.from_user.id) >= METHOD_COST)
def order(m):
    cur.execute("SELECT name FROM methods WHERE name=?", (m.text,))
    if not cur.fetchone():
        return

    cut_points(m.from_user.id, METHOD_COST)

    for a in ADMINS:
        bot.send_message(
            a,
            f"📥 New Order\n👤 {m.from_user.id}\n📦 {m.text}"
        )

    bot.send_message(m.chat.id, "✅ Order sent to admin", reply_markup=main_menu())

# ================= ADMIN =================

@bot.message_handler(commands=["admin"])
def admin(m):
    if not is_admin(m.from_user.id):
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Method", "🗑 Delete Method")
    kb.add("➕ Add Channel", "📢 Channels")
    kb.add("➕ Add Points", "➖ Cut Points")
    kb.add("❌ Close")

    bot.send_message(m.chat.id, "🛠 Admin Panel", reply_markup=kb)

# ---------- ADD METHOD ----------

@bot.message_handler(func=lambda m: m.text == "➕ Add Method")
def am(m):
    bot.send_message(m.chat.id, "Send method name:")
    bot.register_next_step_handler(m, save_method)

def save_method(m):
    cur.execute("INSERT INTO methods VALUES (?)", (m.text,))
    db.commit()
    bot.send_message(m.chat.id, "✅ Method added")

# ---------- DELETE METHOD ----------

@bot.message_handler(func=lambda m: m.text == "🗑 Delete Method")
def dm(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cur.execute("SELECT name FROM methods")
    for (n,) in cur.fetchall():
        kb.add(n)
    bot.send_message(m.chat.id, "Select method to delete:", reply_markup=kb)
    bot.register_next_step_handler(m, del_method)

def del_method(m):
    cur.execute("DELETE FROM methods WHERE name=?", (m.text,))
    db.commit()
    bot.send_message(m.chat.id, "❌ Method deleted")

# ---------- ADD CHANNEL (SHOW ONLY) ----------

@bot.message_handler(func=lambda m: m.text == "➕ Add Channel")
def ac(m):
    bot.send_message(m.chat.id, "Send channel username (@channel):")
    bot.register_next_step_handler(m, save_channel)

def save_channel(m):
    ch = m.text.replace("https://t.me/", "")
    if not ch.startswith("@"):
        bot.send_message(m.chat.id, "❌ Invalid channel")
        return
    cur.execute("INSERT INTO channels VALUES (?)", (ch,))
    db.commit()
    bot.send_message(m.chat.id, "✅ Channel added")

# ---------- POINTS ----------

@bot.message_handler(func=lambda m: m.text == "➕ Add Points")
def ap(m):
    bot.send_message(m.chat.id, "Send: user_id points")
    bot.register_next_step_handler(m, addp)

def addp(m):
    uid, p = map(int, m.text.split())
    add_points(uid, p)
    bot.send_message(m.chat.id, "✅ Points added")

@bot.message_handler(func=lambda m: m.text == "➖ Cut Points")
def cp(m):
    bot.send_message(m.chat.id, "Send: user_id points")
    bot.register_next_step_handler(m, cutp)

def cutp(m):
    uid, p = map(int, m.text.split())
    cut_points(uid, p)
    bot.send_message(m.chat.id, "✅ Points cut")

# ---------- CLOSE ----------

@bot.message_handler(func=lambda m: m.text == "❌ Close")
def close(m):
    bot.send_message(m.chat.id, "Closed", reply_markup=main_menu())

# ================= RUN =================

print("Bot running...")
bot.infinity_polling()
