import telebot
from telebot import types
import sqlite3

# ================= CONFIG =================
TOKEN = "8380662421:AAEP9BOevEPJ5CDDwYesgbkNns4bi4bwrH0"
ADMINS = [7011937754]
METHOD_COST = 7
INVITE_REWARD = 1

FIXED_CHANNELS = [
    "https://t.me/junaidniz110",
    "https://t.me/jndtech1"
]
# ==========================================

bot = telebot.TeleBot(TOKEN)
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

# ================= DATABASE =================
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, ref INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS methods (name TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS channels (username TEXT)")
db.commit()
# ===========================================

def is_admin(uid):
    return uid in ADMINS

def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔥 Get Method")
    kb.add("🔗 Referral", "👤 Account")
    return kb

def admin_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Method", "📋 Method List")
    kb.add("❌ Delete Method")
    kb.add("➕ Add Channel", "📢 Channel List")
    kb.add("❌ Delete Channel")
    kb.add("➕ Add Points", "➖ Cut Points")
    kb.add("❌ Close")
    return kb

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    args = m.text.split()

    cur.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (uid,))
    db.commit()

    # referral
    if len(args) > 1:
        ref = int(args[1])
        if ref != uid:
            cur.execute("SELECT ref FROM users WHERE id=?", (uid,))
            if cur.fetchone()[0] is None:
                cur.execute("UPDATE users SET ref=? WHERE id=?", (ref, uid))
                cur.execute("UPDATE users SET points = points + ? WHERE id=?", (INVITE_REWARD, ref))
                db.commit()

    if not check_join(uid):
        send_join(m.chat.id)
        return

    bot.send_message(m.chat.id, "✅ Verified", reply_markup=main_kb())

# ================= JOIN CHECK =================
def check_join(uid):
    for link in FIXED_CHANNELS:
        ch = link.split("/")[-1]
        try:
            status = bot.get_chat_member("@"+ch, uid).status
            if status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

def send_join(cid):
    kb = types.InlineKeyboardMarkup(row_width=2)
    for c in FIXED_CHANNELS:
        kb.add(types.InlineKeyboardButton("Join", url=c))
    kb.add(types.InlineKeyboardButton("✅ Joined", callback_data="joined"))
    bot.send_message(cid, "❌ Please join all channels", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data=="joined")
def joined(c):
    if check_join(c.from_user.id):
        bot.edit_message_text("✅ Verified", c.message.chat.id, c.message.message_id, reply_markup=main_kb())
    else:
        bot.answer_callback_query(c.id, "Join all channels first!")

