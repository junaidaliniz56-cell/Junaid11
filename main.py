import telebot
from telebot import types
import sqlite3

# ========= CONFIG =========
TOKEN = "PASTE_YOUR_BOT_TOKEN"
ADMINS = [7011937754]
METHOD_COST = 7
REFERRAL_REWARD = 1

# ========= BOT =========
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ========= DATABASE =========
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0,
    ref_by INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    value TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
)
""")
db.commit()

# ========= HELPERS =========
def is_admin(uid):
    return uid in ADMINS

def get_user(uid):
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    u = cur.fetchone()
    if not u:
        cur.execute("INSERT INTO users (user_id, points) VALUES (?,?)", (uid, 0))
        db.commit()
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    return cur.fetchone()

def add_points(uid, pts):
    cur.execute("UPDATE users SET points = points + ? WHERE user_id=?", (pts, uid))
    db.commit()

def cut_points(uid, pts):
    cur.execute("UPDATE users SET points = points - ? WHERE user_id=?", (pts, uid))
    db.commit()

# ========= JOIN CHECK =========
def is_joined(uid):
    rows = cur.execute("SELECT value FROM channels").fetchall()
    for (ch,) in rows:
        if ch.startswith("@") or ch.startswith("-100"):
            try:
                m = bot.get_chat_member(ch, uid)
                if m.status not in ["member", "administrator", "creator"]:
                    return False
            except:
                return False
    return True

def send_join(uid):
    kb = types.InlineKeyboardMarkup()
    rows = cur.execute("SELECT value FROM channels").fetchall()
    for (ch,) in rows:
        if ch.startswith("@"):
            kb.add(types.InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{ch[1:]}"))
        elif ch.startswith("https://t.me"):
            kb.add(types.InlineKeyboardButton("🔔 Join Channel", url=ch))
    kb.add(types.InlineKeyboardButton("✅ Joined", callback_data="check_join"))
    bot.send_message(uid, "🚨 Join all channels to continue", reply_markup=kb)

# ========= START + REFERRAL =========
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    args = m.text.split()

    get_user(uid)

    # referral handling
    if len(args) > 1:
        ref = int(args[1])
        if ref != uid:
            cur.execute("SELECT ref_by FROM users WHERE user_id=?", (uid,))
            if cur.fetchone()[0] is None:
                cur.execute("UPDATE users SET ref_by=? WHERE user_id=?", (ref, uid))
                add_points(ref, REFERRAL_REWARD)
                bot.send_message(ref, f"🎉 Referral joined! +{REFERRAL_REWARD} point")
                db.commit()

    if not is_joined(uid):
        send_join(uid)
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔥 Get Method", "👤 Account", "👥 Referral")
    if is_admin(uid):
        kb.add("🛠 Admin Panel")

    bot.send_message(uid, "✅ Verified & Welcome", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def join_cb(c):
    if is_joined(c.from_user.id):
        bot.answer_callback_query(c.id, "Verified")
        bot.send_message(c.message.chat.id, "Press /start")
    else:
        bot.answer_callback_query(c.id, "Join all channels", show_alert=True)

# ========= ACCOUNT =========
@bot.message_handler(func=lambda m: m.text == "👤 Account")
def account(m):
    u = get_user(m.from_user.id)
    bot.send_message(
        m.chat.id,
        f"👤 <b>Your Account</b>\n\n💰 Points: <b>{u[1]}</b>"
    )

# ========= REFERRAL =========
@bot.message_handler(func=lambda m: m.text == "👥 Referral")
def referral(m):
    link = f"https://t.me/{bot.get_me().username}?start={m.from_user.id}"
    bot.send_message(
        m.chat.id,
        f"👥 <b>Your Referral Link</b>\n\n{link}\n\nInvite = +{REFERRAL_REWARD} point"
    )

# ========= GET METHOD =========
@bot.message_handler(func=lambda m: m.text == "🔥 Get Method")
def get_method(m):
    if get_user(m.from_user.id)[1] < METHOD_COST:
        bot.send_message(m.chat.id, "❌ Not enough points")
        return

    kb = types.InlineKeyboardMarkup()
    rows = cur.execute("SELECT id, name FROM methods").fetchall()
    if not rows:
        bot.send_message(m.chat.id, "No methods available")
        return

    for i, n in rows:
        kb.add(types.InlineKeyboardButton(n, callback_data=f"order_{i}"))

    bot.send_message(m.chat.id, "🔥 Select Method", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("order_"))
def order(c):
    uid = c.from_user.id
    mid = int(c.data.split("_")[1])

    if get_user(uid)[1] < METHOD_COST:
        bot.answer_callback_query(c.id, "Not enough points", show_alert=True)
        return

    cut_points(uid, METHOD_COST)
    name = cur.execute("SELECT name FROM methods WHERE id=?", (mid,)).fetchone()[0]

    for a in ADMINS:
        bot.send_message(
            a,
            f"📥 <b>New Order</b>\n\n"
            f"👤 User: {uid}\n"
            f"🔥 Method: {name}\n"
            f"💰 Cost: {METHOD_COST}"
        )

    bot.answer_callback_query(c.id, "Order placed")
    bot.send_message(uid, "✅ Order placed, admin notified")

# ========= ADMIN PANEL =========
@bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel")
def admin_panel(m):
    if not is_admin(m.from_user.id):
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Channel", "📋 Channels List")
    kb.add("➕ Add Method", "📋 Methods List")
    kb.add("➕ Add Points", "➖ Cut Points")
    kb.add("❌ Close")
    bot.send_message(m.chat.id, "🛠 Admin Panel", reply_markup=kb)

# ========= ADD CHANNEL =========
@bot.message_handler(func=lambda m: m.text == "➕ Add Channel")
def add_channel(m):
    msg = bot.send_message(m.chat.id, "Send @channel | -100id | folder link")
    bot.register_next_step_handler(msg, save_channel)

def save_channel(m):
    cur.execute("INSERT INTO channels (value) VALUES (?)", (m.text,))
    db.commit()
    bot.send_message(m.chat.id, "✅ Channel added")

@bot.message_handler(func=lambda m: m.text == "📋 Channels List")
def list_channels(m):
    rows = cur.execute("SELECT id, value FROM channels").fetchall()
    if not rows:
        bot.send_message(m.chat.id, "No channels")
        return
    t = "📢 Channels:\n\n"
    for i, v in rows:
        t += f"{i}. {v}\n"
    bot.send_message(m.chat.id, t)

# ========= METHODS =========
@bot.message_handler(func=lambda m: m.text == "➕ Add Method")
def add_method(m):
    msg = bot.send_message(m.chat.id, "Send method name")
    bot.register_next_step_handler(msg, save_method)

def save_method(m):
    cur.execute("INSERT INTO methods (name) VALUES (?)", (m.text,))
    db.commit()
    bot.send_message(m.chat.id, "✅ Method added")

@bot.message_handler(func=lambda m: m.text == "📋 Methods List")
def list_methods(m):
    rows = cur.execute("SELECT id, name FROM methods").fetchall()
    if not rows:
        bot.send_message(m.chat.id, "No methods")
        return
    t = "🔥 Methods:\n\n"
    for i, n in rows:
        t += f"{i}. {n}\n"
    bot.send_message(m.chat.id, t)

# ========= POINTS =========
@bot.message_handler(func=lambda m: m.text == "➕ Add Points")
def ask_add(m):
    msg = bot.send_message(m.chat.id, "user_id points")
    bot.register_next_step_handler(msg, do_add)

def do_add(m):
    uid, pts = m.text.split()
    add_points(int(uid), int(pts))
    bot.send_message(m.chat.id, "✅ Points added")

@bot.message_handler(func=lambda m: m.text == "➖ Cut Points")
def ask_cut(m):
    msg = bot.send_message(m.chat.id, "user_id points")
    bot.register_next_step_handler(msg, do_cut)

def do_cut(m):
    uid, pts = m.text.split()
    cut_points(int(uid), int(pts))
    bot.send_message(m.chat.id, "✅ Points cut")

# ========= RUN =========
bot.infinity_polling()
