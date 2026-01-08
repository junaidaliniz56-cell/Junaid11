import telebot, os, json
from telebot import types

BOT_TOKEN = "8546188939:AAGCchjT0fnBRmgeKVz87S1i7cIkhVOfZHI"
ADMINS = [7011937754]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

DATA_FILE = "numbers.json"
CHANNEL_FILE = "channels.json"
STATE = {}

def load(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

NUMBERS = load(DATA_FILE, {})
CHANNELS = load(CHANNEL_FILE, [])

def is_admin(uid): return uid in ADMINS
def flag(c): return "🌍"

# ================= JOIN CHECK =================
def check_join(uid):
    required_channels = ["@Junaidniz", "@jndtech1"]
    for ch in required_channels:
        try:
            m = bot.get_chat_member(ch, uid)
            if m.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    if not check_join(m.chat.id):  # چینل جوائن چیک
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(f"Join @Junaidniz", url="https://t.me/Junaidniz"))
        kb.add(types.InlineKeyboardButton(f"Join @jndtech1", url="https://t.me/jndtech1"))
        kb.add(types.InlineKeyboardButton("✅ Verify", callback_data="verify"))
        bot.send_message(m.chat.id, "❌ Join required channels", reply_markup=kb)
        return

    show_countries(m.chat.id)

@bot.callback_query_handler(func=lambda c: c.data == "verify")
def verify(c):
    if check_join(c.from_user.id):
        bot.answer_callback_query(c.id, "✅ Verified")
        show_countries(c.from_user.id)
    else:
        bot.answer_callback_query(c.id, "❌ Join all channels", show_alert=True)

# ================= USER PANEL =================
def show_countries(cid):
    if not NUMBERS:
        bot.send_message(cid, "❌ No numbers available")
        return

    kb = types.InlineKeyboardMarkup(row_width=2)
    for c in NUMBERS:
        kb.add(types.InlineKeyboardButton(
            f"{flag(c)} {c} ({len(NUMBERS[c])})",
            callback_data=f"country|{c}"
        ))
    kb.add(types.InlineKeyboardButton("🔄 Change Country", callback_data="change"))
    bot.send_message(cid, "🌍 <b>Select Country</b>", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("country|"))
def pick_country(c):
    country = c.data.split("|")[1]
    if country not in NUMBERS or len(NUMBERS[country]) == 0:
        bot.edit_message_text("❌ No numbers available for this country", c.message.chat.id, c.message.message_id)
        return

    num = NUMBERS[country].pop(0)
    save(DATA_FILE, NUMBERS)

    numbers_list = "\n".join([f"{i+1}. {num}" for i, num in enumerate(NUMBERS[country])])

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔄 Change Number", callback_data=f"country|{country}"))
    kb.add(types.InlineKeyboardButton("🌍 Change Country", callback_data="change"))

    kb.add(types.InlineKeyboardButton("📲 Code Group", callback_data="show_code_numbers"))

    bot.edit_message_text(
        f"{flag(country)} <b>Your Number ({country})</b>\n\n📞 <code>{num}</code>\n\n⏳ Waiting for OTP...\n\n{numbers_list}",
        c.message.chat.id,
        c.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data == "change")
def change_country(c):
    show_countries(c.from_user.id)

# ================= SHOW CODE GROUP =================
@bot.callback_query_handler(func=lambda c: c.data == "show_code_numbers")
def show_code_numbers(c):
    # Only show Code Group link with no numbers
    code_group_link = "https://t.me/+Aqq6X6oRWCdhM2Q0"  # Your provided Code Group link

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔄 Change Code Group", callback_data="show_code_numbers"))
    kb.add(types.InlineKeyboardButton("🌍 Change Country", callback_data="change"))

    bot.edit_message_text(
        f"📲 Code Group\n\n🔗 <a href='{code_group_link}'>Join Code Group</a>",
        c.message.chat.id,
        c.message.message_id,
        reply_markup=kb
    )

# ================= ADD NUMBERS =================
@bot.message_handler(func=lambda m: m.text == "➕ Add Numbers")
def add_numbers(m):
    STATE[m.chat.id] = "country"
    bot.send_message(m.chat.id, "🌍 Send Country Name")

@bot.message_handler(func=lambda m: STATE.get(m.chat.id) == "country")
def get_country(m):
    STATE[m.chat.id] = {"country": m.text}
    bot.send_message(m.chat.id, "📄 Send numbers.txt file")

@bot.message_handler(content_types=["document"])
def file_recv(m):
    st = STATE.get(m.chat.id)
    if not st or "country" not in st: return

    # Get the country from STATE
    country = st["country"]

    # Download the file
    file = bot.download_file(bot.get_file(m.document.file_id).file_path)

    # Decode and split by lines
    nums = file.decode().splitlines()

    # Ensure NUMBERS exists for the country
    if country not in NUMBERS:
        NUMBERS[country] = []

    # Add numbers to the NUMBERS dictionary for the specific country
    NUMBERS[country].extend(nums)

    # Save the updated NUMBERS dictionary to the file
    save(DATA_FILE, NUMBERS)

    bot.send_message(m.chat.id, f"✅ {len(nums)} numbers added to {country}")
    STATE.pop(m.chat.id)

# ================= NUMBER DELETE =================
@bot.message_handler(func=lambda m: m.text == "📋 Number List")
def list_numbers(m):
    kb = types.InlineKeyboardMarkup()
    for c in NUMBERS:
        kb.add(types.InlineKeyboardButton(
            f"{flag(c)} {c} ({len(NUMBERS[c])}) ❌",
            callback_data=f"delnum|{c}"
        ))
    bot.send_message(m.chat.id, "📋 Tap to delete country", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("delnum|"))
def del_num(c):
    ctry = c.data.split("|")[1]
    del NUMBERS[ctry]
    save(DATA_FILE, NUMBERS)
    bot.edit_message_text(f"✅ {ctry} deleted", c.message.chat.id, c.message.message_id)

@bot.message_handler(func=lambda m: m.text == "❌ Close")
def close(m):
    bot.send_message(m.chat.id, "Closed", reply_markup=types.ReplyKeyboardRemove())

print("🤖 Bot Running")
bot.infinity_polling()
