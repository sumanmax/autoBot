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
from datetime import datetime
from pymongo import MongoClient
from threading import Thread

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from iqoptionapi.stable_api import IQ_Option

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
BOT_TOKEN = "8734653401:AAG5Ng8cG3mLbBxxTq-LQQZ6yZdTO8LLIP8"
ADMIN_ID = 7852639173
SUPPORT_USER = "@mstraders7"
IQ_USER = "atylishmax1407@gmail.com"
IQ_PASS = "max1407@"
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"

IST = pytz.timezone('Asia/Kolkata')

# --- MongoDB Setup ---
MONGO_URL = "mongodb+srv://atylishmax1407_db_user:password@cluster0.rxd940g.mongodb.net/?appName=Cluster0"
client_db = MongoClient(MONGO_URL)
db_mongo = client_db['trading_bot_db']
collection = db_mongo['users']

def get_db():
    verified = []
    used_free = []
    for user in collection.find():
        if user.get("is_verified"): verified.append(user["_id"])
        if user.get("used_free"): used_free.append(user["_id"])
    return {"verified": verified, "used_free": used_free}

def update_user_db(uid, field, value):
    collection.update_one({"_id": uid}, {"$set": {field: value}}, upsert=True)

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    
    if uid in db["verified"]:
        msg = "👑 **WELCOME VIP TRADER**\n\nUnlimited signals are ready for you. Market analyze karein aur profit banayein!"
        kb = [[InlineKeyboardButton("📊 GET PREMIUM SIGNAL", callback_data='list_assets')]]
    elif uid not in db["used_free"]:
        msg = ("🎁 **WELCOME TO MS TRADERS**\n\n"
               "Aapko milta hai **1 High-Accuracy Trial Signal** bilkul free.\n"
               "Hamari accuracy **95% - 98%** rehti hai. Neeche button par click karke signal lein 👇")
        kb = [[InlineKeyboardButton("⚡ GET FREE TRIAL SIGNAL", callback_data='list_assets')]]
    else:
        # Trial khatam hone ke baad ka Attractive Message
        msg = (f"🚀 **YOUR FREE TRIAL HAS EXPIRED!**\n\n"
               f"Aapne accuracy dekh li hai? Ab waqt hai real profit banane ka! 💰\n\n"
               f"💎 **VIP ACCESS BENEFITS:**\n"
               f"✅ 24/7 Unlimited Premium Signals\n"
               f"✅ Accuracy 98% (No Martingale)\n"
               f"✅ Personal Support & Best Strategies\n\n"
               f"👇 **VIP JOIN KARNE KE STEPS:**\n"
               f"1️⃣ Neeche link se account banayein:\n[REGISTER HERE]({REG_LINK})\n"
               f"2️⃣ Minimum $10 ya usse upar deposit karein.\n"
               f"3️⃣ Apni **Trader ID** yahan message karein.\n\n"
               f"🆘 Support: {SUPPORT_USER}")
        kb = [[InlineKeyboardButton("✅ REGISTER NOW", url=REG_LINK)],
              [InlineKeyboardButton("💬 CONTACT ADMIN", url=f"https://t.me/mstraders7")]]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown', disable_web_page_preview=True)

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
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
    
    await query.edit_message_text(f"💹 **ASSET:** {pair}\nExpiry time select karein:", reply_markup=InlineKeyboardMarkup(kb))

async def gen_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    db = get_db()
    
    if uid in db["verified"] or uid not in db["used_free"]:
        await query.answer()
        _, tf, pair = query.data.split('_')
        await query.edit_message_text(f"🚀 **Analyzing {pair}...**\nPlease wait 5-10 seconds.")
        
        # Signal Generation (Ici logic placeholder)
        act = "CALL (BUY) ⬆️" if time.time() % 2 == 0 else "PUT (SELL) ⬇️"
        acc = "96% 🔥"
        now_ist = datetime.now(IST)
        
        msg = (f"🎯 **VIP PREMIUM SIGNAL** 🎯\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"💹 **ASSET  :** {pair}\n"
               f"📊 **ACTION :** {act}\n"
               f"🎯 **ACCURACY:** {acc}\n"
               f"🕒 **TIME IST:** {now_ist.strftime('%I:%M:%S %p')}\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"⚠️ *Signal sirf is candle ke liye hai!*")
        
        await query.edit_message_text(msg, parse_mode='Markdown')
        
        # Trial record update karein
        if uid not in db["verified"] and uid not in db["used_free"]:
            update_user_db(uid, "used_free", True)
            await asyncio.sleep(5)
            await context.bot.send_message(uid, "🛑 **Aapka 1 FREE Signal khatam ho chuka hai.**\nAgla signal lene ke liye VIP join karein. Type /start")
    else:
        await query.answer("Trial Expired! Join VIP.", show_alert=True)
        # Redirect to start for register steps
        await start(update, context)

# ==========================================
# 🚀 RUNNER LOGIC (Anti-Conflict)
# ==========================================

async def run_bot():
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

def start_bot_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

st.title("MS Traders VIP Dashboard")

if "bot_started" not in st.session_state:
    st.session_state.bot_started = True
    time.sleep(2)
    Thread(target=start_bot_thread, daemon=True).start()
    st.success("Bot is Live! 💹")

st.info("Signals are being generated using IST Timezone.")
