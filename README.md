# WP Shop — Real Gmail + Telegram Draw Version

ဒီ version က HTML-only demo မဟုတ်ပါ။ Google Gmail login, Firestore transaction, one-Gmail-one-redemption နဲ့ Telegram Admin draw flow ပါပါတယ်။

## Setup

1. Firebase Console တွင် project တစ်ခုဖန်တီးပြီး **Authentication → Sign-in providers → Google** ကို enable လုပ်ပါ။ Web App register လုပ်ပြီး config ကို `index.html` ထဲက `firebaseConfig` မှာထည့်ပါ။
2. Firestore Database ဖန်တီးပြီး `firestore.rules` ကို deploy လုပ်ပါ။
3. `functions/` ထဲမှာ `npm install` လုပ်ပြီး Firebase CLI နဲ့ deploy လုပ်ပါ။
4. Secrets ထည့်ပါ: `firebase functions:secrets:set TELEGRAM_BOT_TOKEN` နှင့် `firebase functions:secrets:set TELEGRAM_ADMIN_CHAT_ID`။
5. Telegram bot webhook ကို deploy ပြီးတဲ့ `telegramWebhook` URL သို့ set လုပ်ပါ။ Bot ထဲမှာ `/menu` ပို့ပြီး **🎲 မဲဖောက်မည်** ခလုတ်နှိပ်ပါ။

User flow: Gmail login → account-specific invitation code → invited Gmail တစ်ခုလျှင် code တစ်ခါသာ → ticket created → Admin Telegram မှ ပထမဆုံး pending ticket တစ်ယောက်ပဲ draw.

`index.html` တွင် Firebase config မထည့်မချင်း Google login အလုပ်မလုပ်ပါ။ Telegram bot token ကို frontend ထဲမထည့်ထားပါ—Cloud Function secret ထဲမှာပဲထားပါ။
