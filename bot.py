import telebot
import json
import os
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from flask import Flask
from threading import Thread

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8706727466:AAF7vjFcnf-6vlLj0cqrt6ogyio9-9AFZR8"
ADMIN_PASSWORD = "1662004win"

# Render Persistent Disk အတွက် လမ်းကြောင်းသတ်မှတ်ခြင်း
# Render ပေါ်မှာဆိုရင် /data/ အောက်မှာသိမ်းမယ်၊ ကိုယ့်စက်ထဲမှာဆိုရင် လက်ရှိ folder ထဲမှာသိမ်းမယ်
if os.path.exists("/data"):
    DB_FILE = "/data/user_secure_db.json"
else:
    DB_FILE = "user_secure_db.json"
# =======================================================

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# Render Port Error မတက်စေရန် ရိုးရှင်းသော Web Route တစ်ခုပြုလုပ်ခြင်း
@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_web_server():
    # Render သည် ပုံမှန်အားဖြင့် PORT ဆိုသော environment variable ကို ပေးတတ်သည်
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: 
                data = json.load(f)
                if "approved_users" not in data or not isinstance(data["approved_users"], dict):
                    data["approved_users"] = {}
                if "user_states" not in data:
                    data["user_states"] = {}
                if "keys_db" not in data:
                    data["keys_db"] = {}
                return data
            except json.JSONDecodeError: 
                return get_default_db()
    return get_default_db()

def get_default_db():
    return {
        "approved_users": {},  
        "user_states": {},  
        "keys_db": {} 
    }

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[-] DB Save Error: {e}")

def get_user_menu():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_connect = KeyboardButton("📶 Wi-Fi စတင်ချိတ်ဆက်မည်")
    btn_help = KeyboardButton("❓ အသုံးပြုနည်း လမ်းညွှန်")
    markup.add(btn_connect, btn_help)
    return markup

