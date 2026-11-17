import os
import re
import base64
import requests
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# --- CONFIGURATIONS ---
TELEGRAM_BOT_TOKEN = "8901991980:AAGNk2UpHPQGjOh1hox7ZmdDSWErZ3VJqm0"
ADMIN_CHAT_ID = "8607494475"

# GitHub Configuration (Render Environment Variable မှ အလိုအလျောက် ဆွဲယူမည်)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_OWNER = "swt21200"
REPO_NAME = "Shack"
FILE_PATH = "index.html"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

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

def get_admin_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("📋 ဈေးနှုန်းစာရင်းကြည့်ရန်"), KeyboardButton("ℹ️ အသုံးပြုနည်း"))
    return markup

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    if str(message.chat.id) != ADMIN_CHAT_ID:
        bot.reply_to(message, "👋 မင်္ဂလာပါ! MLBB Top-Up Shop Bot မှ ကြိုဆိုပါတယ်။")
        return
    
    help_text = (
        "👑 **Admin Control Panel မှ ကြိုဆိုပါတယ်!**\n\n"
        "📌 **ဈေးနှုန်းနှင့် နာမည်ပြောင်းရန်:**\n"
        "`/setprice ID နာမည် | ဈေးနှုန်း`\n"
        "ဥပမာ - `/setprice 1 Twilight Pass | 40,000 Ks`\n\n"
        "🖼️ **Banner ပုံပြောင်းရန်:**\n"
        "ပုံတစ်ပုံပို့ပြီး Caption မှာ `/setbanner` လို့ ရေးပို့ပါ။\n\n"
        "🔰 **Shop Icon ပြောင်းရန်:**\n"
        "ပုံတစ်ပုံပို့ပြီး Caption မှာ `/seticon` လို့ ရေးပို့ပါ။"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown", reply_markup=get_admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "ℹ️ အသုံးပြုနည်း")
def handle_help_btn(message):
    send_welcome(message)

@bot.message_handler(func=lambda m: m.text == "📋 ဈေးနှုန်းစာရင်းကြည့်ရန်" or m.text == "/prices")
def list_prices(message):
    if str(message.chat.id) != ADMIN_CHAT_ID:
        return
    
    sha, content, err = get_github_file()
    if err:
        bot.reply_to(message, f"❌ {err}")
        return
    
    # defaultPackages ထဲမှ ID, name, price များကို ရှာဖွေဖတ်ရှုခြင်း
    matches = re.findall(r'\{\s*id:\s*(\d+),\s*name:\s*["\'](.*?)["\'],\s*price:\s*["\'](.*?)["\']', content)
    if not matches:
        bot.reply_to(message, "⚠️ index.html ထဲတွင် Package စာရင်း ရှာမတွေ့ပါ။")
        return
    
    msg_lines = ["📦 **လက်ရှိ Package စာရင်းများ:**\n"]
    for pkg_id, name, price in matches:
        msg_lines.append(f"ID {pkg_id} : {name} — **{price}**")
    msg_lines.append("\n⚙️ ပြောင်းလဲလိုပါက:\n`/setprice ID နာမည် | ဈေးနှုန်း` ကို အသုံးပြုပါ။")
    
    bot.reply_to(message, "\n".join(msg_lines), parse_mode="Markdown")

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
        bot.reply_to(message, "⚠️ Package ID နှင့် နာမည် ထည့်သွင်းပါ။\nဥပမာ - `/setprice 1 Twilight Pass | 40,000 Ks`", parse_mode="Markdown")
        return

    pkg_id = parts[0]
    new_name = parts[1].strip()

    # ဈေးနှုန်းနောက်တွင် Ks မပါသေးပါက အလိုအလျောက် ထည့်ပေးခြင်း
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
        bot.reply_to(
            message,
            f"✅ **အောင်မြင်စွာ ပြောင်းလဲပြီးပါပြီ!**\n"
            f"🆔 ID: {pkg_id}\n"
            f"💎 နာမည်: {new_name}\n"
            f"💰 ဈေးနှုန်း: {new_price}\n\n"
            f"🔄 Vercel တွင် ၁ မိနစ်အတွင်း လူတိုင်းအတွက် Update ဖြစ်သွားပါမည်။",
            parse_mode="Markdown"
        )
    else:
        bot.reply_to(message, f"❌ {msg}")

@bot.message_handler(content_types=["photo"])
def handle_photo_commands(message):
    if str(message.chat.id) != ADMIN_CHAT_ID:
        return
    
    caption = (message.caption or "").strip().lower()
    if caption not in ["/setbanner", "/seticon"]:
        return

    target_filename = "banner.png" if caption == "/setbanner" else "icon.png"
    element_id = "shopBanner" if caption == "/setbanner" else "shopIcon"

    # Telegram မှ ပုံအား ဒေါင်းလုဒ်ဆွဲယူခြင်း
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    # 1. ပုံဖိုင်အား GitHub Repository ထဲသို့ တိုက်ရိုက် Upload/Update တင်ခြင်း
    img_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{target_filename}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    
    get_res = requests.get(img_url, headers=headers)
    img_sha = get_res.json().get("sha") if get_res.status_code == 200 else None

    payload = {
        "message": f"Update {target_filename} via Telegram",
        "content": base64.b64encode(downloaded_file).decode("utf-8")
    }
    if img_sha:
        payload["sha"] = img_sha

    put_res = requests.put(img_url, headers=headers, json=payload)
    if put_res.status_code not in [200, 201]:
        bot.reply_to(message, f"❌ ပုံတင်ရာတွင် အမှားဖြစ်နေပါသည်: {put_res.text}")
        return

    # 2. Browser Cache မမိစေရန် index.html ထဲရှိ ပုံ URL နောက်တွင် version timestamp (?v=...) ထည့်ပေးခြင်း
    import time
    ts = int(time.time())
    new_img_src = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/refs/heads/main/{target_filename}?v={ts}"

    sha, html_content, err = get_github_file()
    if not err and html_content:
        html_pattern = rf'(id=["\']{element_id}["\'][^>]*?src=["\'])([^"\']+)(["\'])'
        if re.search(html_pattern, html_content):
            updated_html = re.sub(html_pattern, rf'\g<1>{new_img_src}\g<3>', html_content, count=1)
            push_github_file(updated_html, sha, f"Refresh {target_filename} cache buster")

    bot.reply_to(
        message,
        f"✅ **{target_filename} အောင်မြင်စွာ ပြောင်းလဲပြီးပါပြီ!**\n"
        f"🔄 Vercel တွင် ၁ မိနစ်အတွင်း လူတိုင်းအတွက် ပုံအသစ် ပေါ်လာပါမည်။",
        parse_mode="Markdown"
    )

print("Telegram Bot is running with Render Environment Variable...")
bot.infinity_polling()
  