# ================= GET METHOD =================
@bot.message_handler(func=lambda m: m.text=="🔥 Get Method")
def get_method(m):
    cur.execute("SELECT points FROM users WHERE id=?", (m.from_user.id,))
    pts = cur.fetchone()[0]

    if pts < METHOD_COST:
        bot.send_message(m.chat.id, "❌ Not enough points")
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cur.execute("SELECT name FROM methods")
    rows = cur.fetchall()

    if not rows:
        bot.send_message(m.chat.id, "❌ No methods available")
        return

    for r in rows:
        kb.add(r[0])
    kb.add("⬅ Back")

    bot.send_message(m.chat.id, "Select Method:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text=="⬅ Back")
def back(m):
    bot.send_message(m.chat.id, "Menu", reply_markup=main_kb())

@bot.message_handler(func=lambda m: m.text not in ["🔥 Get Method","🔗 Referral","👤 Account"])
def order(m):
    cur.execute("SELECT name FROM methods WHERE name=?", (m.text,))
    if not cur.fetchone():
        return

    cur.execute("UPDATE users SET points = points - ? WHERE id=?", (METHOD_COST, m.from_user.id))
    db.commit()

    for a in ADMINS:
        bot.send_message(a, f"📦 New Order\nUser: {m.from_user.id}\nMethod: {m.text}")

    bot.send_message(m.chat.id, "✅ Order sent to admin", reply_markup=main_kb())

# ================= REFERRAL =================
@bot.message_handler(func=lambda m: m.text=="🔗 Referral")
def ref(m):
    link = f"https://t.me/{bot.get_me().username}?start={m.from_user.id}"
    bot.send_message(m.chat.id, f"Your link:\n{link}\n🎁 1 invite = 1 point")

# ================= ACCOUNT =================
@bot.message_handler(func=lambda m: m.text=="👤 Account")
def acc(m):
    cur.execute("SELECT points FROM users WHERE id=?", (m.from_user.id,))
    p = cur.fetchone()[0]
    bot.send_message(m.chat.id, f"👤 ID: {m.from_user.id}\n💰 Points: {p}")

# ================= ADMIN =================
@bot.message_handler(commands=["admin"])
def admin(m):
    if not is_admin(m.from_user.id):
        return
    bot.send_message(m.chat.id, "🛠 Admin Panel", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text=="❌ Close")
def close(m):
    bot.send_message(m.chat.id, "Closed", reply_markup=main_kb())

# ===== Add / Delete Method =====
@bot.message_handler(func=lambda m: m.text=="➕ Add Method")
def am(m):
    bot.send_message(m.chat.id, "Send method name")
    bot.register_next_step_handler(m, save_method)

def save_method(m):
    cur.execute("INSERT INTO methods VALUES(?)", (m.text,))
    db.commit()
    bot.send_message(m.chat.id, "✅ Method added")

@bot.message_handler(func=lambda m: m.text=="❌ Delete Method")
def dm(m):
    bot.send_message(m.chat.id, "Send method name to delete")
    bot.register_next_step_handler(m, del_method)

def del_method(m):
    cur.execute("DELETE FROM methods WHERE name=?", (m.text,))
    db.commit()
    bot.send_message(m.chat.id, "❌ Method deleted")

@bot.message_handler(func=lambda m: m.text=="📋 Method List")
def ml(m):
    cur.execute("SELECT name FROM methods")
    rows = cur.fetchall()
    text = "📋 Methods:\n" + "\n".join([r[0] for r in rows]) if rows else "Empty"
    bot.send_message(m.chat.id, text)

# ===== Channels Admin =====
@bot.message_handler(func=lambda m: m.text=="➕ Add Channel")
def ac(m):
    bot.send_message(m.chat.id, "Send channel @username")
    bot.register_next_step_handler(m, save_ch)

def save_ch(m):
    cur.execute("INSERT INTO channels VALUES(?)", (m.text,))
    db.commit()
    bot.send_message(m.chat.id, "✅ Channel added")

@bot.message_handler(func=lambda m: m.text=="📢 Channel List")
def cl(m):
    cur.execute("SELECT username FROM channels")
    rows = cur.fetchall()
    text = "📢 Channels:\n" + "\n".join([r[0] for r in rows]) if rows else "Empty"
    bot.send_message(m.chat.id, text)

@bot.message_handler(func=lambda m: m.text=="❌ Delete Channel")
def dc(m):
    bot.send_message(m.chat.id, "Send channel username to delete")
    bot.register_next_step_handler(m, del_ch)

def del_ch(m):
    cur.execute("DELETE FROM channels WHERE username=?", (m.text,))
    db.commit()
    bot.send_message(m.chat.id, "❌ Channel deleted")

# ===== Points =====
@bot.message_handler(func=lambda m: m.text=="➕ Add Points")
def ap(m):
    bot.send_message(m.chat.id, "Send: user_id points")
    bot.register_next_step_handler(m, addp)

def addp(m):
    uid, pts = map(int, m.text.split())
    cur.execute("UPDATE users SET points = points + ? WHERE id=?", (pts, uid))
    db.commit()
    bot.send_message(m.chat.id, "✅ Points added")

@bot.message_handler(func=lambda m: m.text=="➖ Cut Points")
def cp(m):
    bot.send_message(m.chat.id, "Send: user_id points")
    bot.register_next_step_handler(m, cutp)

def cutp(m):
    uid, pts = map(int, m.text.split())
    cur.execute("UPDATE users SET points = points - ? WHERE id=?", (pts, uid))
    db.commit()
    bot.send_message(m.chat.id, "➖ Points cut")

# ================= RUN =================
print("Bot running...")
bot.infinity_polling()
