import telebot
import json
import os
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from flask import Flask, request

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8531885088:AAHvHjHqP2U_46FsYI1tRCX29ieXqKxL9PM") 
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1662004win")
DB_FILE = "user_secure_db.json"
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL") # Render မှ ပေးမည့် Web URL
# =======================================================

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: 
                data = json.load(f)
                if "approved_users" not in data or not isinstance(data["approved_users"], dict):
                    data["approved_users"] = {}
                if "user_states" not in data or not isinstance(data["user_states"], dict):
                    data["user_states"] = {}
                if "keys_db" not in data or not isinstance(data["keys_db"], dict):
                    data["keys_db"] = {}
                if "admins" not in data or not isinstance(data["admins"], list):
                    data["admins"] = []
                return data
            except json.JSONDecodeError: 
                return get_default_db()
    return get_default_db()

def get_default_db():
    return {"approved_users": {}, "user_states": {}, "keys_db": {}, "admins": []}

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e: print(f"[-] DB Save Error: {e}")

def get_user_menu():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(KeyboardButton("📶 Wi-Fi စတင်ချိတ်ဆက်မည်"), KeyboardButton("❓ အသုံးပြုနည်း လမ်းညွှန်"))
    return markup

def get_admin_menu():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("✅ User အား ခွင့်ပြုချက်ပေးမည် (Approve)"), KeyboardButton("❌ User အား အသုံးပြုခွင့်ပိတ်မည် (Block)"),
        KeyboardButton("🔑 Key နှင့် Link အသစ်ထည့်မည်"), KeyboardButton("📋 သတ်မှတ်ထားသော Key များစာရင်း"),
        KeyboardButton("🗑️ Key နှင့် Link ပြန်ဖျက်မည်"), KeyboardButton("👤 ခွင့်ပြုထားသော User များစာရင်း"), 
        KeyboardButton("🚪 Admin Panel မှ ထွက်မည်")
    )
    return markup

