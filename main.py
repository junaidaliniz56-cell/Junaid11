import telebot
from telebot import types
import sqlite3

TOKEN = "8380662421:AAEP9BOevEPJ5CDDwYesgbkNns4bi4bwrH0"
ADMIN_ID = 7011937754   # apna Telegram ID
bot = telebot.TeleBot(TOKEN)

# ===== DATABASE =====
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, points INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS channels (username TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS methods (name TEXT, cost INTEGER, content TEXT)")
db.commit()

FIXED_CHANNELS = ["@jndtech1", "@jndtech1"]

# ===== JOIN CHECK =====
def joined(uid):
    all_ch = FIXED_CHANNELS + [c[0] for c in cur.execute("SELECT username FROM channels")]
    for ch in all_ch:
        try:
            st = bot.get_chat_member(ch, uid).status
            if st not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ===== /start =====
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)", (uid, 0))
    db.commit()

    if not joined(uid):
        kb = types.InlineKeyboardMarkup()
        for ch in FIXED_CHANNELS + [c[0] for c in cur.execute("SELECT username FROM channels")]:
            kb.add(types.InlineKeyboardButton("🔗 Join " + ch, url=f"https://t.me/{ch[1:]}"))
        kb.add(types.InlineKeyboardButton("✅ Joined", callback_data="recheck"))
        bot.send_message(uid, "📢 Pehle channels join karo", reply_markup=kb)
        return

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔥 Get Method", callback_data="get_method"))
    bot.send_message(uid, "🔥 Get Method", reply_markup=kb)

# ===== CALLBACKS =====
@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    uid = c.from_user.id

    if c.data == "recheck":
        if joined(uid):
            bot.edit_message_text("✅ Verified", uid, c.message.message_id)
        else:
            bot.answer_callback_query(c.id, "❌ Join pending")

    elif c.data == "get_method":
        rows = cur.execute("SELECT name,cost FROM methods").fetchall()
        if not rows:
            bot.answer_callback_query(c.id, "❌ No methods")
            return
        kb = types.InlineKeyboardMarkup()
        for n, p in rows:
            kb.add(types.InlineKeyboardButton(f"{n} ({p})", callback_data=f"m_{n}"))
        bot.send_message(uid, "📂 Methods:", reply_markup=kb)

    elif c.data.startswith("m_"):
        name = c.data[2:]
        cost, txt = cur.execute(
            "SELECT cost,content FROM methods WHERE name=?", (name,)
        ).fetchone()

        pts = cur.execute(
            "SELECT points FROM users WHERE id=?", (uid,)
        ).fetchone()[0]

        if pts < cost:
            bot.answer_callback_query(c.id, "❌ Not enough points")
            return

        cur.execute("UPDATE users SET points=points-? WHERE id=?", (cost, uid))
        db.commit()
        bot.send_message(uid, txt)

# ===== ADMIN PANEL =====
@bot.message_handler(commands=["admin"])
def admin(m):
    if m.from_user.id != ADMIN_ID:
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("➕ Add Method", "📋 Method List")
    kb.row("➕ Add Channel", "📢 Channel List")
    kb.row("➕ Add Points", "➖ Cut Points")
    kb.row("❌ Close")
    bot.send_message(m.chat.id, "🛠 Admin Panel", reply_markup=kb)

# ===== ADD METHOD =====
@bot.message_handler(func=lambda m: m.text == "➕ Add Method")
def add_method(m):
    bot.send_message(m.chat.id, "Method name bhejo")
    bot.register_next_step_handler(m, method_name)

def method_name(m):
    name = m.text
    bot.send_message(m.chat.id, "Points cost bhejo")
    bot.register_next_step_handler(m, method_cost, name)

def method_cost(m, name):
    if not m.text.isdigit():
        bot.send_message(m.chat.id, "❌ Number bhejo")
        return
    cost = int(m.text)
    bot.send_message(m.chat.id, "Method content bhejo")
    bot.register_next_step_handler(m, method_content, name, cost)

def method_content(m, name, cost):
    cur.execute("INSERT INTO methods VALUES (?,?,?)", (name, cost, m.text))
    db.commit()
    bot.send_message(m.chat.id, "✅ Method added")

# ===== METHOD LIST =====
@bot.message_handler(func=lambda m: m.text == "📋 Method List")
def ml(m):
    rows = cur.execute("SELECT name,cost FROM methods").fetchall()
    if not rows:
        bot.send_message(m.chat.id, "❌ No methods")
        return
    bot.send_message(m.chat.id, "\n".join([f"{n} - {c}" for n, c in rows]))

# ===== ADD POINTS =====
@bot.message_handler(func=lambda m: m.text == "➕ Add Points")
def add_pts(m):
    bot.send_message(m.chat.id, "User ID bhejo")
    bot.register_next_step_handler(m, pts_uid)

def pts_uid(m):
    if not m.text.isdigit():
        bot.send_message(m.chat.id, "❌ Invalid ID")
        return
    uid = int(m.text)
    bot.send_message(m.chat.id, "Points bhejo")
    bot.register_next_step_handler(m, pts_add, uid)

def pts_add(m, uid):
    if not m.text.isdigit():
        bot.send_message(m.chat.id, "❌ Number bhejo")
        return
    cur.execute("UPDATE users SET points=points+? WHERE id=?", (int(m.text), uid))
    db.commit()
    bot.send_message(m.chat.id, "✅ Points added")

# ===== CUT POINTS =====
@bot.message_handler(func=lambda m: m.text == "➖ Cut Points")
def cut_pts(m):
    bot.send_message(m.chat.id, "User ID bhejo")
    bot.register_next_step_handler(m, cut_uid)

def cut_uid(m):
    uid = int(m.text)
    bot.send_message(m.chat.id, "Points bhejo")
    bot.register_next_step_handler(m, cut_do, uid)

def cut_do(m, uid):
    cur.execute("UPDATE users SET points=points-? WHERE id=?", (int(m.text), uid))
    db.commit()
    bot.send_message(m.chat.id, "✅ Points cut")

# ===== CHANNEL =====
@bot.message_handler(func=lambda m: m.text == "➕ Add Channel")
def add_ch(m):
    bot.send_message(m.chat.id, "@channelusername bhejo")
    bot.register_next_step_handler(m, save_ch)

def save_ch(m):
    cur.execute("INSERT INTO channels VALUES(?)", (m.text,))
    db.commit()
    bot.send_message(m.chat.id, "✅ Channel added")

@bot.message_handler(func=lambda m: m.text == "📢 Channel List")
def cl(m):
    rows = cur.execute("SELECT username FROM channels").fetchall()
    bot.send_message(m.chat.id, "\n".join([r[0] for r in rows]) or "❌ Empty")

# ===== CLOSE =====
@bot.message_handler(func=lambda m: m.text == "❌ Close")
def close(m):
    bot.send_message(m.chat.id, "❌ Closed", reply_markup=types.ReplyKeyboardRemove())

print("Bot running...")
bot.infinity_polling()
