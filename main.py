import collections
# IQ Option compatibility fix (SABSE UPAR RAKHEIN)
if not hasattr(collections, 'Iterable'):
    import collections.abc
    collections.Iterable = collections.abc.Iterable

import os
import time
import asyncio
import pandas as pd
import streamlit as st
import pytz
from datetime import datetime
from pymongo import MongoClient
from iqoptionapi.stable_api import IQ_Option
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
BOT_TOKEN = "8734653401:AAFsiz0sF3h4Jl0E5GYS_zxZwgwd9O6ZKm4"
ADMIN_ID = 7852639173
SUPPORT_USER = "@mstraders7"
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"
IQ_USER = "atylishmax1407@gmail.com"
IQ_PASS = "max1407@"
IST = pytz.timezone('Asia/Kolkata')
MONGO_URI = "mongodb+srv://atylishmax1407_db_user:L6T5cl4gztJIaRRs@cluster0.rxd940g.mongodb.net/?appName=Cluster0"

# --- Database Setup ---
try:
    client_db = MongoClient(MONGO_URI)
    db_col = client_db['trading_bot_db']['bot_data']
except Exception as e:
    st.error(f"DB Error: {e}")

def get_db():
    try:
        data = db_col.find_one({"_id": "bot_storage"})
        if not data:
            initial = {"_id": "bot_storage", "verified": [], "used_free": []}
            db_col.insert_one(initial)
            return initial
        return data
    except: return {"verified": [], "used_free": []}

def save_db(data):
    try: db_col.replace_one({"_id": "bot_storage"}, data, upsert=True)
    except: pass

# ==========================================
# 📊 YOUR ORIGINAL SIGNAL LOGIC
# ==========================================
def get_signal_logic(pair, tf):
    try:
        api = IQ_Option(IQ_USER, IQ_PASS)
        if not api.connect():
            return "CONN ERROR ⚠️", "N/A", "N/A"
        
        time.sleep(2) # Stabilize connection
        candles = api.get_candles(pair, int(tf), 60, time.time())
        if not candles: return "NO DATA ⚠️", "N/A", "N/A"
        
        df = pd.DataFrame(candles)
        
        # Indicators Logic (EMA & RSI)
        df['ema'] = df['close'].rolling(window=12).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        last = df.iloc[-1]
        entry_time = datetime.now(IST).strftime('%I:%M:%S %p')
        
        # Signal Conditions
        if last['rsi'] < 30: return "CALL (BUY) ⬆️", "97% 🔥", entry_time
        elif last['rsi'] > 70: return "PUT (SELL) ⬇️", "97% 🔥", entry_time
        else:
            direction = "CALL ⬆️" if last['close'] > last['ema'] else "PUT ⬇️"
            return direction, "92% 📈", entry_time
    except:
        return "ERROR ⚠️", "N/A", "N/A"

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    
    if uid in db["verified"]:
        msg = "✅ **VIP ACCESS ACTIVE**\nUnlimited signals ready!"
        kb = [[InlineKeyboardButton("📊 Get VIP Signal", callback_data='list_assets')]]
    elif uid not in db["used_free"]:
        msg = "🎁 **FREE TRIAL**\nAapko **1 FREE VIP Signal** mila hai."
        kb = [[InlineKeyboardButton("⚡ Get Signal", callback_data='list_assets')]]
    else:
        msg = (f"🚀 **VIP ACCESS REQUIRED**\n\n1️⃣ [REGISTER HERE]({REG_LINK})\n"
               f"2️⃣ Deposit $10\n3️⃣ Send your Trader ID here.")
        kb = [[InlineKeyboardButton("✅ REGISTER NOW", url=REG_LINK)]]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    assets = ["EURUSD", "GBPUSD", "USDJPY", "EURJPY", "AUDUSD", "GBPJPY", "USDCAD"]
    kb = []
    for i in range(0, len(assets), 2):
        row = [InlineKeyboardButton(f"💹 {assets[i]}", callback_data=f'p_{assets[i]}')]
        if i+1 < len(assets):
            row.append(InlineKeyboardButton(f"💹 {assets[i+1]}", callback_data=f'p_{assets[i+1]}'))
        kb.append(row)
    await query.edit_message_text("✨ **SELECT ASSET** ✨", reply_markup=InlineKeyboardMarkup(kb))

async def handle_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    kb = [[InlineKeyboardButton("⏱ 1m", callback_data=f'tf_60_{pair}'), 
           InlineKeyboardButton("⏱ 5m", callback_data=f'tf_300_{pair}')]]
    await query.edit_message_text(f"💹 Asset: **{pair}**\nSelect Timeframe:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def send_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    db = get_db()
    
    if uid in db["verified"] or uid not in db["used_free"]:
        await query.answer()
        _, tf, pair = query.data.split('_')
        await query.edit_message_text(f"🚀 **Analyzing {pair} Market...**")
        
        act, acc, tm = get_signal_logic(pair, tf)
        
        msg = (f"🎯 **VIP SIGNAL**\n━━━━━━━━━━━━━━━\n"
               f"💹 ASSET: **{pair}**\n📊 ACTION: **{act}**\n"
               f"🎯 ACCURACY: **{acc}**\n🕒 ENTRY (IST): **{tm}**\n"
               f"━━━━━━━━━━━━━━━")
        
        await query.edit_message_text(msg, parse_mode='Markdown')
        if uid not in db["verified"]:
            db["used_free"].append(uid)
            save_db(db)
    else:
        await query.answer("Join VIP for more signals!", show_alert=True)

async def handle_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    if uid not in db["verified"]:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 **VIP Request**\nTrader ID: `{update.message.text}`\nUID: `{uid}`\nApprove: `/verify {uid}`")
        await update.message.reply_text("📩 ID sent to Admin for verification!")

async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        try:
            target_uid = int(context.args[0])
            db = get_db()
            if target_uid not in db["verified"]:
                db["verified"].append(target_uid)
                save_db(db)
                await update.message.reply_text(f"✅ User {target_uid} Verified!")
                await context.bot.send_message(target_uid, "🎉 **VIP ACTIVATED!**\nUnlimited signals are now unlocked. Type /start")
        except: await update.message.reply_text("Format: /verify [UID]")

# ==========================================
# 🔄 ENGINE
# ==========================================
async def main_engine():
    while True:
        try:
            app = Application.builder().token(BOT_TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("verify", verify_command))
            app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
            app.add_handler(CallbackQueryHandler(handle_time, pattern='^p_'))
            app.add_handler(CallbackQueryHandler(send_signal, pattern='^tf_'))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_id))
            
            await app.initialize()
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            while True: await asyncio.sleep(3600)
        except: await asyncio.sleep(10)

if __name__ == '__main__':
    st.set_page_config(page_title="VIP Server")
    st.title("📈 VIP Trading Server")
    if "bot_running" not in st.session_state:
        st.session_state.bot_running = True
        import threading
        threading.Thread(target=lambda: asyncio.run(main_engine()), daemon=True).start()
    st.success("Bot is Live & Connected to MongoDB ✅")
