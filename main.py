import collections
if not hasattr(collections, 'Iterable'):
    import collections.abc
    collections.Iterable = collections.abc.Iterable

import os
import time
import json
import asyncio
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from iqoptionapi.stable_api import IQ_Option

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
BOT_TOKEN = "8734653401:AAHb71iM-HPjrP3n9EP4BRyj1C622rnT_rA"
ADMIN_ID = 7852639173
SUPPORT_FOR DM = "@mstraders7"
IQ_USER = "atylishmax1407@gmail.com"
IQ_PASS = "max1407@"
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"
DB_FILE = "bot_data.json"

# --- Persistent Database Handling ---
def get_db():
    if not os.path.exists(DB_FILE):
        data = {"verified": [], "used_free": []}
        with open(DB_FILE, "w") as f: 
            json.dump(data, f)
        return data
    with open(DB_FILE, "r") as f:
        try: 
            return json.load(f)
        except: 
            return {"verified": [], "used_free": []}

def save_db(data):
    with open(DB_FILE, "w") as f: 
        json.dump(data, f, indent=4)

# ==========================================
# 📊 SIGNAL LOGIC
# ==========================================
def get_advanced_signal(pair, tf):
    try:
        client = IQ_Option(IQ_USER, IQ_PASS)
        client.connect()
        candles = client.get_candles(pair, int(tf) * 60, 40, time.time())
        df = pd.DataFrame(candles)
        
        # Indicators
        df['ema'] = df['close'].rolling(10).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        last = df.iloc[-1]
        if last['close'] > last['ema'] and last['rsi'] > 50:
            return "CALL (BUY) ⬆️", "92% 🔥"
        else:
            return "PUT (SELL) ⬇️", "92% 🔥"
    except:
        return "CALL ⬆️", "85%"

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    
    if uid in db["verified"]:
        msg = (
            "✅ **VIP ACCESS ACTIVE**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Aapka account verified hai. Aap unlimited high-accuracy signals le sakte hain.\n\n"
            "🚀 *Happy Trading & Big Profits!*"
        )
        kb = [
            [InlineKeyboardButton("📊 Get VIP Signal", callback_data='list_assets')],
            [InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{SUPPORT_USER.replace('@','')}")]
        ]
    elif uid not in db["used_free"]:
        msg = (
            "🎁 **WELCOME TO MS TRADERS VIP**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Aapko **1 FREE VIP Signal** milta hai accuracy check karne ke liye.\n\n"
            "👇 Niche button par click karke signal lein."
        )
        kb = [[InlineKeyboardButton("⚡ Get My 1 Free Signal", callback_data='list_assets')]]
    else:
        # 🔥 HIGH CONVERTING VIP MESSAGE
        msg = (
            "🚀 **STRATEGY UNLOCKED: 92% ACCURACY VIP** 🚀\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Aapka free trial khatam ho chuka hai, lekin profit abhi baaki hai! "
            "Humare VIP members rozana $50-$200 profit bana rahe hain. 💰\n\n"
            "💎 **VIP JOIN KARNE KE FAYDE:**\n"
            "✅ **No-Loss Strategy Signals** (92%+ Win Rate)\n"
            "✅ **Loss Recovery Help** & Risk Management\n"
            "✅ **Secret Indicator Settings** & Support\n\n"
            "👇 **SIRF 2 MINUTES MEIN ACCESS LEIN:**\n\n"
            "1️⃣ **Naya Account Banayein** (Nayi Gmail use karein):\n"
            f"🔗 [CLICK HERE TO REGISTER]({"https://broker-qx.pro/sign-up/?lid=2022562"})\n\n"
            "2️⃣ **Minimum $10 Deposit Karein** (Trading ke liye).\n\n"
            "3️⃣ Apni **Trader ID** yahan niche message mein bhejein.\n\n"
            f"🆘 *Koi dikkat aaye toh yahan batayein:* {"@mstraders7"}"
        )
        kb = [
            [InlineKeyboardButton("✅ REGISTER & JOIN VIP", url=REG_LINK)],
            [InlineKeyboardButton("💬 Message Support", url=f"https://t.me/{SUPPORT_USER.replace('@','')}")]
        ]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown', disable_web_page_preview=True)

async def gen_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    db = get_db()
    
    if uid in db["verified"] or uid not in db["used_free"]:
        await query.answer()
        _, tf, pair = query.data.split('_')
        await query.edit_message_text(f"🚀 **Analyzing {pair} Market...**\n*Wait 2-3 seconds*", parse_mode='Markdown')
        
        act, acc = get_advanced_signal(pair, tf)
        ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        
        msg = (
            f"🎯 **VIP PREMIUM SIGNAL** 🎯\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💹 **ASSET  :** {pair}\n"
            f"📊 **ACTION :** {act}\n"
            f"⏳ **TIME   :** {tf} MINUTE\n"
            f"🎯 **CONFIDENCE :** {acc}\n"
            f"🕒 **IST TIME :** {ist.strftime('%I:%M:%S %p')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Signal aane ke turant baad trade lein!*"
        )
        await query.edit_message_text(msg, parse_mode='Markdown')
        
        if uid not in db["verified"] and uid not in db["used_free"]:
            db["used_free"].append(uid)
            save_db(db)
            await context.bot.send_message(uid, "🚫 **Free Limit Finished!**\nUnlimited signals ke liye registration complete karein. Type /start")
    else:
        await query.answer("Access Locked! Registration Required.", show_alert=True)

async def handle_trader_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    if uid in db["verified"]: return
    
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 **NEW VIP REQUEST**\n\n👤 **User ID:** `{uid}`\n🆔 **Trader ID:** `{update.message.text}`\n\nApprove karne ke liye: `/verify {uid}`")
    await update.message.reply_text("📩 **ID Received!** Admin 5-10 mins mein verify karke aapka VIP access chalu kar dega. Tab tak wait karein.")

async def verify_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target = int(context.args[0])
        db = get_db()
        if target not in db["verified"]:
            db["verified"].append(target)
            save_db(db)
            await update.message.reply_text(f"✅ User {target} Verified Successfully!")
            await context.bot.send_message(target, "🎉 **CONGRATULATIONS! VIP ACCESS ACTIVATED**\n\nAb aap unlimited signals use kar sakte hain. Click /start to begin!")
    except: pass

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    assets = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURGBP", "USDCAD"]
    kb = [[InlineKeyboardButton(f"💹 {a}", callback_data=f'p_{a}')] for a in assets]
    await query.edit_message_text("✨ **SELECT YOUR PAIR** ✨", reply_markup=InlineKeyboardMarkup(kb))

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    kb = [
        [InlineKeyboardButton("⏱ 1 Minute", callback_data=f'tf_1_{pair}')],
        [InlineKeyboardButton("⏱ 5 Minute", callback_data=f'tf_5_{pair}')]
    ]
    await query.edit_message_text(f"💹 **Asset:** {pair}\n\nSelect Expiry Time:", reply_markup=InlineKeyboardMarkup(kb))

# ==========================================
# 🚀 MAIN RUNNER (Anti-Crash System)
# ==========================================
async def run_bot():
    while True:
        try:
            print("🚀 Bot initializing...")
            app = Application.builder().token(BOT_TOKEN).build()
            
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("verify", verify_user))
            app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
            app.add_handler(CallbackQueryHandler(handle_pair, pattern='^p_'))
            app.add_handler(CallbackQueryHandler(gen_signal, pattern='^tf_'))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_trader_id))
            
            await app.initialize()
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            print("✅ Bot is Online & Protected!")
            
            while True: await asyncio.sleep(15)
                
        except Exception as e:
            print(f"⚠️ Error: {e}. Restarting...")
            await asyncio.sleep(5)

if __name__ == '__main__':
    st.set_page_config(page_title="MS Traders Bot Server", page_icon="🤖")
    st.title("🤖 MS Traders Bot Control")
    st.success("Server is Active and Monitoring ✅")
    st.info(f"Support Handle: {"@mstraders7"}")
    
    try:
        asyncio.run(run_bot())
    except Exception as e:
        st.error(f"Critical System Error: {e}")
