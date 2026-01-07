import telebot
import sqlite3

# ============ CONFIG ============
TOKEN = "8380662421:AAEP9BOevEPJ5CDDwYesgbkNns4bi4bwrH0"   # ⚠️ testing token
ADMINS = [7011937754]
INVITE_REWARD = 1
METHOD_COST = 7

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ============ DATABASE ============
conn = sqlite3.connect("database.db", check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0)")
c.execute("CREATE TABLE IF NOT EXISTS methods (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS channels (channel TEXT)")
conn.commit()

# ============ HELPERS ============
def is_admin(uid):
    return uid in ADMINS

def get_points(uid):
    c.execute("SELECT points FROM users WHERE user_id=?", (uid,))
    r = c.fetchone()
    return r[0] if r else 0

def check_join(uid):
    c.execute("SELECT channel FROM channels")
    for (ch,) in c.fetchall():
        try:
            m = bot.get_chat_member(ch, uid)
            if m.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ============ START ============
@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    args = msg.text.split()

    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    if not c.fetchone():
        c.execute("INSERT INTO users(user_id, points) VALUES (?,0)", (uid,))
        if len(args) > 1:
            ref = int(args[1])
            c.execute("UPDATE users SET points = points + ? WHERE user_id=?", (INVITE_REWARD, ref))
        conn.commit()

    bot.reply_to(
        msg,
        f"👋 Welcome\n\n"
        f"💰 Points: {get_points(uid)}\n"
        f"👥 Invite = +1 Point\n"
        f"🧠 Method = 7 Points\n\n"
        f"/account\n/methods"
    )

# ============ ACCOUNT ============
@bot.message_handler(commands=["account"])
def account(msg):
    uid = msg.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={uid}"
    bot.reply_to(
        msg,
        f"👤 ID: {uid}\n"
        f"💰 Points: {get_points(uid)}\n\n"
        f"🔗 Referral Link:\n{link}"
    )

# ============ METHODS ============
@bot.message_handler(commands=["methods"])
def methods(msg):
    c.execute("SELECT id,title FROM methods")
    rows = c.fetchall()
    if not rows:
        bot.reply_to(msg, "❌ No methods available")
        return

    text = "📚 Method List:\n\n"
    for i,t in rows:
        text += f"{i}. {t}\n"
    text += "\nUse: /getmethod ID"
    bot.reply_to(msg, text)

@bot.message_handler(commands=["getmethod"])
def getmethod(msg):
    uid = msg.from_user.id
    args = msg.text.split()

    if not check_join(uid):
        bot.reply_to(msg, "❗ Join required channels first")
        return

    if get_points(uid) < METHOD_COST:
        bot.reply_to(msg, "❌ Not enough points")
        return

    if len(args) < 2:
        bot.reply_to(msg, "Use: /getmethod ID")
        return

    mid = int(args[1])
    c.execute("SELECT content FROM methods WHERE id=?", (mid,))
    r = c.fetchone()
    if not r:
        bot.reply_to(msg, "❌ Method not found")
        return

    c.execute("UPDATE users SET points = points - ? WHERE user_id=?", (METHOD_COST, uid))
    conn.commit()
    bot.reply_to(msg, f"✅ Method Unlocked:\n\n{r[0]}")

# ============ ADMIN ============
@bot.message_handler(commands=["addmethod"])
def addmethod(msg):
    if not is_admin(msg.from_user.id):
        return
    data = msg.text.split("|",2)
    if len(data) < 3:
        bot.reply_to(msg, "Use:\n/addmethod | Title | Content")
        return
    c.execute("INSERT INTO methods(title,content) VALUES (?,?)",(data[1],data[2]))
    conn.commit()
    bot.reply_to(msg, "✅ Method Added")

@bot.message_handler(commands=["addchannel"])
def addchannel(msg):
    if not is_admin(msg.from_user.id):
        return
    c.execute("INSERT INTO channels VALUES (?)",(msg.text.split()[1],))
    conn.commit()
    bot.reply_to(msg, "✅ Channel Added")

@bot.message_handler(commands=["addpoints"])
def addpoints(msg):
    if not is_admin(msg.from_user.id):
        return
    _,uid,pts = msg.text.split()
    c.execute("UPDATE users SET points = points + ? WHERE user_id=?",(int(pts),int(uid)))
    conn.commit()
    bot.reply_to(msg, "✅ Points Added")

@bot.message_handler(commands=["cutpoints"])
def cutpoints(msg):
    if not is_admin(msg.from_user.id):
        return
    _,uid,pts = msg.text.split()
    c.execute("UPDATE users SET points = points - ? WHERE user_id=?",(int(pts),int(uid)))
    conn.commit()
    bot.reply_to(msg, "✅ Points Cut")

# ============ BROADCAST ============
@bot.message_handler(commands=["broadcast"])
def broadcast(msg):
    if not is_admin(msg.from_user.id):
        return
    text = msg.text.replace("/broadcast","")
    c.execute("SELECT user_id FROM users")
    for (u,) in c.fetchall():
        try:
            bot.send_message(u, text)
        except:
            pass
    bot.reply_to(msg, "✅ Broadcast Sent")

@bot.message_handler(commands=["fwd"])
def fwd(msg):
    if not is_admin(msg.from_user.id):
        return
    c.execute("SELECT user_id FROM users")
    for (u,) in c.fetchall():
        try:
            bot.forward_message(u, msg.chat.id, msg.message_id)
        except:
            pass

# ============ RUN ============
print("🤖 TeleBot is running...")
bot.infinity_polling()
