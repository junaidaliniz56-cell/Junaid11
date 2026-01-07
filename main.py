import telebot
from telebot import types
import sqlite3

TOKEN = "8380662421:AAEP9BOevEPJ5CDDwYesgbkNns4bi4bwrH0"
ADMINS = [7011937754]

METHOD_COST = 7
INVITE_REWARD = 1

FIXED_CHANNELS = [
    "jndtech1",
    "jndtech1"
]

bot = telebot.TeleBot(TOKEN)
db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

# ===== DB =====
cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, ref INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS methods(name TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS channels(username TEXT)")
db.commit()

def is_admin(uid):
    return uid in ADMINS

# ===== KEYBOARDS =====
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

# ===== START =====
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

# ===== JOIN CHECK =====
def check_join(uid):
    all_channels = FIXED_CHANNELS[:]
    cur.execute("SELECT username FROM channels")
    for (c,) in cur.fetchall():
        all_channels.append(c.replace("@", ""))

    for ch in all_channels:
        try:
            s = bot.get_chat_member("@"+ch, uid).status
            if s not in ["member","administrator","creator"]:
                return False
        except:
            return False
    return True

def send_join(cid):
    kb = types.InlineKeyboardMarkup(row_width=2)

    for ch in FIXED_CHANNELS:
        kb.add(types.InlineKeyboardButton("Join", url="https://t.me/"+ch))

    cur.execute("SELECT username FROM channels")
    for (c,) in cur.fetchall():
        kb.add(types.InlineKeyboardButton("Join", url="https://t.me/"+c.replace("@","")))

    kb.add(types.InlineKeyboardButton("✅ Joined", callback_data="joined"))
    bot.send_message(cid, "❌ Please join all channels", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data=="joined")
def joined(c):
    if check_join(c.from_user.id):
        bot.edit_message_text("✅ Verified", c.message.chat.id, c.message.message_id, reply_markup=main_kb())
    else:
        bot.answer_callback_query(c.id, "Join all channels first!")

# ===== USER =====
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
        bot.send_message(m.chat.id, "❌ No methods")
        return

    for r in rows:
        kb.add(r[0])
    kb.add("⬅ Back")
    bot.send_message(m.chat.id, "Select method:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text=="⬅ Back")
def back(m):
    bot.send_message(m.chat.id, "Menu", reply_markup=main_kb())

@bot.message_handler(func=lambda m: m.text and not m.text.startswith("/"))
def order(m):
    cur.execute("SELECT name FROM methods WHERE name=?", (m.text,))
    if not cur.fetchone():
        return

    cur.execute("UPDATE users SET points = points - ? WHERE id=?", (METHOD_COST, m.from_user.id))
    db.commit()

    for a in ADMINS:
        bot.send_message(a, f"📦 New Order\nUser: {m.from_user.id}\nMethod: {m.text}")

    bot.send_message(m.chat.id, "✅ Order sent", reply_markup=main_kb())

@bot.message_handler(func=lambda m: m.text=="🔗 Referral")
def ref(m):
    link = f"https://t.me/{bot.get_me().username}?start={m.from_user.id}"
    bot.send_message(m.chat.id, f"{link}\n🎁 1 invite = 1 point")

@bot.message_handler(func=lambda m: m.text=="👤 Account")
def acc(m):
    cur.execute("SELECT points FROM users WHERE id=?", (m.from_user.id,))
    bot.send_message(m.chat.id, f"💰 Points: {cur.fetchone()[0]}")

# ===== ADMIN =====
@bot.message_handler(commands=["admin"])
def admin(m):
    if not is_admin(m.from_user.id):
        return
    bot.send_message(m.chat.id, "🛠 Admin Panel", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text=="❌ Close")
def close(m):
    bot.send_message(m.chat.id, "Closed", reply_markup=main_kb())

# ===== METHODS =====
@bot.message_handler(func=lambda m: m.text=="➕ Add Method")
def am(m):
    bot.send_message(m.chat.id, "Send method name")
    bot.register_next_step_handler(m, lambda x: (cur.execute("INSERT INTO methods VALUES(?)",(x.text,)), db.commit(), bot.send_message(x.chat.id,"✅ Added")))

@bot.message_handler(func=lambda m: m.text=="📋 Method List")
def ml(m):
    cur.execute("SELECT name FROM methods")
    bot.send_message(m.chat.id, "\n".join([r[0] for r in cur.fetchall()]) or "Empty")

@bot.message_handler(func=lambda m: m.text=="❌ Delete Method")
def dm(m):
    bot.send_message(m.chat.id, "Send method name")
    bot.register_next_step_handler(m, lambda x: (cur.execute("DELETE FROM methods WHERE name=?",(x.text,)), db.commit(), bot.send_message(x.chat.id,"❌ Deleted")))

# ===== CHANNELS =====
@bot.message_handler(func=lambda m: m.text=="➕ Add Channel")
def ac(m):
    bot.send_message(m.chat.id, "Send @channelusername")
    bot.register_next_step_handler(m, save_ch)

def save_ch(m):
    if not m.text.startswith("@"):
        bot.send_message(m.chat.id, "❌ Only @username")
        return
    cur.execute("INSERT INTO channels VALUES(?)",(m.text,))
    db.commit()
    bot.send_message(m.chat.id, "✅ Channel added")

@bot.message_handler(func=lambda m: m.text=="📢 Channel List")
def cl(m):
    cur.execute("SELECT username FROM channels")
    bot.send_message(m.chat.id, "\n".join([r[0] for r in cur.fetchall()]) or "Empty")

@bot.message_handler(func=lambda m: m.text=="❌ Delete Channel")
def dc(m):
    bot.send_message(m.chat.id, "Send @channelusername")
    bot.register_next_step_handler(m, lambda x: (cur.execute("DELETE FROM channels WHERE username=?",(x.text,)), db.commit(), bot.send_message(x.chat.id,"❌ Deleted")))

# ===== POINTS =====
@bot.message_handler(func=lambda m: m.text=="➕ Add Points")
def ap(m):
    bot.send_message(m.chat.id, "Send: user_id points")
    bot.register_next_step_handler(m, lambda x: (cur.execute("UPDATE users SET points=points+? WHERE id=?",tuple(map(int,x.text.split()))), db.commit(), bot.send_message(x.chat.id,"✅ Added")))

@bot.message_handler(func=lambda m: m.text=="➖ Cut Points")
def cp(m):
    bot.send_message(m.chat.id, "Send: user_id points")
    bot.register_next_step_handler(m, lambda x: (cur.execute("UPDATE users SET points=points-? WHERE id=?",tuple(map(int,x.text.split()))), db.commit(), bot.send_message(x.chat.id,"➖ Cut")))

print("Bot running...")
bot.infinity_polling()
