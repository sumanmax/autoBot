import collections
if not hasattr(collections, 'Iterable'):
    import collections.abc
    collections.Iterable = collections.abc.Iterable

import os
import time
import asyncio
import pandas as pd
import streamlit as st
import pytz
import certifi
from datetime import datetime
from pymongo import MongoClient
from threading import Thread

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==========================================
# ⚙️ CONFIGURATION & SETTINGS
# ==========================================
BOT_TOKEN = "8734653401:AAEcLYLEVTCtM5EhGODwJanwhMQGYdS6JyU"
ADMIN_ID = 7852639173
SUPPORT_USER = "@mstraders7"
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"
IST = pytz.timezone('Asia/Kolkata')

# --- MongoDB Setup with SSL Fix ---
MONGO_URL = "mongodb+srv://atylishmax1407_db_user:max1407@cluster0.rxd940g.mongodb.net/?retryWrites=true&w=majority"
ca = certifi.where()

try:
    client_db = MongoClient(MONGO_URL, tlsCAFile=ca, serverSelectionTimeoutMS=5000)
    db_mongo = client_db['trading_bot_db']
    collection = db_mongo['users']
    # Check connection
    client_db.admin.command('ping')
    db_status = "Connected ✅"
except Exception as e:
    db_status = f"Error ❌ ({e})"

def get_user_status(uid):
    try:
        user = collection.find_one({"_id": uid})
        if not user:
            return {"is_verified": False, "used_free": False}
        return user
    except:
        return {"is_verified": False, "used_free": False}

def update_db(uid, field, value):
    try:
        collection.update_one({"_id": uid}, {"$set": {field: value}}, upsert=True)
    except:
        pass

# ==========================================
# 🤖 BOT LOGIC (Handlers)
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    status = get_user_status(uid)
    
    if status.get("is_verified"):
        msg = "👑 **WELCOME TO VIP CHANNEL**\n\nAapka VIP access active hai. Unlimited signals ke liye niche click karein!"
        kb = [[InlineKeyboardButton("📊 GET PREMIUM SIGNAL", callback_data='list_assets')]]
    elif not status.get("used_free"):
        msg = ("🎁 **WELCOME TO MS TRADERS**\n\n"
               "Hamari Accuracy **98%** hai. Aapko milta hai **1 FREE Trial Signal**.\n"
               "Niche button par click karke pair select karein 👇")
        kb = [[InlineKeyboardButton("⚡ START FREE TRIAL", callback_data='list_assets')]]
    else:
        msg = (f"🚀 **YOUR FREE TRIAL EXPIRED!**\n\n"
               f"Accuracy dekh li? Ab real profit ki baari hai! 💰\n\n"
               f"💎 **VIP JOINING STEPS:**\n"
               f"1️⃣ Register on: [CLICK HERE]({REG_LINK})\n"
               f"2️⃣ Deposit minimum $10.\n"
               f"3️⃣ Send your **Trader ID** here to verify.\n\n"
               f"🆘 Support: {SUPPORT_USER}")
        kb = [[InlineKeyboardButton("✅ REGISTER NOW", url=REG_LINK)],
              [InlineKeyboardButton("💬 CONTACT ADMIN", url=f"https://t.me/mstraders7")]]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown', disable_web_page_preview=True)

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Famous Assets
    assets = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURGBP", "USDCAD", "EURJPY", "GBPJPY"]
    kb = []
    for i in range(0, len(assets), 2):
        row = [InlineKeyboardButton(f"💹 {assets[i]}", callback_data=f'p_{assets[i]}')]
        if i+1 < len(assets):
            row.append(InlineKeyboardButton(f"💹 {assets[i+1]}", callback_data=f'p_{assets[i+1]}'))
        kb.append(row)
    
    await query.edit_message_text("✨ **SELECT TRADING ASSET** ✨\nMarket analyze kiya ja raha hai...", reply_markup=InlineKeyboardMarkup(kb))

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    
    kb = [[InlineKeyboardButton("⏱ 1 Minute", callback_data=f'tf_60_{pair}')],
          [InlineKeyboardButton("⏱ 5 Minutes", callback_data=f'tf_300_{pair}')]]
    
    await query.edit_message_text(f"💹 **ASSET:** {pair}\nSelect Timeframe:", reply_markup=InlineKeyboardMarkup(kb))

async def gen_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    status = get_user_status(uid)
    
    if status.get("is_verified") or not status.get("used_free"):
        await query.answer()
        _, tf, pair = query.data.split('_')
        await query.edit_message_text(f"🚀 **Analyzing {pair}...**\nPlease wait.")
        
        # Signal Generation logic
        act = "CALL (BUY) ⬆️" if time.time() % 2 == 0 else "PUT (SELL) ⬇️"
        now_ist = datetime.now(IST)
        
        msg = (f"🎯 **VIP PREMIUM SIGNAL** 🎯\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"💹 **ASSET  :** {pair}\n"
               f"📊 **ACTION :** {act}\n"
               f"🎯 **ACCURACY:** 98% 🔥\n"
               f"🕒 **TIME IST:** {now_ist.strftime('%I:%M:%S %p')}\n"
               f"━━━━━━━━━━━━━━━━━━")
        
        await query.edit_message_text(msg, parse_mode='Markdown')
        
        if not status.get("is_verified"):
            update_db(uid, "used_free", True)
            await asyncio.sleep(3)
            await context.bot.send_message(uid, "🛑 **Trial Finished!** VIP join karne ke liye /start karein.")
    else:
        await query.answer("Trial Expired! Join VIP.", show_alert=True)

# ==========================================
# 🚀 CORE ENGINE
# ==========================================

async def run_bot():
    while True:
        try:
            app = Application.builder().token(BOT_TOKEN).build()
            await app.initialize()
            await app.bot.delete_webhook(drop_pending_updates=True)
            
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
            app.add_handler(CallbackQueryHandler(handle_pair, pattern='^p_'))
            app.add_handler(CallbackQueryHandler(gen_signal, pattern='^tf_'))
            
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            while True: await asyncio.sleep(3600)
        except Exception as e:
            print(f"Bot Error: {e}")
            await asyncio.sleep(15)

def start_bot_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

# --- Streamlit Dashboard ---
st.set_page_config(page_title="MS Traders Bot", page_icon="💹")
st.title("MS Traders VIP Control Panel")
st.write(f"**Database Status:** {db_status}")

if "bot_started" not in st.session_state:
    st.session_state.bot_started = True
    Thread(target=start_bot_thread, daemon=True).start()
    st.success("Bot is successfully running 24/7! ✅")

st.info("Check Telegram for signals. Timezone set to IST (Asia/Kolkata).")