def get_admin_menu():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_approve = KeyboardButton("✅ User အား ခွင့်ပြုချက်ပေးမည် (Approve)")
    btn_block = KeyboardButton("❌ User အား အသုံးပြုခွင့်ပိတ်မည် (Block)")
    btn_add_key = KeyboardButton("🔑 Key နှင့် Link အသစ်ထည့်မည်")
    btn_view_keys = KeyboardButton("📋 သတ်မှတ်ထားသော Key များစာရင်း")
    btn_del_key = KeyboardButton("🗑️ Key နှင့် Link ပြန်ဖျက်မည်")
    btn_list = KeyboardButton("👤 ခွင့်ပြုထားသော User များစာရင်း")
    btn_exit = KeyboardButton("🚪 Admin Panel မှ ထွက်မည်")
    markup.add(btn_approve, btn_block, btn_add_key, btn_view_keys, btn_del_key, btn_list, btn_exit)
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
        welcome_text = f"👋 မင်္ဂလာပါ {db_data['approved_users'][chat_id]['name']} ဗျာ၊ Wi-Fi ချိတ်ဆက်ပေးမည့်စနစ်မှ ကြိုဆိုပါတယ်။"
        bot.send_message(chat_id, welcome_text, reply_markup=get_user_menu())
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

    if state == "AWAITING_ADMIN_PASSWORD":
        if user_text == ADMIN_PASSWORD:
            db_data["user_states"][chat_id] = "ADMIN_MAIN"
            save_db(db_data)
            bot.send_message(chat_id, "🔓 Admin Access Granted! မင်္ဂလာပါ အိုင်တီမန်နေဂျာ။", reply_markup=get_admin_menu())
        else:
            db_data["user_states"][chat_id] = None
            save_db(db_data)
            bot.send_message(chat_id, "❌ Admin စကားဝှက် မှားယွင်းပါသည်။", reply_markup=ReplyKeyboardRemove())
        return

    admin_buttons = [
        "✅ User အား ခွင့်ပြုချက်ပေးမည် (Approve)", 
        "❌ User အား အသုံးပြုခွင့်ပိတ်မည် (Block)", 
        "🔑 Key နှင့် Link အသစ်ထည့်မည်", 
        "📋 သတ်မှတ်ထားသော Key များစာရင်း",
        "🗑️ Key နှင့် Link ပြန်ဖျက်မည်",
        "👤 ခွင့်ပြုထားသော User များစာရင်း", 
        "🚪 Admin Panel မှ ထွက်မည်"
    ]
    
    if state == "ADMIN_MAIN" or user_text in admin_buttons or (state and state.startswith("AWAITING_")):
        
        if user_text == "✅ User အား ခွင့်ပြုချက်ပေးမည် (Approve)":
            db_data["user_states"][chat_id] = "AWAITING_APPROVE_ID"
            save_db(db_data)
            bot.send_message(chat_id, "🔑 အသုံးပြုခွင့်ပေးမည့် ယူဇာ၏ **Telegram ID** ကို အရင်ရိုက်ထည့်ပေးပါ...", reply_markup=ReplyKeyboardRemove())
            return

        elif user_text == "❌ User အား အသုံးပြုခွင့်ပိတ်မည် (Block)":
            db_data["user_states"][chat_id] = "AWAITING_BLOCK"
            save_db(db_data)
            bot.send_message(chat_id, "🚷 အသုံးပြုခွင့် ပြန်ပိတ်မည့် ယူဇာ၏ **Telegram ID** ကို ရိုက်ထည့်ပေးပါ...", reply_markup=ReplyKeyboardRemove())
            return

        elif user_text == "🔑 Key နှင့် Link အသစ်ထည့်မည်":
            db_data["user_states"][chat_id] = "AWAITING_KEY_NAME"
            save_db(db_data)
            bot.send_message(chat_id, "🔑 ထည့်သွင်းလိုသော **Key (စကားဝှက်)** ကို ရိုက်ထည့်ပေးပါ... (ဥပမာ - `12576438`)", reply_markup=ReplyKeyboardRemove())
            return

        elif user_text == "📋 သတ်မှတ်ထားသော Key များစာရင်း":
            keys_dict = db_data.get("keys_db", {})
            list_text = "📋 **လက်ရှိစနစ်ထဲရှိ Key နှင့် Links များစာရင်း** -\n\n"
            if not keys_dict:
                list_text += "• သတ်မှတ်ထားသော Key မရှိသေးပါ။"
            else:
                for k, l in keys_dict.items():
                    list_text += f"🔑 **Key:** `{k}`\n🔗 **Link:** {l}\n\n"
            bot.send_message(chat_id, list_text, reply_markup=get_admin_menu(), parse_mode="Markdown", disable_web_page_preview=True)
            return

        elif user_text == "🗑️ Key နှင့် Link ပြန်ဖျက်မည်":
            db_data["user_states"][chat_id] = "AWAITING_KEY_DELETE"
            save_db(db_data)
            bot.send_message(chat_id, "🗑️ စနစ်ထဲမှ ပြန်လည်ဖြုတ်ချလိုသော **Key (စကားဝှက်)** ကို ရိုက်ထည့်ပေးပါ...", reply_markup=ReplyKeyboardRemove())
            return

        elif user_text == "👤 ခွင့်ပြုထားသော User များစာရင်း":
            approved_dict = db_data.get("approved_users", {})
            list_text = "👤 **ခွင့်ပြုချက်ရထားသော User များစာရင်း** -\n\n"
            if not approved_dict:
                list_text += "• ခွင့်ပြုထားသော User မရှိသေးပါ။"
            else:
                for uid, info in approved_dict.items():
                    list_text += f"• **ID:** `{uid}`\n  **Name:** {info['name']}\n  **Date:** _{info['date']}_\n\n"
            bot.send_message(chat_id, list_text, reply_markup=get_admin_menu(), parse_mode="Markdown")
            return

        elif user_text == "🚪 Admin Panel မှ ထွက်မည်":
            db_data["user_states"][chat_id] = None
            save_db(db_data)
            if chat_id in db_data.get("approved_users", {}):
                bot.send_message(chat_id, "🚪 Admin Panel မှ ထွက်ပြီးပါပြီ။", reply_markup=get_user_menu())
            else:
                bot.send_message(chat_id, "🚪 Admin Panel မှ ထွက်ပြီးပါပြီ။", reply_markup=ReplyKeyboardRemove())
            return

        if state == "AWAITING_KEY_DELETE":
            keys_dict = db_data.get("keys_db", {})
            if user_text in keys_dict:
                del db_data["keys_db"][user_text]
                db_data["user_states"][chat_id] = "ADMIN_MAIN"
                save_db(db_data)
                bot.send_message(chat_id, f"✅ Key: `{user_text}` နှင့် Link အား အပြီးဖျက်လိုက်ပါပြီ။", reply_markup=get_admin_menu(), parse_mode="Markdown")
            else:
                bot.send_message(chat_id, f"❌ Key: `{user_text}` အား စနစ်ထဲတွင် ရှာမတွေ့ပါ။", reply_markup=get_admin_menu())
            return

        if state == "AWAITING_KEY_NAME":
            db_data["user_states"][chat_id] = f"AWAITING_KEY_LINK:{user_text}"
            save_db(db_data)
            bot.send_message(chat_id, f"🔗 Key: `{user_text}` အတွက် ချိတ်ဆက်ပေးမည့် **Wi-Fi Portal Link** ကို ဆက်လက်ထည့်သွင်းပေးပါ...", parse_mode="Markdown")
            return

        if state and state.startswith("AWAITING_KEY_LINK:"):
            target_key = state.split(":")[1]
            wifi_url = user_text
            db_data["keys_db"][target_key] = wifi_url
            db_data["user_states"][chat_id] = "ADMIN_MAIN"
            save_db(db_data)
            bot.send_message(chat_id, f"✅ Key: `{target_key}` အတွက် Wi-Fi Link ကို အောင်မြင်စွာ ထည့်သွင်းသိမ်းဆည်းပြီးပါပြီ။", reply_markup=get_admin_menu(), parse_mode="Markdown")
            return

        if state == "AWAITING_APPROVE_ID":
            if user_text.isdigit():
                db_data["user_states"][chat_id] = f"AWAITING_APPROVE_NAME:{user_text}"
                save_db(db_data)
                bot.send_message(chat_id, f"👤 User ID: `{user_text}` အတွက် **'နာမည် (Name)'** ကို ရိုက်ထည့်ပေးပါ...", parse_mode="Markdown")
            else:
                bot.send_message(chat_id, "❌ ID သည် ဂဏန်းများသာ ဖြစ်ရပါမည်။", reply_markup=get_admin_menu())
            return

        if state and state.startswith("AWAITING_APPROVE_NAME:"):
            target_id = state.split(":")[1]
            user_name = user_text
            current_time = datetime.now().strftime("%d-%b-%Y %I:%M:%S %p")
            db_data["approved_users"][target_id] = {"name": user_name, "date": current_time, "last_tab_msg_id": None}
            db_data["user_states"][chat_id] = "ADMIN_MAIN"
            save_db(db_data)
            bot.send_message(chat_id, f"✅ User ID: `{target_id}` ({user_name}) အား ခွင့်ပြုချက်ပေးလိုက်ပါပြီ။", reply_markup=get_admin_menu(), parse_mode="Markdown")
            try: 
                bot.send_message(int(target_id), f"🎉 မင်္ဂလာပါ {user_name}၊ စနစ်အသုံးပြုခွင့် ရရှိပါပြီ။", reply_markup=get_user_menu())
            except Exception: 
                pass
            return

        if state == "AWAITING_BLOCK":
            if user_text.isdigit():
                target_id = user_text
                if target_id in db_data["approved_users"]:
                    user_info = db_data["approved_users"][target_id]
                    user_name = user_info.get("name", "User")
                    last_msg_id = user_info.get("last_tab_msg_id")
                    
                    if last_msg_id:
                        try: bot.delete_message(int(target_id), int(last_msg_id))
                        except Exception: pass
                    
                    if target_id in db_data["user_states"]:
                        db_data["user_states"][target_id] = None
                        
                    del db_data["approved_users"][target_id]
                    db_data["user_states"][chat_id] = "ADMIN_MAIN"
                    save_db(db_data)
                    
                    bot.send_message(chat_id, f"🚷 User ID: `{target_id}` အသုံးပြုခွင့်ကို ပိတ်ပြီး Tab စာသားများကို ဖျက်ဆီးလိုက်ပါပြီ။", reply_markup=get_admin_menu(), parse_mode="Markdown")
                    
                    try: send_force_start(target_id, user_name)
                    except Exception: pass
                else:
                    bot.send_message(chat_id, "❌ အဆိုပါ ID မှာ Approved List ထဲတွင် မရှိပါ။", reply_markup=get_admin_menu())
            return

    # ==================== APPROVED USER ROLE HANDLING ====================
    if chat_id in db_data.get("approved_users", {}):
        if user_text == "📶 Wi-Fi စတင်ချိတ်ဆက်မည်":
            db_data["user_states"][chat_id] = "USER_INPUT_PASSWORD"
            save_db(db_data)
            bot.send_message(chat_id, "🔑 ကျေးဇူးပြု၍ Wi-Fi အသက်သွင်းရန်အတွက် Admin ပေးထားသော 'Key (စကားဝှက်)' ကို ရိုက်ထည့်ပေးပါ...", reply_markup=ReplyKeyboardRemove())
            return
            
        elif user_text == "❓ အသုံးပြုနည်း လမ်းညွှန်":
            help_text = (
                "📌 **စနစ်အသုံးပြုနည်းလမ်းညွှန်** -\n\n"
                "၁။ မိမိဖုန်းကို သတ်မှတ်ထားသော Wi-Fi Network နှင့် ချိတ်ဆက်ပါ။\n"
                "၂။ '📶 Wi-Fi စတင်ချိတ်ဆက်မည်' ကိုနှိပ်ပြီး မိမိရရှိထားသော Key စကားဝှက်ကို ရိုက်ထည့်ပါ။\n"
                "၃။ စကားဝှက်မှန်ပါက ထွက်လာမည့် [👉 Wi-Fi စတင်ရန် ဤနေရာကိုနှိပ်ပါ 👈] Tab စာသားလေးကို နှိပ်လိုက်လျှင် ဖုန်း၌ အင်တာနက်မရှိသော်လည်း Wi-Fi ပွင့်သွားပါလိမ့်မည်။"
            )
            bot.send_message(chat_id, help_text, reply_markup=get_user_menu())
            return

        if state == "USER_INPUT_PASSWORD":
            keys_dict = db_data.get("keys_db", {})
            if user_text in keys_dict:
                wifi_link = keys_dict[user_text]
                
                old_msg_id = db_data["approved_users"][chat_id].get("last_tab_msg_id")
                if old_msg_id:
                    try: bot.delete_message(int(chat_id), int(old_msg_id))
                    except Exception: pass

                db_data["user_states"][chat_id] = None
                
                success_text = (
                    "✅ **စကားဝှက် မှန်ကန်ပါသည်။**\n\n"
                    f"[👉 Wi-Fi စတင်ရန် ဤနေရာကိုနှိပ်ပါ 👈]({wifi_link})"
                )
                sent_msg = bot.send_message(chat_id, success_text, reply_markup=get_user_menu(), parse_mode="Markdown")
                db_data["approved_users"][chat_id]["last_tab_msg_id"] = sent_msg.message_id
                save_db(db_data)
            else:
                bot.send_message(chat_id, "❌ စကားဝှက် (Key) မမှန်ကန်ပါ။ ကျေးဇူးပြု၍ ပြန်လည်ရိုက်ထည့်ပါ...")
            return
    else:
        pending_text = (
            "🔒 **စနစ်ကို အသုံးပြုရန် ခွင့်ပြုချက် လိုအပ်ပါသည်**\n\n"
            f"👤 သင့်အမည်: `{message.from_user.first_name}`\n"
            f"🆔 သင့်ရဲ့ ID: `{chat_id}`\n\n"
            "⚠️ အထက်ပါ **ID** နှင့် **သင့်အမည်** ကို ကူးယူ (Copy) ပြီး Admin ထံသို့ ပို့ပေးကာ အသုံးပြုခွင့် တောင်းခံလိုက်ပါဗျာ။"
        )
        bot.send_message(chat_id, pending_text, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")

if __name__ == "__main__":
    # Web Server ကို Background Thread အနေဖြင့် စတင်ခြင်း (Port Error ကာကွယ်ရန်)
    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()
    
    print("[+] Double Secure Control Bot စတင်လည်ပတ်နေပါပြီ...")
    bot.infinity_polling()
