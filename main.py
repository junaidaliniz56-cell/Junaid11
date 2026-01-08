import telebot, os, json
from telebot import types

BOT_TOKEN = "8546188939:AAGCchjT0fnBRmgeKVz87S1i7cIkhVOfZHI"
ADMINS = [7011937754]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

DATA_FILE = "numbers.json"
CHANNEL_FILE = "channels.json"
USER_STATE = {} # State management for users/admins

def load(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

NUMBERS = load(DATA_FILE, {})
CHANNELS = load(CHANNEL_FILE, [])

def is_admin(uid): return uid in ADMINS
def flag(c): return "🌍"

# ================= JOIN CHECK =================
def check_join(uid):
    # یہاں وہ چینلز لکھیں جن کا جوائن ہونا لازمی ہے
    required_channels = ["@Junaidniz", "@jndtech1"]
    for ch in required_channels:
        try:
            m = bot.get_chat_member(ch, uid)
            if m.status in ["left", "kicked"]:
                return False
        except Exception:
            # اگر بوٹ چینل میں ایڈمن نہیں ہے تو یہ ایرر دے سکتا ہے
            return False
    return True

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    if not check_join(m.chat.id):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Join @Junaidniz", url="https://t.me/Junaidniz"))
        kb.add(types.InlineKeyboardButton("Join @jndtech1", url="https://t.me/jndtech1"))
        kb.add(types.InlineKeyboardButton("✅ Verify", callback_data="verify"))
        bot.send_message(m.chat.id, "❌ <b>آپ نے ہمارے چینلز جوائن نہیں کیے۔</b>\nبراہ کرم پہلے جوائن کریں اور پھر Verify پر کلک کریں۔", reply_markup=kb)
        return

    show_countries(m.chat.id)

@bot.callback_query_handler(func=lambda c: c.data == "verify")
def verify(c):
    if check_join(c.from_user.id):
        bot.delete_message(c.message.chat.id, c.message.message_id)
        show_countries(c.from_user.id)
    else:
        bot.answer_callback_query(c.id, "❌ ابھی تک آپ نے چینلز جوائن نہیں کیے۔", show_alert=True)

# ================= USER PANEL =================
def show_countries(cid):
    if not NUMBERS or all(len(v) == 0 for v in NUMBERS.values()):
        bot.send_message(cid, "❌ اس وقت کوئی نمبر دستیاب نہیں ہے۔")
        return

    kb = types.InlineKeyboardMarkup(row_width=2)
    for c in NUMBERS:
        if len(NUMBERS[c]) > 0:
            kb.add(types.InlineKeyboardButton(
                f"{flag(c)} {c} ({len(NUMBERS[c])})",
                callback_data=f"country|{c}"
            ))
    
    kb.add(types.InlineKeyboardButton("📢 OTP Group", url="https://t.me/+Aqq6X6oRWCdhM2Q0"))
    bot.send_message(cid, "🌍 <b>ملک کا انتخاب کریں:</b>", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("country|"))
def pick_country(c):
    country = c.data.split("|")[1]
    
    if country in NUMBERS and len(NUMBERS[country]) > 0:
        num = NUMBERS[country].pop(0)
        save(DATA_FILE, NUMBERS)

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔄 Change Number", callback_data=f"country|{country}"))
        kb.add(types.InlineKeyboardButton("🌍 Change Country", callback_data="change"))

        bot.edit_message_text(
            f"{flag(country)} <b>آپ کا نمبر ({country})</b>\n\n📞 <code>{num}</code>\n\n⏳ OTP کا انتظار کریں...",
            c.message.chat.id,
            c.message.message_id,
            reply_markup=kb
        )
    else:
        bot.answer_callback_query(c.id, "❌ اس ملک کے نمبر ختم ہو گئے ہیں۔", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "change")
def change_country(c):
    show_countries(c.message.chat.id)

# ================= ADMIN PANEL =================
@bot.message_handler(commands=["admin"])
def admin(m):
    if not is_admin(m.chat.id): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Numbers", "📋 Number List")
    kb.add("❌ Close")
    bot.send_message(m.chat.id, "🛠 <b>ایڈمن پینل میں خوش آمدید</b>", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "➕ Add Numbers")
def start_add_numbers(m):
    if not is_admin(m.chat.id): return
    USER_STATE[m.chat.id] = "waiting_country"
    bot.send_message(m.chat.id, "🌍 ملک کا نام لکھیں (مثلاً: USA, India):")

@bot.message_handler(func=lambda m: USER_STATE.get(m.chat.id) == "waiting_country")
def get_country_name(m):
    USER_STATE[m.chat.id] = {"target_country": m.text}
    bot.send_message(m.chat.id, f"📄 اب {m.text} کے لیے <code>.txt</code> فائل بھیجیں جس میں نمبرز ہوں۔")

@bot.message_handler(content_types=["document"], func=lambda m: isinstance(USER_STATE.get(m.chat.id), dict))
def process_file(m):
    state = USER_STATE.get(m.chat.id)
    country = state["target_country"]
    
    file_info = bot.get_file(m.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    try:
        content = downloaded_file.decode("utf-8")
        nums = [n.strip() for n in content.splitlines() if n.strip()]
        
        if country not in NUMBERS:
            NUMBERS[country] = []
        
        NUMBERS[country].extend(nums)
        save(DATA_FILE, NUMBERS)
        
        bot.send_message(m.chat.id, f"✅ {len(nums)} نمبرز کامیابی سے {country} میں شامل کر دیے گئے۔")
        del USER_STATE[m.chat.id]
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ فائل پڑھنے میں غلطی ہوئی: {e}")

@bot.message_handler(func=lambda m: m.text == "📋 Number List")
def list_numbers(m):
    if not is_admin(m.chat.id): return
    if not NUMBERS:
        bot.send_message(m.chat.id, "فہرست خالی ہے۔")
        return
    
    kb = types.InlineKeyboardMarkup()
    for c in NUMBERS:
        kb.add(types.InlineKeyboardButton(f"❌ Delete {c} ({len(NUMBERS[c])})", callback_data=f"delnum|{c}"))
    bot.send_message(m.chat.id, "نمبرز ڈیلیٹ کرنے کے لیے ملک پر کلک کریں:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("delnum|"))
def delete_country_numbers(c):
    ctry = c.data.split("|")[1]
    if ctry in NUMBERS:
        del NUMBERS[ctry]
        save(DATA_FILE, NUMBERS)
        bot.answer_callback_query(c.id, f"{ctry} کے نمبرز ڈیلیٹ کر دیے گئے۔")
        bot.edit_message_text("✅ ڈیلیٹ ہو گیا", c.message.chat.id, c.message.message_id)

@bot.message_handler(func=lambda m: m.text == "❌ Close")
def close_panel(m):
    bot.send_message(m.chat.id, "پینل بند کر دیا گیا۔", reply_markup=types.ReplyKeyboardRemove())

print("🤖 Bot is running...")
bot.infinity_polling()
        
