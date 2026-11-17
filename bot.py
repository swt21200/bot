import base64
import requests
import telebot

# --- CONFIGURATIONS ---
TELEGRAM_BOT_TOKEN = "8901991980:AAGNk2UpHPQGjOh1hox7ZmdDSWErZ3VJqm0"
ADMIN_CHAT_ID = "8607494475"

# GitHub Configuration
GITHUB_TOKEN = (
    "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"
)
REPO_OWNER = "swt21200"  # Your GitHub Username
REPO_NAME = "bot"  # Your Repository Name
FILE_PATH = "index.html"  # File to update

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


def update_github_html(new_price_text):
  url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
  headers = {
      "Authorization": f"Bearer {GITHUB_TOKEN}",
      "Accept": "application/vnd.github+json",
  }

  # 1. Get current file SHA and content
  response = requests.get(url, headers=headers)
  if response.status_code != 200:
    return False, "GitHub မှ ဖိုင်ကို ဆွဲယူ၍မရပါ။"

  file_data = response.json()
  sha = file_data["sha"]
  current_content = base64.b64decode(file_data["content"]).decode("utf-8")

  # 2. Modify content (ဥပမာအားဖြင့် defaultPackages ထဲက ဈေးနှုန်းကို အစားထိုးခြင်း)
  # ဒီနေရာမှာ Admin ပို့လိုက်တဲ့ ဈေးနှုန်းအသစ်နဲ့ HTML ထဲက ဈေးနှုန်းကို Code ဖြင့် အစားထိုးနိုင်သည်
  # ရိုးရှင်းလွယ်ကူစေရန် ဈေးနှုန်းအသစ်ကို HTML ထဲသို့ ထည့်သွင်းပုံစံ ရေးနိုင်သည်

  updated_content = current_content  # လိုအပ်ပါက string replace ဖြင့် ပြင်နိုင်သည်

  # 3. Commit and Push back to GitHub
  encoded_content = base64.b64encode(updated_content.encode("utf-8")).decode(
      "utf-8"
  )
  payload = {
      "message": "Update packages via Telegram Bot",
      "content": encoded_content,
      "sha": sha,
  }

  put_response = requests.put(url, headers=headers, json=payload)
  if put_response.status_code in [200, 201]:
    return True, "GitHub သို့ အောင်မြင်စွာ အပ်ဒိတ်တင်ပြီးပါပြီ။"
  else:
    return False, f"Error: {put_response.text}"


@bot.message_handler(commands=["setprice"])
def handle_setprice(message):
  if str(message.chat.id) != ADMIN_CHAT_ID:
    bot.reply_to(message, "⚠️ ဤ විධාန်ကို Admin သာ အသုံးပြုနိုင်ပါသည်။")
    return

  # ဥပမာ - /setprice 4800 Ks လို့ ပို့လိုက်ရင်
  text = message.text.replace("/setprice", "").strip()
  if not text:
    bot.reply_to(
        message,
        "ကျေးဇူးပြု၍ ပြောင်းလဲလိုသော ဈေးနှုန်းကို တွဲဖက်ရေးပါ။ (ဥပမာ -"
        " /setprice 5000 Ks)",
    )
    return

  success, msg = update_github_html(text)
  if success:
    bot.reply_to(
        message,
        f"✅ ဈေးနှုန်း အောင်မြင်စွာ ပြောင်းလဲပြီးပါပြီ!\n{msg}\n(Vercel"
        " တွင် မိနစ်ပိုင်းအတွင်း အလိုအလျောက် Update ဖြစ်ပါမည်)",
    )
  else:
    bot.reply_to(message, f"❌ မအောင်မြင်ပါ: {msg}")


print("Telegram Bot is running...")
bot.infinity_polling()
