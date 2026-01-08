import telebot
from telebot import types
import sqlite3

# ================= CONFIG =================
TOKEN = "8380662421:AAEP9BOevEPJ5CDDwYesgbkNns4bi4bwrH0"
ADMINS = [7011937754]     # your Telegram numeric ID
METHOD_COST = 7
INVITE_REWARD = 1

# Fixed force-join channels (BOT MUST BE ADMIN HERE)
FORCE_CHANNELS = [
    "@junaidniz110",
    "@jndtech1"
]
# =========================================

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

# ================= DATABASE =================
cur.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0,
    ref INTEGER
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
# ===========================================

# ================= HELPERS =================
def is_admin(uid):
    return uid in ADMINS

def get_user(uid, ref=None):
    u = cur.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not u:
        cur.execute("INSERT INTO users (id, points, ref) VALUES (?, ?, ?)", (uid, 0, ref))
        db.commit()
        if ref and ref != uid:
            cur.execute("UPDATE users SET points = points + ? WHERE id=?", (INVITE_REWARD, ref))
            db.commit()
    return cur.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

def add_points(uid, p):
    cur.execute("UPDATE users SET points = points + ? WHERE id=?", (p, uid))
    db.commit()

def cut_points(uid, p):
    cur.execute("UPDATE users SET points = points - ? WHERE id=?", (p, uid))
    db.commit()

def is_joined(uid):
    for ch in FORCE_CHANNELS:
        try:
            st = bot.get_chat_member(ch, uid).status
            if st in ["left", "kicked"]:
                return False
        except:
            return False
    return True
# ===========================================

# ================= KEYBOARDS =================
def user_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔥 Get Method")
    kb.add("👤 Account", "👥 Referral")
    return kb

def admin_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Channel", "📋 Channel List")
    kb.add("➕ Add Method", "❌ Delete Method")
    kb.add("➕ Add Points")
    kb.add("❌ Close")
    return kb
# ===========================================

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    ref = None
    if len(m.text.split()) > 1:
        ref = int(m.text.split()[1])
    get_user(m.from_user.id, ref)

    kb = types.InlineKeyboardMarkup()
    for ch in FORCE_CHANNELS:
        kb.add(types.InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}"))
    kb.add(types.InlineKeyboardButton("✅ Join Check", callback_data="join_check"))

    bot.send_message(
        m.chat.id,
        "🚫 <b>Pehlay dono channels join karo</b>",
        reply_markup=kb
    )
# ===========================================

@bot.callback_query_handler(func=lambda c: c.data == "join_check")
def join_check(c):
    if not is_joined(c.from_user.id):
        bot.answer_callback_query(c.id, "❌ Pehlay channels join karo", show_alert=True)
        return
    bot.edit_message_text("✅ <b>Join verified</b>", c.message.chat.id, c.message.message_id)
    bot.send_message(c.from_user.id, "🎉 Welcome", reply_markup=user_kb())

# ================= USER =================
@bot.message_handler(func=lambda m: m.text == "👤 Account")
def acc(m):
    u = get_user(m.from_user.id)
    bot.send_message(
        m.chat.id,
        f"👤 <b>Account</b>\n\n"
        f"🆔 ID: <code>{u[0]}</code>\n"
        f"💰 Points: <b>{u[1]}</b>"
    )

@bot.message_handler(func=lambda m: m.text == "👥 Referral")
def ref(m):
    bot.send_message(
        m.chat.id,
        f"👥 <b>Invite & Earn</b>\n\n"
        f"Invite link:\n"
        f"https://t.me/{bot.get_me().username}?start={m.from_user.id}\n\n"
        f"🎁 Per invite: {INVITE_REWARD} Point"
    )
# ===========================================

# ================= METHODS =================
@bot.message_handler(func=lambda m: m.text == "🔥 Get Method")
def methods(m):
    if not is_joined(m.from_user.id):
        bot.send_message(m.chat.id, "❌ Pehlay channels join karo")
        return

    rows = cur.execute("SELECT id, name FROM methods").fetchall()
    if not rows:
        bot.send_message(m.chat.id, "❌ No methods")
        return

    kb = types.InlineKeyboardMarkup()
    for mid, name in rows:
        kb.add(types.InlineKeyboardButton(name, callback_data=f"sel_{mid}"))

    bot.send_message(m.chat.id, "🔥 <b>Select Method</b>", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("sel_"))
def confirm(c):
    mid = int(c.data.split("_")[1])
    name = cur.execute("SELECT name FROM methods WHERE id=?", (mid,)).fetchone()[0]

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Confirm (7 Points)", callback_data=f"ord_{mid}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel")
    )

    bot.edit_message_text(
        f"🔥 <b>{name}</b>\n💰 Fee: {METHOD_COST} Points",
        c.message.chat.id,
        c.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("ord_"))
def order(c):
    uid = c.from_user.id
    mid = int(c.data.split("_")[1])
    u = get_user(uid)

    if u[1] < METHOD_COST:
        bot.answer_callback_query(c.id, "❌ Not enough points", show_alert=True)
        return

    cut_points(uid, METHOD_COST)
    name = cur.execute("SELECT name FROM methods WHERE id=?", (mid,)).fetchone()[0]

    for a in ADMINS:
        bot.send_message(
            a,
            f"📥 <b>New Order</b>\n"
            f"👤 {uid}\n"
            f"🔥 {name}\n"
            f"💰 {METHOD_COST} Points"
        )

    bot.edit_message_text("✅ <b>Order placed</b>", c.message.chat.id, c.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "cancel")
def cancel(c):
    bot.edit_message_text("❌ Cancelled", c.message.chat.id, c.message.message_id)
# ===========================================

# ================= ADMIN =================
@bot.message_handler(commands=["admin"])
def admin(m):
    if not is_admin(m.from_user.id): return
    bot.send_message(m.chat.id, "🛠 <b>Admin Panel</b>", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "➕ Add Method")
def add_method(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id, "Send method name")
    bot.register_next_step_handler(msg, save_method)

def save_method(m):
    cur.execute("INSERT INTO methods (name) VALUES (?)", (m.text,))
    db.commit()
    bot.send_message(m.chat.id, "✅ Method added")

@bot.message_handler(func=lambda m: m.text == "❌ Delete Method")
def del_method(m):
    if not is_admin(m.from_user.id): return
    rows = cur.execute("SELECT id, name FROM methods").fetchall()
    kb = types.InlineKeyboardMarkup()
    for mid, name in rows:
        kb.add(types.InlineKeyboardButton(f"❌ {name}", callback_data=f"delm_{mid}"))
    bot.send_message(m.chat.id, "Delete method:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("delm_"))
def delm(c):
    mid = int(c.data.split("_")[1])
    cur.execute("DELETE FROM methods WHERE id=?", (mid,))
    db.commit()
    bot.answer_callback_query(c.id, "Deleted")
# ===========================================

bot.infinity_polling()
