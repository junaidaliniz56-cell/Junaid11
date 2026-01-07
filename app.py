import telebot
from telebot import types
import sqlite3
import re

# ============ CONFIG ============
TOKEN = "8380662421:AAEP9BOevEPJ5CDDwYesgbkNns4bi4bwrH0"  # testing only
ADMINS = [7011937754]

INVITE_REWARD = 1
METHOD_COST = 7

bot = telebot.TeleBot(TOKEN)

# ============ DATABASE ============
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, points INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS methods (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS channels (username TEXT UNIQUE)")
db.commit()

# ============ STATE ============
admin_state = {}

# ============ KEYBOARDS ============
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🧠 Get Method")
    kb.add("🔗 Referral", "👤 Account")
    return kb

def admin_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Method", "📂 Methods")
    kb.add("➕ Add Channel", "📢 Channels")
    kb.add("❌ Close")
    return kb

# ============ HELPERS ============
def is_admin(uid):
    return uid in ADMINS

def get_points(uid):
    cur.execute("SELECT points FROM users WHERE id=?", (uid,))
    r = cur.fetchone()
    return r[0] if r else 0

def check_join(uid):
    cur.execute("SELECT username FROM channels")
    for (ch,) in cur.fetchall():
        try:
            m = bot.get_chat_member(ch, uid)
            if m.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ============ START ============
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    args = m.text.split()

    cur.execute("SELECT * FROM users WHERE id=?", (uid,))
    if not cur.fetchone():
        cur.execute("INSERT INTO users VALUES (?,0)", (uid,))
        if len(args) > 1:
            ref = int(args[1])
            cur.execute("UPDATE users SET points = points + ? WHERE id=?", (INVITE_REWARD, ref))
        db.commit()

    bot.send_message(
        m.chat.id,
        "✅ Verified!\n\nWelcome to Method Bot",
        reply_markup=main_menu()
    )

# ============ ACCOUNT ============
@bot.message_handler(func=lambda m: m.text == "👤 Account")
def account(m):
    uid = m.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={uid}"
    bot.send_message(
        m.chat.id,
        f"🆔 ID: {uid}\n"
        f"💰 Points: {get_points(uid)}\n\n"
        f"🔗 Referral Link:\n{link}"
    )

# ============ REFERRAL ============
@bot.message_handler(func=lambda m: m.text == "🔗 Referral")
def referral(m):
    uid = m.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={uid}"
    bot.send_message(
        m.chat.id,
        f"Invite friends & earn +{INVITE_REWARD} point 🎁\n\n{link}"
    )

# ============ GET METHOD ============
@bot.message_handler(func=lambda m: m.text == "🧠 Get Method")
def get_method(m):
    uid = m.from_user.id

    if not check_join(uid):
        cur.execute("SELECT username FROM channels")
        txt = "❗ Join all channels first:\n\n"
        for (c,) in cur.fetchall():
            txt += f"{c}\n"
        bot.send_message(m.chat.id, txt)
        return

    if get_points(uid) < METHOD_COST:
        bot.send_message(m.chat.id, "❌ Not enough points")
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cur.execute("SELECT id,title FROM methods")
    for i,t in cur.fetchall():
        kb.add(f"{i}. {t}")
    kb.add("🔙 Back")

    bot.send_message(
        m.chat.id,
        f"Select method (Cost: {METHOD_COST} points)",
        reply_markup=kb
    )

# ============ OPEN METHOD ============
@bot.message_handler(func=lambda m: "." in m.text)
def open_method(m):
    uid = m.from_user.id
    try:
        mid = int(m.text.split(".")[0])
    except:
        return

    cur.execute("SELECT content FROM methods WHERE id=?", (mid,))
    r = cur.fetchone()
    if not r:
        return

    cur.execute("UPDATE users SET points = points - ? WHERE id=?", (METHOD_COST, uid))
    db.commit()

    bot.send_message(
        m.chat.id,
        f"✅ Method Unlocked:\n\n{r[0]}",
        reply_markup=main_menu()
    )

# ============ BACK ============
@bot.message_handler(func=lambda m: m.text == "🔙 Back")
def back(m):
    bot.send_message(m.chat.id, "Main Menu", reply_markup=main_menu())

# ============ ADMIN PANEL ============
@bot.message_handler(commands=["admin"])
def admin(m):
    if not is_admin(m.from_user.id):
        return
    bot.send_message(m.chat.id, "🛠 Admin Panel", reply_markup=admin_keyboard())

# ============ ADMIN BUTTONS ============
@bot.message_handler(func=lambda m: m.text in ["➕ Add Method", "➕ Add Channel"])
def admin_buttons(m):
    if not is_admin(m.from_user.id):
        return

    admin_state[m.from_user.id] = m.text

    if m.text == "➕ Add Method":
        bot.send_message(m.chat.id, "Send:\nTitle | Full method text")

    elif m.text == "➕ Add Channel":
        bot.send_message(
            m.chat.id,
            "Send only:\n✔ @channelname\n✔ https://t.me/channelname"
        )

# ============ ADMIN INPUT ============
@bot.message_handler(func=lambda m: m.from_user.id in admin_state)
def admin_input(m):
    uid = m.from_user.id
    action = admin_state.pop(uid)

    if action == "➕ Add Method":
        try:
            t,c = m.text.split("|",1)
            cur.execute("INSERT INTO methods(title,content) VALUES (?,?)",(t.strip(),c.strip()))
            db.commit()
            bot.send_message(uid, "✅ Method Added", reply_markup=admin_keyboard())
        except:
            bot.send_message(uid, "❌ Wrong format", reply_markup=admin_keyboard())

    elif action == "➕ Add Channel":
        text = m.text.strip()
        if re.match(r"^@[A-Za-z0-9_]{5,32}$", text):
            ch = text
        elif re.match(r"^https://t\.me/[A-Za-z0-9_]{5,32}$", text):
            ch = "@"+text.split("/")[-1]
        else:
            bot.send_message(uid, "❌ Invalid Channel", reply_markup=admin_keyboard())
            return

        try:
            cur.execute("INSERT INTO channels(username) VALUES (?)",(ch,))
            db.commit()
            bot.send_message(uid, f"✅ Channel Added:\n{ch}", reply_markup=admin_keyboard())
        except:
            bot.send_message(uid, "⚠ Channel Exists", reply_markup=admin_keyboard())

# ============ LIST METHODS ============
@bot.message_handler(func=lambda m: m.text == "📂 Methods")
def list_methods(m):
    if not is_admin(m.from_user.id):
        return
    cur.execute("SELECT id,title FROM methods")
    txt = "📂 Methods:\n\n"
    for i,t in cur.fetchall():
        txt += f"{i}. {t}\n"
    bot.send_message(m.chat.id, txt, reply_markup=admin_keyboard())

# ============ LIST & DELETE CHANNELS ============
@bot.message_handler(func=lambda m: m.text == "📢 Channels")
def list_channels(m):
    if not is_admin(m.from_user.id):
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cur.execute("SELECT username FROM channels")
    for (c,) in cur.fetchall():
        kb.add(f"❌ Delete {c}")
    kb.add("❌ Close")
    bot.send_message(m.chat.id, "📢 Channels (tap to delete)", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text.startswith("❌ Delete "))
def delete_channel(m):
    if not is_admin(m.from_user.id):
        return
    ch = m.text.replace("❌ Delete ","")
    cur.execute("DELETE FROM channels WHERE username=?", (ch,))
    db.commit()
    bot.send_message(m.chat.id, f"🗑 Deleted {ch}", reply_markup=admin_keyboard())

# ============ CLOSE ============
@bot.message_handler(func=lambda m: m.text == "❌ Close")
def close(m):
    bot.send_message(m.chat.id, "Closed", reply_markup=main_menu())

# ============ RUN ============
print("🤖 Bot running successfully...")
bot.infinity_polling()
