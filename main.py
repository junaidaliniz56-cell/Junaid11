import telebot
from telebot import types
import sqlite3

TOKEN = "8380662421:AAEP9BOevEPJ5CDDwYesgbkNns4bi4bwrH0"
ADMIN_ID = 7011937754  # apna Telegram ID
bot = telebot.TeleBot(TOKEN)

# ===== DATABASE =====
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, points INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS channels (username TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS methods (name TEXT, cost INTEGER, content TEXT)")
db.commit()

# ===== FIXED CHANNELS (BOT ADMIN HERE) =====
FIXED_CHANNELS = [
    "@jndtech1",
    "@jndtech1"
]

# ===== JOIN CHECK =====
def joined(user_id):
    all_channels = FIXED_CHANNELS + [c[0] for c in cur.execute("SELECT username FROM channels")]
    for ch in all_channels:
        try:
            status = bot.get_chat_member(ch, user_id).status
            if status not in ["member", "administrator", "creator"]:
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
            kb.add(types.InlineKeyboardButton("🔗 Join " + ch, url=f"https://t.me/{ch.replace('@','')}"))
        kb.add(types.InlineKeyboardButton("✅ Joined", callback_data="recheck"))
        bot.send_message(uid, "📢 Pehle sab channels join karo", reply_markup=kb)
        return

    bot.send_message(uid, "🔥 Get Method", reply_markup=main_menu())

# ===== MAIN MENU =====
def main_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔥 Get Method", callback_data="get_method"))
    return kb

# ===== CALLBACK HANDLER (IMPORTANT) =====
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    uid = call.from_user.id

    if call.data == "recheck":
        if joined(uid):
            bot.edit_message_text("✅ Verified", uid, call.message.message_id)
            bot.send_message(uid, "🔥 Get Method", reply_markup=main_menu())
        else:
            bot.answer_callback_query(call.id, "❌ Abhi join nahi kiya")

    elif call.data == "get_method":
        cur.execute("SELECT points FROM users WHERE id=?", (uid,))
        pts = cur.fetchone()[0]

        cur.execute("SELECT name, cost FROM methods")
        rows = cur.fetchall()

        if not rows:
            bot.answer_callback_query(call.id, "❌ No methods")
            return

        kb = types.InlineKeyboardMarkup()
        for name, cost in rows:
            kb.add(types.InlineKeyboardButton(f"{name} ({cost} pts)", callback_data=f"method_{name}"))
        bot.send_message(uid, "📂 Methods:", reply_markup=kb)

    elif call.data.startswith("method_"):
        name = call.data.replace("method_", "")
        cur.execute("SELECT cost, content FROM methods WHERE name=?", (name,))
        cost, content = cur.fetchone()

        cur.execute("SELECT points FROM users WHERE id=?", (uid,))
        pts = cur.fetchone()[0]

        if pts < cost:
            bot.answer_callback_query(call.id, "❌ Not enough points")
            return

        cur.execute("UPDATE users SET points=points-? WHERE id=?", (cost, uid))
        db.commit()
        bot.send_message(uid, content)

# ===== /admin =====
@bot.message_handler(commands=["admin"])
def admin(m):
    if m.from_user.id != ADMIN_ID:
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("➕ Add Method", "📋 Method List")
    kb.row("❌ Delete Method")
    kb.row("➕ Add Channel", "📢 Channel List")
    kb.row("❌ Delete Channel")
    kb.row("➕ Add Points", "➖ Cut Points")
    kb.row("❌ Close")
    bot.send_message(m.chat.id, "🛠 Admin Panel", reply_markup=kb)

# ===== ADD CHANNEL =====
@bot.message_handler(func=lambda m: m.text == "➕ Add Channel")
def add_ch(m):
    bot.send_message(m.chat.id, "Send @channelusername")
    bot.register_next_step_handler(m, save_ch)

def save_ch(m):
    ch = m.text.strip()
    if not ch.startswith("@"):
        bot.send_message(m.chat.id, "❌ Only @channelusername")
        return
    cur.execute("INSERT INTO channels VALUES(?)", (ch,))
    db.commit()
    bot.send_message(m.chat.id, "✅ Channel added")

# ===== CHANNEL LIST =====
@bot.message_handler(func=lambda m: m.text == "📢 Channel List")
def ch_list(m):
    rows = cur.execute("SELECT username FROM channels").fetchall()
    if not rows:
        bot.send_message(m.chat.id, "❌ No channels")
        return
    bot.send_message(m.chat.id, "\n".join([c[0] for c in rows]))

# ===== BOT START =====
print("Bot running...")
bot.infinity_polling()