def send_force_start(target_id, from_user_first_name):
    pending_text = (
        "🔒 **စနစ်ကို အသုံးပြုရန် ခွင့်ပြုချက် လိုအပ်ပါသည်**\n\n"
        f"👤 သင့်အမည်: `{from_user_first_name}`\n"
        f"🆔 သင့်ရဲ့ ID: `{target_id}`\n\n"
        "⚠️ အကြောင်းကြားစာ: Admin မှ သင့်ရဲ့ အသုံးပြုခွင့်ကို ပိတ်သိမ်းလိုက်ပါသဖြင့် စာမျက်နှာအဟောင်းများ ပျက်သွားပါပြီ။ အသုံးပြုခွင့် ပြန်လည်တောင်းခံပါ။"
    )
    bot.send_message(target_id, pending_text, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")

@bot.message_handler(commands=['start', 'help', 'admin'])
def send_welcome(message):
    chat_id = str(message.chat.id)
    db_data = load_db()
    db_data["user_states"][chat_id] = None
    save_db(db_data)

    if message.text == "/admin":
        db_data["user_states"][chat_id] = "AWAITING_ADMIN_PASSWORD"
        save_db(db_data)
        bot.send_message(chat_id, "🔐 Admin Panel သို့ ဝင်ရောက်ရန် Password ရိုက်ထည့်ပေးပါ...", reply_markup=ReplyKeyboardRemove())
        return
    
    if chat_id in db_data.get("approved_users", {}):
        bot.send_message(chat_id, f"👋 မင်္ဂလာပါ {db_data['approved_users'][chat_id]['name']} ဗျာ၊ Wi-Fi ချိတ်ဆက်ပေးမည့်စနစ်မှ ကြိုဆိုပါတယ်။", reply_markup=get_user_menu())
    else:
        pending_text = (
            "🔒 **စနစ်ကို အသုံးပြုရန် ခွင့်ပြုချက် လိုအပ်ပါသည်**\n\n"
            f"👤 သင့်အမည်: `{message.from_user.first_name}`\n"
            f"🆔 သင့်ရဲ့ ID: `{chat_id}`\n\n"
            "⚠️ အထက်ပါ **ID** နှင့် **သင့်အမည်** ကို ကူးယူ (Copy) ပြီး Admin ထံသို့ ပို့ပေးကာ အသုံးပြုခွင့် တောင်းခံလိုက်ပါဗျာ။"
        )
        bot.send_message(chat_id, pending_text, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    chat_id = str(message.chat.id)
    user_text = message.text.strip()
    db_data = load_db()
    state = db_data["user_states"].get(chat_id)
    admins_list = db_data.get("admins", [])

    if state == "AWAITING_ADMIN_PASSWORD":
        if user_text == ADMIN_PASSWORD:
            db_data["user_states"][chat_id] = "ADMIN_MAIN"
            if chat_id not in admins_list: db_data["admins"].append(chat_id)
            save_db(db_data)
            bot.send_message(chat_id, "🔓 Admin Access Granted!", reply_markup=get_admin_menu())
        else:
            db_data["user_states"][chat_id] = None
            save_db(db_data)
            bot.send_message(chat_id, "❌ Admin စကားဝှက် မှားယွင်းပါသည်။", reply_markup=ReplyKeyboardRemove())
        return

    if chat_id in admins_list:
        if user_text == "✅ User အား ခွင့်ပြုချက်ပေးမည် (Approve)":
            db_data["user_states"][chat_id] = "AWAITING_APPROVE_ID"
            save_db(db_data)
            bot.send_message(chat_id, "🔑 ယူဇာ၏ **Telegram ID** ကို ရိုက်ထည့်ပေးပါ...", reply_markup=ReplyKeyboardRemove())
            return
        elif user_text == "❌ User အား အသုံးပြုခွင့်ပိတ်မည် (Block)":
            db_data["user_states"][chat_id] = "AWAITING_BLOCK"
            save_db(db_data)
            bot.send_message(chat_id, "🚷 ပြန်ပိတ်မည့် ယူဇာ၏ **Telegram ID** ကို ရိုက်ထည့်ပေးပါ...", reply_markup=ReplyKeyboardRemove())
            return
        elif user_text == "🔑 Key နှင့် Link အသစ်ထည့်မည်":
            db_data["user_states"][chat_id] = "AWAITING_KEY_NAME"
            save_db(db_data)
            bot.send_message(chat_id, "🔑 ထည့်သွင်းလိုသော **Key (စကားဝှက်)** ကို ရိုက်ထည့်ပေးပါ...", reply_markup=ReplyKeyboardRemove())
            return
        elif user_text == "📋 သတ်မှတ်ထားသော Key များစာရင်း":
            keys_dict = db_data.get("keys_db", {})
            list_text = "📋 **လက်ရှိစနစ်ထဲရှိ Key နှင့် Links များစာရင်း** -\n\n"
            if not keys_dict: list_text += "• သတ်မှတ်ထားသော Key မရှိသေးပါ။"
            else:
                for k, l in keys_dict.items(): list_text += f"🔑 **Key:** `{k}`\n🔗 **Link:** {l}\n\n"
            bot.send_message(chat_id, list_text, reply_markup=get_admin_menu(), parse_mode="Markdown", disable_web_page_preview=True)
            return
        elif user_text == "🗑️ Key နှင့် Link ပြန်ဖျက်မည်":
            db_data["user_states"][chat_id] = "AWAITING_KEY_DELETE"
            save_db(db_data)
            bot.send_message(chat_id, "🗑️ ဖြုတ်ချလိုသော **Key (စကားဝှက်)** ကို ရိုက်ထည့်ပေးပါ...", reply_markup=ReplyKeyboardRemove())
            return
        elif user_text == "👤 ခွင့်ပြုထားသော User များစာရင်း":
            approved_dict = db_data.get("approved_users", {})
            list_text = "👤 **ခွင့်ပြုချက်ရထားသော User များစာရင်း** -\n\n"
            if not approved_dict: list_text += "• ခွင့်ပြုထားသော User မရှိသေးပါ။"
            else:
                for uid, info in approved_dict.items(): list_text += f"• **ID:** `{uid}`\n  **Name:** {info['name']}\n\n"
            bot.send_message(chat_id, list_text, reply_markup=get_admin_menu(), parse_mode="Markdown")
            return
        elif user_text == "🚪 Admin Panel မှ ထွက်မည်":
            db_data["user_states"][chat_id] = None
            if chat_id in db_data["admins"]: db_data["admins"].remove(chat_id)
            save_db(db_data)
            bot.send_message(chat_id, "🚪 Admin Panel မှ ထွက်ပြီးပါပြီ။", reply_markup=get_user_menu() if chat_id in db_data.get("approved_users", {}) else ReplyKeyboardRemove())
            return

        if state == "AWAITING_KEY_DELETE":
            if user_text in db_data.get("keys_db", {}):
                del db_data["keys_db"][user_text]
                db_data["user_states"][chat_id] = "ADMIN_MAIN"
                save_db(db_data)
                bot.send_message(chat_id, f"✅ Key: `{user_text}` ကို ဖျက်လိုက်ပါပြီ။", reply_markup=get_admin_menu(), parse_mode="Markdown")
            else: bot.send_message(chat_id, f"❌ Key: `{user_text}` ရှာမတွေ့ပါ။", reply_markup=get_admin_menu())
            return
        if state == "AWAITING_KEY_NAME":
            db_data["user_states"][chat_id] = f"AWAITING_KEY_LINK:{user_text}"
            save_db(db_data)
            bot.send_message(chat_id, f"🔗 Key: `{user_text}` အတွက် **Wi-Fi Portal Link** ထည့်ပေးပါ...", parse_mode="Markdown")
            return
        if state and state.startswith("AWAITING_KEY_LINK:"):
            target_key = state.split(":", 1)[1]
            db_data["keys_db"][target_key] = user_text
            db_data["user_states"][chat_id] = "ADMIN_MAIN"
            save_db(db_data)
            bot.send_message(chat_id, f"✅ Key: `{target_key}` အတွက် လင့်ခ်သိမ်းပြီးပါပြီ။", reply_markup=get_admin_menu(), parse_mode="Markdown")
            return
        if state == "AWAITING_APPROVE_ID":
            if user_text.isdigit():
                db_data["user_states"][chat_id] = f"AWAITING_APPROVE_NAME:{user_text}"
                save_db(db_data)
                bot.send_message(chat_id, f"👤 User ID: `{user_text}` အတွက် နာမည်ရိုက်ထည့်ပေးပါ...", parse_mode="Markdown")
            else: bot.send_message(chat_id, "❌ ID သည် ဂဏန်းသာဖြစ်ရမည်။", reply_markup=get_admin_menu())
            return
        if state and state.startswith("AWAITING_APPROVE_NAME:"):
            target_id = state.split(":", 1)[1]
            db_data["approved_users"][target_id] = {"name": user_text, "date": datetime.now().strftime("%d-%b-%Y"), "last_tab_msg_id": None}
            db_data["user_states"][chat_id] = "ADMIN_MAIN"
            save_db(db_data)
            bot.send_message(chat_id, f"✅ User ID: `{target_id}` ခွင့်ပြုလိုက်ပါပြီ။", reply_markup=get_admin_menu(), parse_mode="Markdown")
            try: bot.send_message(int(target_id), f"🎉 ခွင့်ပြုချက် ရရှိပါပြီ။", reply_markup=get_user_menu())
            except Exception: pass
            return
        if state == "AWAITING_BLOCK":
            if user_text in db_data["approved_users"]:
                last_msg_id = db_data["approved_users"][user_text].get("last_tab_msg_id")
                if last_msg_id:
                    try: bot.delete_message(int(user_text), int(last_msg_id))
                    except Exception: pass
                del db_data["approved_users"][user_text]
                db_data["user_states"][chat_id] = "ADMIN_MAIN"
                save_db(db_data)
                bot.send_message(chat_id, f"🚷 ပိတ်လိုက်ပါပြီ။", reply_markup=get_admin_menu(), parse_mode="Markdown")
                try: send_force_start(user_text, "User")
                except Exception: pass
            else: bot.send_message(chat_id, "❌ ID ရှာမတွေ့ပါ။", reply_markup=get_admin_menu())
            return

    if chat_id in db_data.get("approved_users", {}):
        if user_text == "📶 Wi-Fi စတင်ချိတ်ဆက်မည်":
            db_data["user_states"][chat_id] = "USER_INPUT_PASSWORD"
            save_db(db_data)
            bot.send_message(chat_id, "🔑 Admin ပေးထားသော Key ကို ရိုက်ထည့်ပါ...", reply_markup=ReplyKeyboardRemove())
            return
        elif user_text == "❓ အသုံးပြုနည်း လမ်းညွှန်":
            bot.send_message(chat_id, "📌 Key ရိုက်ထည့်ပြီး Wi-Fi Link ကိုနှိပ်ပါ။", reply_markup=get_user_menu())
            return

        if state == "USER_INPUT_PASSWORD":
            if user_text in db_data.get("keys_db", {}):
                wifi_link = db_data["keys_db"][user_text]
                old_msg_id = db_data["approved_users"][chat_id].get("last_tab_msg_id")
                if old_msg_id:
                    try: bot.delete_message(int(chat_id), int(old_msg_id))
                    except Exception: pass
                db_data["user_states"][chat_id] = None
                sent_msg = bot.send_message(chat_id, f"✅ [👉 Wi-Fi စတင်ရန် ဤနေရာကိုနှိပ်ပါ 👈]({wifi_link})", reply_markup=get_user_menu(), parse_mode="Markdown")
                db_data["approved_users"][chat_id]["last_tab_msg_id"] = sent_msg.message_id
                save_db(db_data)
            else: bot.send_message(chat_id, "❌ စကားဝှက် မမှန်ပါ။")
            return

# Flask Web Route for Webhook
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.stream.read().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    if RENDER_EXTERNAL_URL:
        bot.set_webhook(url=RENDER_EXTERNAL_URL + BOT_TOKEN)
        return "Webhook Set Successfully!", 200
    return "Render URL missing", 400

if __name__ == "__main__":
    # Render အတွက် Port ဖွင့်ပေးခြင်း
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
