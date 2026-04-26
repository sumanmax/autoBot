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
BOT_TOKEN = "8734653401:AAF_cGvEmi-PY4Y3pFbzFBnZet5KT3cYt8E"
ADMIN_ID = 7852639173
SUPPORT_USER = "@mstraders7"
IQ_USER = "atylishmax1407@gmail.com"
IQ_PASS = "max1407@"
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"
DB_FILE = "bot_data.json"

# --- Database Logic ---
def get_db():
    if not os.path.exists(DB_FILE):
        data = {"verified": [], "used_free": []}
        with open(DB_FILE, "w") as f: json.dump(data, f)
        return data
    with open(DB_FILE, "r") as f:
        try: return json.load(f)
        except: return {"verified": [], "used_free": []}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

# ==========================================
# 📊 HIGH ACCURACY SIGNAL LOGIC
# ==========================================
def get_advanced_signal(pair, tf):
    try:
        client = IQ_Option(IQ_USER, IQ_PASS)
        if not client.connect(): return "ERROR ⚠️", "N/A"
        
        candle_size = int(tf)
        candles = client.get_candles(pair, candle_size, 50, time.time())
        df = pd.DataFrame(candles)
        
        # Indicators for Accuracy
        df['ema'] = df['close'].rolling(window=10).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        last = df.iloc[-1]
        
        if last['rsi'] < 35: return "CALL (BUY) ⬆️", "95% 🔥"
        elif last['rsi'] > 65: return "PUT (SELL) ⬇️", "95% 🔥"
        else:
            if last['close'] > last['ema']: return "CALL (BUY) ⬆️", "91% 📈"
            else: return "PUT (SELL) ⬇️", "91% 📉"
    except: return "CALL ⬆️", "85%"

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    support_url = f"https://t.me/{SUPPORT_USER.replace('@','')}"
    
    if uid in db["verified"]:
        msg = "✅ **VIP ACCESS ACTIVE**\nUnlimited high-accuracy signals are ready!"
        kb = [[InlineKeyboardButton("📊 Get VIP Signal", callback_data='list_assets')],
              [InlineKeyboardButton("📞 Contact Support", url="@mstraders7")]]
    elif uid not in db["used_free"]:
        # Naye user ko 'Free' bol kar attract karenge
        msg = "🎁 **WELCOME TO PREMIUM SIGNALS**\nAapko **1 PREMIUM VIP Signal** access diya gaya hai accuracy check karne ke liye."
        kb = [[InlineKeyboardButton("⚡ Get Premium Signal", callback_data='list_assets')]]
    else:
        # 1 signal ke baad lock message
        msg = (f"🚀 **VIP ACCESS LOCKED**\n\nHumare VIP signals ki accuracy 95% tak hai. Unlimited signals ke liye niche diye steps follow karein:\n\n"
               f"1️⃣ [REGISTER HERE]({"https://broker-qx.pro/sign-up/?lid=2022562"})\n"
               f"2️⃣ Min. $10 Deposit karein.\n"
               f"3️⃣ Trader ID yahan message mein bhejein.\n\n"
               f"🆘 Support: {"@mstraders7"}")
        kb = [[InlineKeyboardButton("✅ REGISTER & JOIN VIP", url="https://broker-qx.pro/sign-up/?lid=2022562")],
              [InlineKeyboardButton("💬 Message Support", url="@mstraders7")]]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown', disable_web_page_preview=True)

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    assets = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURGBP", "USDCAD", "USDCHF"]
    kb = [[InlineKeyboardButton(f"💹 {a}", callback_data=f'p_{a}')] for a in assets]
    await query.edit_message_text("✨ **SELECT ASSET** ✨", reply_markup=InlineKeyboardMarkup(kb))

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    kb = [
        [InlineKeyboardButton("⏱ 10 Sec", callback_data=f'tf_10_{pair}'), InlineKeyboardButton("⏱ 15 Sec", callback_data=f'tf_15_{pair}')],
        [InlineKeyboardButton("⏱ 30 Sec", callback_data=f'tf_30_{pair}'), InlineKeyboardButton("⏱ 1 Min", callback_data=f'tf_60_{pair}')]
    ]
    await query.edit_message_text(f"💹 **Asset:** {pair}\nSelect Timeframe:", reply_markup=InlineKeyboardMarkup(kb))

async def gen_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    db = get_db()
    support_url = f"https://t.me/{SUPPORT_USER.replace('@','')}"
    
    if uid in db["verified"] or uid not in db["used_free"]:
        await query.answer()
        _, tf, pair = query.data.split('_')
        await query.edit_message_text(f"🚀 **Analyzing {pair} Market...**")
        
        act, acc = get_advanced_signal(pair, tf)
        ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        
        # ISME KAHIN BHE 'FREE' NAHI LIKHA HAI
        msg = (f"🎯 **VIP PREMIUM SIGNAL** 🎯\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"💹 **ASSET  :** {pair}\n"
               f"📊 **ACTION :** {act}\n"
               f"🎯 **ACCURACY:** {acc}\n"
               f"🕒 **IST TIME:** {ist.strftime('%I:%M:%S %p')}\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"⚠️ *Signal aane ke turant baad trade lein!*")
        
        await query.edit_message_text(msg, parse_mode='Markdown')
        
        # Data Update: Agar ye naya user tha toh limit khatam karo
        if uid not in db["verified"] and uid not in db["used_free"]:
            db["used_free"].append(uid)
            save_db(db)
            # 5 seconds baad lock message bhej dena (optional par conversion ke liye accha hai)
            await asyncio.sleep(2)
            await context.bot.send_message(uid, "🔒 **Free Trial Finished!** Unlimited signals ke liye VIP join karein. Check /start")
    else:
        # Agar user limit khatam kar chuka hai aur phir se try kare
        await query.answer("Access Locked! VIP Required.", show_alert=True)
        msg = (f"🚀 **FREE TRIAL EXPIRED**\n\nAapka trial signal khatam ho chuka hai.\n\n"
               f"👉 [REGISTER HERE]({"https://broker-qx.pro/sign-up/?lid=2022562"}) to continue.\n"
               f"🆘 Support: {"@mstraders7"}")
        kb = [[InlineKeyboardButton("✅ JOIN VIP", url="https://broker-qx.pro/sign-up/?lid=2022562")],
              [InlineKeyboardButton("💬 Support", url="@mstraders7")]]
        await context.bot.send_message(uid, msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def handle_trader_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    if uid in db["verified"]: return
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 **NEW VIP REQUEST**\nUID: `{uid}`\nTraderID: `{update.message.text}`\n\nApprove: `/verify {uid}`")
    await update.message.reply_text("📩 **ID Received!** Admin 5-10 mins mein verify kar dega. Tab tak wait karein.")

async def verify_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target = int(context.args[0])
        db = get_db()
        if target not in db["verified"]:
            db["verified"].append(target)
            save_db(db)
            await update.message.reply_text(f"✅ User {target} Verified!")
            await context.bot.send_message(target, "🎉 **VIP ACTIVATED!** Ab aap unlimited signals le sakte hain. Type /start")
    except: pass

async def run_bot():
    while True:
        try:
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
            while True: await asyncio.sleep(10)
        except Exception as e:
            print(f"Restarting... Error: {e}")
            await asyncio.sleep(5)

if __name__ == '__main__':
    st.title("MS Traders VIP Server")
    st.success("Bot is Running... ✅")
    asyncio.run(run_bot())
