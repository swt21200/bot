const {onRequest} = require('firebase-functions/v2/https');
const {defineSecret} = require('firebase-functions/params');
const admin = require('firebase-admin');
admin.initializeApp();
const db = admin.firestore();
const BOT_TOKEN = defineSecret('TELEGRAM_BOT_TOKEN');
const ADMIN_CHAT_ID = defineSecret('TELEGRAM_ADMIN_CHAT_ID');

exports.telegramWebhook = onRequest({secrets:[BOT_TOKEN, ADMIN_CHAT_ID]}, async (req,res)=>{
  try {
    const update=req.body||{}; const msg=update.message; const cb=update.callback_query;
    if(msg && String(msg.chat.id)===ADMIN_CHAT_ID.value() && msg.text==='/menu'){
      await tg('sendMessage',{chat_id:msg.chat.id,text:'WP SHOP Admin Menu',reply_markup:{inline_keyboard:[[{text:'🎲 မဲဖောက်မည်',callback_data:'draw_next'}]]}});
    }
    if(cb && String(cb.message.chat.id)===ADMIN_CHAT_ID.value() && cb.data==='draw_next'){
      const result=await drawFirstPending();
      await tg('answerCallbackQuery',{callback_query_id:cb.id,text:result?`Winner: ${result.reward}`:'Pending ticket မရှိပါ'});
      if(result) await tg('sendMessage',{chat_id:ADMIN_CHAT_ID.value(),text:formatWinner(result),parse_mode:'Markdown'});
    }
    res.status(200).send('ok');
  }catch(e){console.error(e);res.status(500).send('error')}
});
async function drawFirstPending(){
  const snap=await db.collection('tickets').where('status','==','pending').orderBy('createdAt','asc').limit(1).get();
  if(snap.empty)return null;
  const ref=snap.docs[0].ref; let winner=null;
  await db.runTransaction(async tx=>{const fresh=await tx.get(ref);if(!fresh.exists||fresh.data().status!=='pending')return;const d=fresh.data();const profile=(await db.doc('users/'+d.refereeUid).get()).data()||{};const reward=Math.random()<.65?'Diamond 5 လုံး':'Diamond 10 လုံး';winner={...d,...profile,reward};tx.update(ref,{status:'won',reward,drawnAt:admin.firestore.FieldValue.serverTimestamp()})});
  return winner;
}
function formatWinner(w){return `✅ *WINNER*\n\n🏆 ဆု: ${w.reward}\n👤 Gmail: ${w.refereeEmail}\n🎮 User ID: ${w.mlUserId||'မထည့်ရသေး'}\n🌐 Server ID: ${w.serverId||'မထည့်ရသေး'}\n🕒 အချိန်: ယခု`}
async function tg(method,body){return fetch(`https://api.telegram.org/bot${BOT_TOKEN.value()}/${method}`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)})}
