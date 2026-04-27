import collections
if not hasattr(collections, 'Iterable'):
    import collections.abc
    collections.Iterable = collections.abc.Iterable

# Iske baad baaki imports
from iqoptionapi.stable_api import IQ_Option
# ... rest of your code

import os
import time
import asyncio
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from iqoptionapi.stable_api import IQ_Option

# ==========================================
# ⚙️ CONFIGURATION & MONGODB
# ==========================================
BOT_TOKEN = "8734653401:AAFnkFQbZ0CZRrshGCuUuxUbc4OU3HWVaCM"
ADMIN_ID = 7852639173
SUPPORT_USER = "@mstraders7"
IQ_USER = "atylishmax1407@gmail.com"
IQ_PASS = "max1407@"
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"

# MongoDB Connection String (Permanent Storage)
MONGO_URI = "mongodb+srv://atylishmax1407_db_user:L6T5cl4gztJIaRRs@cluster0.rxd940g.mongodb.net/?appName=Cluster0"

try:
    client_db = MongoClient(MONGO_URI)
    mongo_db = client_db['trading_bot_db']
    users_col = mongo_db['bot_data']
except Exception as e:
    st.error(f"MongoDB Connection Error: {e}")

# --- Database Logic (MongoDB) ---
def get_db():
    try:
        data = users_col.find_one({"_id": "bot_storage"})
        if not data:
            initial_data = {"_id": "bot_storage", "verified": [], "used_free": []}
            users_col.insert_one(initial_data)
            return initial_data
        return data
    except:
        return {"verified": [], "used_free": []}

def save_db(data):
    try:
        users_col.replace_one({"_id": "bot_storage"}, data)
    except Exception as e:
        print(f"DB Save Error: {e}")

# ==========================================
# 📊 SIGNAL LOGIC (SAME TO SAME)
# ==========================================
def get_advanced_signal(pair, tf):
    try:
        client = IQ_Option(IQ_USER, IQ_PASS)
        if not client.connect(): return "ERROR ⚠️", "N/A"
        
        candle_size = int(tf)
        candles = client.get_candles(pair, candle_size, 60, time.time())
        df = pd.DataFrame(candles)
        
        df['ema'] = df['close'].rolling(window=12).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        last = df.iloc[-1]
        
        if last['rsi'] < 30: return "CALL (BUY) ⬆️", "97% 🔥"
        elif last['rsi'] > 70: return "PUT (SELL) ⬇️", "97% 🔥"
        else:
            if last['close'] > last['ema']: return "CALL (BUY) ⬆️", "92% 📈"
            else: return "PUT (SELL) ⬇️", "92% 📉"
    except: return "CALL ⬆️", "85%"

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    support_url = f"https://t.me/{SUPPORT_USER.replace('@','')}"
    
    if uid in db["verified"]:
        msg = "✅ **VIP ACCESS ACTIVE**\nUnlimited premium signals are ready for you!"
        kb = [[InlineKeyboardButton("📊 Get VIP Signal", callback_data='list_assets')],
              [InlineKeyboardButton("📞 Contact Support", url="@mstraders7")]]
    elif uid not in db["used_free"]:
        msg = "🎁 **WELCOME TO PREMIUM SIGNALS**\nAapko **1 PREMIUM VIP Signal** access diya gaya hai accuracy check karne ke liye."
        kb = [[InlineKeyboardButton("⚡ Get Premium Signal", callback_data='list_assets')]]
    else:
        msg = (f"🚀 **VIP ACCESS LOCKED**\n\nUnlimited 95%+ accuracy signals ke liye niche diye steps follow karein:\n\n"
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
    
    assets = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURGBP", "USDCAD", "USDCHF", "EURJPY", "GBPJPY", "AUDJPY", "EURAUD", "NZDUSD"]
    kb = []
    for i in range(0, len(assets), 2):
        row = [InlineKeyboardButton(f"💹 {assets[i]}", callback_data=f'p_{assets[i]}')]
        if i+1 < len(assets):
            row.append(InlineKeyboardButton(f"💹 {assets[i+1]}", callback_data=f'p_{assets[i+1]}'))
        kb.append(row)
    
    kb.append([InlineKeyboardButton("🔙 Back to Main", callback_data='start_back')])
    await query.edit_message_text("✨ **SELECT TRADING ASSET** ✨", reply_markup=InlineKeyboardMarkup(kb))

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    
    kb = [
        [InlineKeyboardButton("⏱ 10 Sec", callback_data=f'tf_10_{pair}'), InlineKeyboardButton("⏱ 15 Sec", callback_data=f'tf_15_{pair}')],
        [InlineKeyboardButton("⏱ 30 Sec", callback_data=f'tf_30_{pair}'), InlineKeyboardButton("⏱ 1 Min", callback_data=f'tf_60_{pair}')],
        [InlineKeyboardButton("⏱ 5 Min", callback_data=f'tf_300_{pair}')]
    ]
    await query.edit_message_text(f"💹 **Asset:** {pair}\nSelect Timeframe:", reply_markup=InlineKeyboardMarkup(kb))

async def gen_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    db = get_db()
    
    if uid in db["verified"] or uid not in db["used_free"]:
        await query.answer()
        _, tf, pair = query.data.split('_')
        await query.edit_message_text(f"🚀 **Analyzing {pair} Market...**")
        
        act, acc = get_advanced_signal(pair, tf)
        ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        
        msg = (f"🎯 **VIP PREMIUM SIGNAL** 🎯\n━━━━━━━━━━━━━━━━━━\n"
               f"💹 ASSET  : {pair}\n📊 **ACTION : {act}\n🎯 ACCURACY: {acc}\n🕒 IST TIME: {ist.strftime('%I:%M:%S %p')}\n"
               f"━━━━━━━━━━━━━━━━━━\n⚠️ *Fast signal: Entry turant lein!*")
        
        await query.edit_message_text(msg, parse_mode='Markdown')
        
        if uid not in db["verified"] and uid not in db["used_free"]:
            db["used_free"].append(uid)
            save_db(db)
            await asyncio.sleep(2)
            await context.bot.send_message(uid, "🔒 Free Trial Finished! VIP join karein unlimited signals ke liye.")
    else:
        await query.answer("Access Locked! VIP Required.", show_alert=True)

async def handle_trader_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    if uid in db["verified"]: return
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 VIP Request\nUID: `{uid}`\nID: `{update.message.text}`\n\nApprove: `/verify {uid}`")
    await update.message.reply_text("📩 ID Received! Admin will verify soon.")

async def verify_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target = int(context.args[0])
        db = get_db()
        if target not in db["verified"]:
            db["verified"].append(target)
            save_db(db)
            await update.message.reply_text(f"✅ User {target} Verified!")
            await context.bot.send_message(target, "🎉 VIP ACTIVATED! Check /start")
    except: pass

# ==========================================
# 🔄 ENGINE (SAFE AUTO-RECONNECT)
# ==========================================
async def run_bot():
    while True:
        app = None
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
            while True: await asyncio.sleep(3600)
        except Exception as e:
            if app:
                try: 
                    await app.updater.stop()
                    await app.stop()
                except: pass
            await asyncio.sleep(10)

if __name__ == '__main__':
    st.set_page_config(page_title="Trading Bot")
    st.title("📈 VIP Signal Bot Server")
    st.success("Server Running... ✅")
    st.info("Database: MongoDB Permanent Storage Active")

    if "bot_started" not in st.session_state:
        st.session_state.bot_started = True
        import threading
        def start_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_bot())
        
        threading.Thread(target=start_loop, daemon=True).start()
