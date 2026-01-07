import telebot
from telebot import types
import sqlite3

# ========== CONFIG ==========
TOKEN = "YOUR_BOT_TOKEN"
ADMINS = [7011937754]

METHOD_COST = 7
INVITE_REWARD = 1

# 🔒 FIXED CHANNELS (PUBLIC ONLY)
CHANNELS = [
    "@Jndtech1",
    "@Jndtech1",
    "@Jndtech1"
]

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ========== DATABASE ==========
db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS referrals (
    referrer INTEGER,
    user INTEGER UNIQUE
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT
)
""")
db.commit()

# ========== HELPERS ==========
def is_admin(uid):
    return uid in ADMINS

def get_points(uid):
    cur.execute("SELECT points FROM users WHERE id=?", (uid,))
    r = cur.fetchone()
    return r[0] if r else 0

def check_channels(uid):
    for ch in CHANNELS:
        try:
            m = bot.get_chat_member(ch, uid)
            if m.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

def join_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    for ch in CHANNELS:
        kb.add(types.InlineKeyboardButton("Join", url=f"https://t.me/{ch.replace('@','')}"))
    kb.add(types.InlineKeyboardButton("✅ Joined", callback_data="check_join"))
    return kb

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔥 Get Method")
    kb.add("🔗 Referral")
    kb.add("👤 Account")
    return kb

# ========== START ==========
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    args = m.text.split()

    cur.execute("INSERT OR IGNORE INTO users (id, points) VALUES (?,0)", (uid,))
    db.commit()

    # referral
    if len(args) > 1:
        try:
            ref = int(args[1])
            if ref != uid:
                cur.execute(
                    "INSERT OR IGNORE INTO referrals (referrer, user) VALUES (?,?)",
                    (ref, uid)
                )
                if cur.rowcount > 0:
                    cur.execute(
                        "UPDATE users SET points = points + ? WHERE id=?",
                        (INVITE_REWARD, ref)
                    )
                    db.commit()
        except:
            pass

    if not check_channels(uid):
        bot.send_message(
            m.chat.id,
            "🚫 <b>Please join all required channels first</b>",
            reply_markup=join_keyboard()
        )
        return

    bot.send_message(
        m.chat.id,
        "✅ <b>Welcome</b>",
        reply_markup=main_menu()
    )

# ========== JOIN CHECK ==========
@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def joined(c):
    if check_channels(c.from_user.id):
        bot.edit_message_text(
            "✅ <b>Access Granted</b>",
            c.message.chat.id,
            c.message.message_id
        )
        bot.send_message(c.message.chat.id, "Main Menu", reply_markup=main_menu())
    else:
        bot.answer_callback_query(c.id, "❌ Join all channels first", show_alert=True)

# ========== BLOCK IF NOT JOINED ==========
def guard(m):
    if not check_channels(m.from_user.id):
        bot.send_message(
            m.chat.id,
            "🚫 Join required channels first",
            reply_markup=join_keyboard()
        )
        return False
    return True

# ========== ACCOUNT ==========
@bot.message_handler(func=lambda m: m.text == "👤 Account")
def account(m):
    if not guard(m): return
    bot.send_message(
        m.chat.id,
        f"👤 <b>Account</b>\n\n💰 Points: <b>{get_points(m.from_user.id)}</b>"
    )

# ========== REFERRAL ==========
@bot.message_handler(func=lambda m: m.text == "🔗 Referral")
def referral(m):
    if not guard(m): return
    link = f"https://t.me/{bot.get_me().username}?start={m.from_user.id}"
    bot.send_message(
        m.chat.id,
        f"🔗 <b>Your Referral Link</b>\n\n{link}\n\n🎁 +1 point per user"
    )

# ========== SHOW METHODS ==========
@bot.message_handler(func=lambda m: m.text == "🔥 Get Method")
def methods(m):
    if not guard(m): return
    cur.execute("SELECT id,title FROM methods")
    rows = cur.fetchall()

    if not rows:
        bot.send_message(m.chat.id, "❌ No methods available")
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i,t in rows:
        kb.add(f"{i}. {t}")
    kb.add("⬅ Back")

    bot.send_message(
        m.chat.id,
        "🔥 <b>Select Method (7 Points)</b>",
        reply_markup=kb
    )

# ========== ORDER ==========
@bot.message_handler(func=lambda m: m.text and m.text.split(".")[0].isdigit())
def order(m):
    if not guard(m): return

    uid = m.from_user.id
    mid = int(m.text.split(".")[0])

    cur.execute("SELECT title FROM methods WHERE id=?", (mid,))
    r = cur.fetchone()
    if not r: return

    if get_points(uid) < METHOD_COST:
        bot.send_message(m.chat.id, "❌ Not enough points")
        return

    cur.execute(
        "UPDATE users SET points = points - ? WHERE id=?",
        (METHOD_COST, uid)
    )
    db.commit()

    title = r[0]

    bot.send_message(
        m.chat.id,
        f"✅ <b>Order Placed</b>\n\n📦 {title}\n⏳ Admin will contact you",
        reply_markup=main_menu()
    )

    for a in ADMINS:
        bot.send_message(
            a,
            f"🆕 <b>NEW ORDER</b>\n\n"
            f"👤 {uid}\n"
            f"📛 @{m.from_user.username}\n"
            f"📦 {title}\n"
            f"💰 7 Points"
        )

# ========== ADMIN ADD METHOD ==========
@bot.message_handler(commands=["admin"])
def admin(m):
    if not is_admin(m.from_user.id): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Method", "📋 Methods", "❌ Close")
    bot.send_message(m.chat.id, "🛠 Admin Panel", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "➕ Add Method")
def add_m(m):
    if not is_admin(m.from_user.id): return
    bot.send_message(m.chat.id, "Send method name only")
    bot.register_next_step_handler(m, save_m)

def save_m(m):
    if not is_admin(m.from_user.id): return
    cur.execute("INSERT INTO methods (title) VALUES (?)", (m.text.strip(),))
    db.commit()
    bot.send_message(m.chat.id, "✅ Method added")

@bot.message_handler(func=lambda m: m.text == "📋 Methods")
def list_m(m):
    if not is_admin(m.from_user.id): return
    cur.execute("SELECT id,title FROM methods")
    t = "\n".join([f"{i}. {n}" for i,n in cur.fetchall()])
    bot.send_message(m.chat.id, t or "No methods")

# ========== RUN ==========
print("Bot running...")
bot.infinity_polling()
