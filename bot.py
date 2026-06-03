import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
import pytz
import uuid

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ChatMemberHandler, filters, ContextTypes
from flask import Flask, request, jsonify
from threading import Thread

# Configuration (အမှန်ပြင်ဆင်ထားသော နေရာ)
BOT_TOKEN = "8706727466:AAEYGFLafGWwfRMIpkWx_8GCUr1zqRBimDU"
GROUP_ID = -1003505610406
WEB_SERVER_PORT = 5000

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database setup
def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            personal_bot_link TEXT UNIQUE,
            last_free_key_date TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_invite_links (
            invite_link_id TEXT PRIMARY KEY,
            inviter_user_id INTEGER,
            invite_link_url TEXT UNIQUE,
            created_at TEXT,
            expires_at TEXT,
            is_used INTEGER DEFAULT 0,
            joined_user_id INTEGER,
            FOREIGN KEY (inviter_user_id) REFERENCES users(user_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            key_id TEXT PRIMARY KEY,
            user_id INTEGER,
            expiration_time TEXT,
            is_active INTEGER DEFAULT 1,
            invite_link_url TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # Check and add columns if they don't exist
    try:
        cursor.execute("ALTER TABLE group_invite_links ADD COLUMN joined_user_id INTEGER")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE keys ADD COLUMN invite_link_url TEXT")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

def generate_and_store_key(user_id, invite_link_url=None):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    # Deactivate any existing keys for this user
    cursor.execute("UPDATE keys SET is_active = 0 WHERE user_id = ?", (user_id,))
    
    new_key = str(uuid.uuid4())
    expiration_time = datetime.now(pytz.utc) + timedelta(hours=1)
    cursor.execute("INSERT INTO keys (key_id, user_id, expiration_time, invite_link_url) VALUES (?, ?, ?, ?)",
                   (new_key, user_id, expiration_time.isoformat(), invite_link_url))
    conn.commit()
    conn.close()
    return new_key

def is_key_valid(key_id):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, expiration_time, is_active FROM keys WHERE key_id = ?", (key_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        user_id, expiration_time_str, is_active = result
        if not is_active:
            return False
        expiration_time = datetime.fromisoformat(expiration_time_str)
        if datetime.now(pytz.utc) < expiration_time:
            return True
    return False

def get_main_menu_keyboard():
    keyboard = [
        [KeyboardButton("🚀 Bot စတင်ရန်"), KeyboardButton("🔗 Invite Link ရယူရန်")],
        [KeyboardButton("🎁 Daily Free Key"), KeyboardButton("🔑 ကျွန်ုပ်၏ Key စစ်ရန်")],
        [KeyboardButton("ℹ️ အကူအညီ")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT personal_bot_link FROM users WHERE user_id = ?", (user.id,))
    user_data = cursor.fetchone()
    
    welcome_text = (
        f"မင်္ဂလာပါ {user.mention_html()} 🙏\n\n"
        "ကျွန်ုပ်တို့၏ Bot မှ ကြိုဆိုပါတယ်။ လူဖိတ်ပြီး (သို့) နေ့စဉ် အခမဲ့ 1-Hour Key ရယူနိုင်ပါတယ်။\n"
        "အောက်က Menu ခလုတ်များကို အသုံးပြုနိုင်ပါတယ် 👇"
    )

    if not user_data:
        bot_username = (await context.bot.get_me()).username
        personal_bot_link = f"https://t.me/{bot_username}?start=invite_{user.id}"
        cursor.execute("INSERT INTO users (user_id, username, personal_bot_link) VALUES (?, ?, ?)",
                       (user.id, user.username, personal_bot_link))
        conn.commit()
    
    await update.message.reply_text(welcome_text, parse_mode='HTML', reply_markup=get_main_menu_keyboard())
    conn.close()

async def get_daily_free_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    today = datetime.now(pytz.utc).strftime("%Y-%m-%d")
    
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT last_free_key_date FROM users WHERE user_id = ?", (user.id,))
    result = cursor.fetchone()
    
    if result and result[0] == today:
        await update.message.reply_text("❌ သင်သည် ယနေ့အတွက် Free Key ရယူပြီးပါပြီ။ မနက်ဖြန်မှ ပြန်လာခဲ့ပါ။")
    else:
        new_key = generate_and_store_key(user.id)
        cursor.execute("UPDATE users SET last_free_key_date = ? WHERE user_id = ?", (today, user.id))
        conn.commit()
        await update.message.reply_text(
            f"🎁 ယနေ့အတွက် သင်၏ Daily Free Key ရပါပြီ-\n\n"
            f"<code>{new_key}</code>\n\n"
            f"⚠️ ဒီ Key က ၁ နာရီပဲ သက်တမ်းရှိပြီး တစ်ကြိမ်ပဲ သုံးလို့ရပါမယ်။",
            parse_mode='HTML'
        )
    conn.close()

async def get_invite_link_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    try:
        invite_link_object = await context.bot.create_chat_invite_link(
            chat_id=GROUP_ID,
            member_limit=1,
            expire_date=datetime.now(pytz.utc) + timedelta(minutes=10),
            name=f"Invite by {user.username or user.first_name} ({user.id})"
        )
        invite_link_url = invite_link_object.invite_link
        cursor.execute("INSERT INTO group_invite_links (invite_link_id, inviter_user_id, invite_link_url, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                       (invite_link_url, user.id, invite_link_url, datetime.now(pytz.utc).isoformat(), (datetime.now(pytz.utc) + timedelta(minutes=10)).isoformat()))
        conn.commit()
        await update.message.reply_text(
            f"🔗 သင်၏ သီးသန့် Invite Link ရပါပြီ-\n\n"
            f"<code>{invite_link_url}</code>\n\n"
            f"⚠️ ဒီ Link က ၁၀ မိနစ်ပဲ ခံပြီး ၁ ယောက်ပဲ Join လို့ရပါမယ်။\n"
            f"လူ Join တတာနဲ့ သင့်ဆီ Key ပို့ပေးပါ့မယ်။",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error creating invite link: {e}")
        await update.message.reply_text("❌ Link ထုတ်လို့မရပါ။ Bot ကို Group Admin ပေးထားလား စစ်ဆေးပေးပါ။")
    finally:
        conn.close()

async def chat_member_updated_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = update.chat_member
    if not result or result.chat.id != GROUP_ID:
        return
        
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status
    user_id = result.from_user.id
    
    # 1. Detect New Join via Invite Link
    if old_status in ["left", "kicked", "both_left"] and new_status in ["member", "administrator", "creator"]:
        invite_link = result.invite_link
        if invite_link:
            conn = sqlite3.connect("bot_data.db")
            cursor = conn.cursor()
            cursor.execute("SELECT inviter_user_id, is_used FROM group_invite_links WHERE invite_link_url = ?", (invite_link.invite_link,))
            invite_data = cursor.fetchone()
            
            if invite_data and not invite_data[1]:
                inviter_user_id = invite_data[0]
                # Associate the joined user with the invite link
                cursor.execute("UPDATE group_invite_links SET is_used = 1, joined_user_id = ? WHERE invite_link_url = ?", 
                               (result.new_chat_member.user.id, invite_link.invite_link))
                conn.commit()
                
                new_key = generate_and_store_key(inviter_user_id, invite_link.invite_link)
                try:
                    await context.bot.send_message(
                        chat_id=inviter_user_id, 
                        text=(f"🎉 လူသစ် Join လာပါပြီ။ သင့်အတွက် 1-Hour Key ရပါပြီ-\n\n<code>{new_key}</code>\n\nနှိပ်လိုက်ရင် Copy ကူးသွားပါလိမ့်မယ်။"), 
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Error sending key: {e}")
            conn.close()

    # 2. Detect Member Left - Revoke Key if the person who joined via link leaves
    elif new_status in ["left", "kicked"]:
        left_user_id = result.new_chat_member.user.id
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        
        # Find if this user joined via an invite link and who the inviter was
        cursor.execute("SELECT inviter_user_id, invite_link_url FROM group_invite_links WHERE joined_user_id = ?", (left_user_id,))
        invite_info = cursor.fetchone()
        
        if invite_info:
            inviter_user_id, invite_link_url = invite_info
            # Deactivate the key associated with this invite link
            cursor.execute("UPDATE keys SET is_active = 0 WHERE user_id = ? AND invite_link_url = ?", (inviter_user_id, invite_link_url))
            conn.commit()
            
            try:
                await context.bot.send_message(
                    chat_id=inviter_user_id,
                    text="⚠️ သင်ဖိတ်ခေါ်ထားသူသည် Group မှ ထွက်သွားသောကြောင့် ထုတ်ပေးထားသော Key ကို ပယ်ဖျက်လိုက်ပါပြီ။"
                )
            except Exception:
                pass
        conn.close()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if text == "🚀 Bot စတင်ရန်":
        await start(update, context)
    elif text == "🔗 Invite Link ရယူရန်":
        await get_invite_link_action(update, context)
    elif text == "🎁 Daily Free Key":
        await get_daily_free_key(update, context)
    elif text == "ℹ️ အကူအညီ":
        help_text = (
            "📖 **အသုံးပြုနည်း**\n\n"
            "၁။ '🔗 Invite Link ရယူရန်' ကိုနှိပ်ပြီး လူဖိတ်ပါ။\n"
            "၂။ '🎁 Daily Free Key' ကိုနှိပ်ပြီး တစ်ရက်တစ်ခါ အခမဲ့ Key ယူပါ။\n"
            "၃။ ရလာတဲ့ Key ကို Termux ထဲမှာ ထည့်သုံးပါ။\n\n"
            "⚠️ **သတိပြုရန်:** သင်ဖိတ်ခေါ်သူသည် Group မှ ထွက်သွားပါက သင့်အားထုတ်ပေးထားသော Key မှာ အလိုအလျောက် ပယ်ဖျက်ခံရပါမည်။"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    elif text == "🔑 ကျွန်ုပ်၏ Key စစ်ရန်":
        await update.message.reply_text("စစ်ဆေးလိုသော Key ကို /check_key <key> ပုံစံဖြင့် ရိုက်ပို့ပေးပါ။")

async def check_key_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 1:
        key_id = context.args[0]
        if is_key_valid(key_id):
            await update.message.reply_text(f"✅ Key <code>{key_id}</code> သည် အသုံးပြုနိုင်ပါသည်။", parse_mode='HTML')
        else:
            await update.message.reply_text(f"❌ Key <code>{key_id}</code> သည် မှားယွင်းနေသည် (သို့) သက်တမ်းကုန်နေပါသည်။", parse_mode='HTML')
    else:
        await update.message.reply_text("အသုံးပြုပုံ- /check_key <သင့်ရဲ့_key>")

app = Flask(__name__)
@app.route("/", methods=["GET"])
def health_check():
    return "Bot is alive!", 200

@app.route("/verify_key", methods=["POST"])
def verify_key_api():
    data = request.get_json()
    key_id = data.get("key")
    if is_key_valid(key_id):
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE keys SET is_active = 0 WHERE key_id = ?", (key_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Key used."}), 200
    return jsonify({"status": "error", "message": "Invalid/Expired key."}), 403

def run_flask_app():
    app.run(host="0.0.0.0", port=WEB_SERVER_PORT)

def main() -> None:
    init_db()
    Thread(target=run_flask_app, daemon=True).start()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check_key", check_key_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(ChatMemberHandler(chat_member_updated_handler, ChatMemberHandler.CHAT_MEMBER))
    application.run_polling(allowed_updates=[Update.CHAT_MEMBER, Update.MESSAGE, Update.MY_CHAT_MEMBER])

if __name__ == "__main__":
    main()
