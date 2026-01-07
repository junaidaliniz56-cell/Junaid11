import telebot
from telebot import types
import sqlite3
import re

# ================= CONFIG =================
TOKEN = "8380662421:AAEP9BOevEPJ5CDDwYesgbkNns4bi4bwrH0"
ADMINS = [7011937754]

INVITE_REWARD = 1
METHOD_COST = 7

bot = telebot.TeleBot(TOKEN)

# ================= DATABASE =================
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, points INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS methods (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS channels (username TEXT UNIQUE)")
db.commit()

admin_state = {}

# ================= HELPERS =================
def is_admin(uid):
    return uid in ADMINS

def get_points(uid):
    cur.execute("SELECT points FROM users WHERE id=?", (uid,))
    r = cur.fetchone()
    return r[0] if r else 0

def get_channels():
    cur.execute("SELECT username FROM channels")
    return [c[0] for c in cur.fetchall()]

def user_joined_all(uid):
    channels = get_channels()
    if not channels:
        return True
    for ch in channels:
        try:
            m = bot.get_chat_member(ch, uid)
            if m.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ================= KEYBOARDS =================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🧠 Get Method")
    kb.add("🔗 Referral", "👤 Account")
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Method", "➕ Add Channel")
    kb.add("📂 Methods", "📢 Channels")
    kb.add("❌ Close")
    return kb

def join_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    for ch in get_channels():
        kb.add(
            types.InlineKeyboardButton(
                "🔗 Join",
                url=f"https://t.me/{ch.replace('@','')}"
            )
        )
    kb.add(types.InlineKeyboardButton("✅ Joined", callback_data="check_join"))
    return kb

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    args = m.text.split()

    cur.execute("SELECT * FROM users WHERE id=?", (uid,))
    if not cur.fetchone():
        cur.execute("INSERT INTO users VALUES (?,0)", (uid,))
        if len(args) > 1:
            try:
                ref = int(args[1])
                cur.execute(
                    "UPDATE users SET points = points + ? WHERE id=?",
                    (INVITE_REWARD, ref)
                )
            except:
                pass
        db.commit()

    if not user_joined_all(uid):
        bot.send_message(
            m.chat.id,
            "🚨 Please join all the required channels before using the bot!",
            reply_markup=join_keyboard()
        )
        return

    bot.send_message(
        m.chat.id,
        "✅ You are verified!\nWelcome 🎉",
        reply_markup=main_menu()
    )

# ================= JOIN CHECK =================
@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(c):
    if user_joined_all(c.from_user.id):
        bot.edit_message_text(
            "✅ Verified successfully!\nNow you can use the bot 🎉",
            c.message.chat.id,
            c.message.message_id
        )
        bot.send_message(c.message.chat.id, "Main Menu", reply_markup=main_menu())
    else:
        bot.answer_callback_query(c.id, "❌ Join all channels first!", show_alert=True)

# ================= ACCOUNT =================
@bot.message_handler(func=lambda m: m.text == "👤 Account")
def account(m):
    uid = m.from_user.id
    if not user_joined_all(uid):
        bot.send_message(m.chat.id, "Join channels first!", reply_markup=join_keyboard())
        return

    link = f"https://t.me/{bot.get_me().username}?start={uid}"
    bot.send_message(
        m.chat.id,
        f"🆔 ID: {uid}\n💰 Points: {get_points(uid)}\n\n🔗 {link}"
    )

# ================= REFERRAL =================
@bot.message_handler(func=lambda m: m.text == "🔗 Referral")
def referral(m):
    uid = m.from_user.id
    if not user_joined_all(uid):
        bot.send_message(m.chat.id, "Join channels first!", reply_markup=join_keyboard())
        return

    link = f"https://t.me/{bot.get_me().username}?start={uid}"
    bot.send_message(
        m.chat.id,
        f"🎁 Invite users & earn +{INVITE_REWARD} point\n\n{link}"
    )

# ================= GET METHOD =================
@bot.message_handler(func=lambda m: m.text == "🧠 Get Method")
def get_method(m):
    uid = m.from_user.id

    if not user_joined_all(uid):
        bot.send_message(m.chat.id, "Join channels first!", reply_markup=join_keyboard())
        return

    if get_points(uid) < METHOD_COST:
        bot.send_message(m.chat.id, "❌ Not enough points")
        return

    cur.execute("SELECT id,title FROM methods")
    rows = cur.fetchall()
    if not rows:
        bot.send_message(m.chat.id, "❌ No methods available")
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i, t in rows:
        kb.add(f"{i}. {t}")
    kb.add("🔙 Back")

    bot.send_message(
        m.chat.id,
        f"Select method (Cost: {METHOD_COST} points)",
        reply_markup=kb
    )

# ================= OPEN METHOD =================
@bot.message_handler(func=lambda m: m.text and m.text.split(".")[0].isdigit())
def open_method(m):
    uid = m.from_user.id
    mid = int(m.text.split(".")[0])

    cur.execute("SELECT content FROM methods WHERE id=?", (mid,))
    r = cur.fetchone()
    if not r:
        return

    cur.execute(
        "UPDATE users SET points = points - ? WHERE id=?",
        (METHOD_COST, uid)
    )
    db.commit()

    bot.send_message(
        m.chat.id,
        f"✅ Method Unlocked:\n\n{r[0]}",
        reply_markup=main_menu()
    )

# ================= ADMIN =================
@bot.message_handler(commands=["admin"])
def admin(m):
    if not is_admin(m.from_user.id):
        return
    bot.send_message(m.chat.id, "🛠 Admin Panel", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text in ["➕ Add Method", "➕ Add Channel"])
def admin_buttons(m):
    if not is_admin(m.from_user.id):
        return
    admin_state[m.from_user.id] = m.text

    if m.text == "➕ Add Method":
        bot.send_message(m.chat.id, "Send:\nTitle | Full Method Text")

    if m.text == "➕ Add Channel":
        bot.send_message(m.chat.id, "Send only @channelname or https://t.me/channel")

@bot.message_handler(func=lambda m: m.from_user.id in admin_state)
def admin_input(m):
    uid = m.from_user.id
    action = admin_state.pop(uid)

    if action == "➕ Add Method":
        try:
            t, c = m.text.split("|", 1)
            cur.execute(
                "INSERT INTO methods(title,content) VALUES (?,?)",
                (t.strip(), c.strip())
            )
            db.commit()
            bot.send_message(uid, "✅ Method Added", reply_markup=admin_menu())
        except:
            bot.send_message(uid, "❌ Format error")

    if action == "➕ Add Channel":
        txt = m.text.strip()
        if re.match(r"^@[A-Za-z0-9_]{5,32}$", txt):
            ch = txt
        elif re.match(r"^https://t\.me/[A-Za-z0-9_]{5,32}$", txt):
            ch = "@" + txt.split("/")[-1]
        else:
            bot.send_message(uid, "❌ Invalid channel")
            return

        cur.execute("INSERT OR IGNORE INTO channels VALUES (?)", (ch,))
        db.commit()
        bot.send_message(uid, f"✅ Channel Added: {ch}", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "❌ Close")
def close(m):
    bot.send_message(m.chat.id, "Closed", reply_markup=main_menu())

# ================= RUN =================
print("🤖 Bot running successfully...")
bot.infinity_polling()
