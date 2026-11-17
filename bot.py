import os
import re
import base64
import requests
import telebot
from flask import Flask
from threading import Thread

# --- CONFIGURATIONS ---
TELEGRAM_BOT_TOKEN = "8901991980:AAGNk2UpHPQGjOh1hox7ZmdDSWErZ3VJqm0"
ADMIN_CHAT_ID = "8607494475"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_OWNER = "swt21200"
REPO_NAME = "bot"
FILE_PATH = "index.html"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "MLBB Top-Up Bot is running successfully!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def get_github_file(path=FILE_PATH):
    if not GITHUB_TOKEN:
        return None, None, "Render Environment Variable တွင် GITHUB_TOKEN ထည့်သွင်းထားခြင်း မရှိပါ။"
    
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None, None, f"GitHub မှ ဖိုင်ဆွဲယူ၍မရပါ (Status: {response.status_code}) - {response.text}"
    
    data = response.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return data["sha"], content, None

def push_github_file(new_content, sha, commit_message, path=FILE_PATH):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    encoded_content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
    payload = {
        "message": commit_message,
        "content": encoded_content,
        "sha": sha
    }
    response = requests.put(url, headers=headers, json=payload)
    if response.status_code in [200, 201]:
        return True, "GitHub သို့ အောင်မြင်စွာ Update တင်ပြီးပါပြီ။"
    return False, f"GitHub Update Error ({response.status_code}): {response.text}"

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    if str(message.chat.id) != ADMIN_CHAT_ID:
        bot.reply_to(message, "👋 မင်္ဂလာပါ! MLBB Top-Up Shop Bot မှ ကြိုဆိုပါတယ်။")
        return
    
    help_text = (
        "👑 **Admin Control Panel မှ ကြိုဆိုပါတယ်!**\n\n"
        "📌 **ဈေးနှုန်းနှင့် နာမည်ပြောင်းရန်:**\n"
        "`/setprice ID နာမည် | ဈေးနှုန်း`\n"
        "ဥပမာ - `/setprice 1 Twilight Pass | 40,000 Ks`"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=["setprice"])
def handle_setprice(message):
    if str(message.chat.id) != ADMIN_CHAT_ID:
        bot.reply_to(message, "⚠️ ဤလုပ်ဆောင်ချက်ကို Admin သာ အသုံးပြုနိုင်ပါသည်။")
        return

    raw = message.text.replace("/setprice", "", 1).strip()
    if "|" not in raw:
        bot.reply_to(message, "⚠️ ပုံစံမှားယွင်းနေပါသည်။\nဥပမာ - `/setprice 1 Twilight Pass | 40,000 Ks`", parse_mode="Markdown")
        return

    left, new_price = [x.strip() for x in raw.split("|", 1)]
    parts = left.split(" ", 1)
    if len(parts) < 2 or not parts[0].isdigit():
        bot.reply_to(message, "⚠️ Package ID နှင့် နာမည် ထည့်သွင်းပါ။", parse_mode="Markdown")
        return

    pkg_id = parts[0]
    new_name = parts[1].strip()

    if new_price.replace(",", "").isdigit():
        new_price = f"{int(new_price.replace(',', '')):,} Ks"

    sha, content, err = get_github_file()
    if err:
        bot.reply_to(message, f"❌ {err}")
        return

    pattern = rf'(\{{[^{{}}]*?id:\s*{pkg_id}\s*,[^{{}}]*?name:\s*)(["\'])(.*?)\2([^{{}}]*?price:\s*)(["\'])(.*?)\5'
    
    if not re.search(pattern, content):
        bot.reply_to(message, f"❌ ID {pkg_id} ကို index.html ထဲတွင် ရှာမတွေ့ပါ။")
        return

    def replacer(match):
        return f'{match.group(1)}"{new_name}"{match.group(4)}"{new_price}"'

    updated_content = re.sub(pattern, replacer, content, count=1)
    
    success, msg = push_github_file(updated_content, sha, f"Update package ID {pkg_id} via Telegram")
    if success:
        bot.reply_to(message, f"✅ **အောင်မြင်စွာ ပြောင်းလဲပြီးပါပြီ!**\nID: {pkg_id} | {new_name} — {new_price}", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"❌ {msg}")

if __name__ == "__main__":
    # Flask ကို Background Thread ဖြင့် စတင်ခြင်း (Render Port Requirement ဖြေရှင်းရန်)
    t = Thread(target=run_flask)
    t.start()
    
    print("Telegram Bot & Flask Web Server are running...")
    bot.infinity_polling()
    
