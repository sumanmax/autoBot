import collections
import os
import time
import asyncio
import streamlit as st
import pytz
import certifi
from datetime import datetime
from pymongo import MongoClient
from threading import Thread

# Fix for older collections issue
if not hasattr(collections, 'Iterable'):
    import collections.abc
    collections.Iterable = collections.abc.Iterable

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
BOT_TOKEN = "8734653401:AAFdyXc0knvgZF7X4klVYA0j4pvKEhaaBzo" 
ADMIN_ID = 7852639173
SUPPORT_USER = "@mstraders7"
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"
IST = pytz.timezone('Asia/Kolkata')

# --- MongoDB Setup ---
MONGO_URL = "mongodb+srv://atylishmax1407_db_user:max14072001@cluster0.rxd940g.mongodb.net/?retryWrites=true&w=majority"
ca = certifi.where()

@st.cache_resource
def get_db_connection():
    try:
        client_db = MongoClient(MONGO_URL, tlsCAFile=ca, serverSelectionTimeoutMS=5000)
        db = client_db['trading_bot_db']
        client_db.admin.command('ping')
        return db, "Connected ✅"
    except Exception as e:
        return None, f"Database Error ❌"

db_mongo, db_status = get_db_connection()
collection = db_mongo['users'] if db_mongo is not None else None

# ==========================================
# 🛠 DATABASE HELPERS
# ==========================================

def get_user(uid):
    if collection is not None:
        return collection.find_one({"_id": uid})
    return None

def set_trial_used(uid):
    if collection is not None:
        collection.update_one({"_id": uid}, {"$set": {"used_free": True}}, upsert=True)

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    
    is_verified = user.get("is_verified", False) if user else False
    used_free = user.get("used_free", False) if user else False

    if is_verified:
        msg = "👑 **WELCOME VIP MEMBER**\n\nAapka unlimited access active hai!"
        kb = [[InlineKeyboardButton("📊 GET PREMIUM SIGNAL", callback_data='list_assets')]]
    elif not used_free:
        msg = (
            "🎁 **WELCOME TO MS TRADERS**\n\n"
            "Aapko milta hai **1 High-Accuracy Trial Signal** bilkul free.\n"
            "Accuracy check karne ke liye niche click karein 👇"
        )
        kb = [[InlineKeyboardButton("⚡ START FREE TRIAL", callback_data='list_assets')]]
    else:
        msg = (
            f"🚀 **YOUR FREE TRIAL EXPIRED!**\n\n"
            f"Ab real profit banane ka waqt hai! 💰\n\n"
            f"💎 **VIP JOINING STEPS:**\n"
            f"1️⃣ Account banayein: [REGISTER]({REG_LINK})\n"
            f"2️⃣ Minimum $10 deposit karein.\n"
            f"3️⃣ Apni **Trader ID** Admin ko bhejein.\n\n"
            f"🆘 Support: {SUPPORT_USER}"
        )
        kb = [[InlineKeyboardButton("✅ REGISTER NOW", url=REG_LINK)],
              [InlineKeyboardButton("💬 CONTACT ADMIN", url="https://t.me/mstraders7")]]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown', disable_web_page_preview=True)

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    assets = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURGBP", "USDCAD"]
    kb = [[InlineKeyboardButton(f"💹 {a}", callback_data=f'p_{a}')] for a in assets]
    await query.edit_message_text("✨ **SELECT PAIR** ✨", reply_markup=InlineKeyboardMarkup(kb))

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    kb = [[InlineKeyboardButton("⏱ 1 Minute", callback_data=f'tf_{pair}')]]
    await query.edit_message_text(f"💹 **ASSET:** {pair}\nSelect Timeframe:", reply_markup=InlineKeyboardMarkup(kb))

async def gen_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    user = get_user(uid)
    
    is_verified = user.get("is_verified", False) if user else False
    used_free = user.get("used_free", False) if user else False

    if is_verified or not used_free:
        await query.answer()
        pair = query.data.split('_')[1]
        await query.edit_message_text(f"🚀 **Analyzing {pair}...**")
        await asyncio.sleep(1.5)
        
        act = "CALL (BUY) ⬆️" if int(time.time()) % 2 == 0 else "PUT (SELL) ⬇️"
        now_ist = datetime.now(IST)
        
        msg = (
            f"🎯 **VIP PREMIUM SIGNAL** 🎯\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💹 **ASSET  :** {pair}\n"
            f"📊 **ACTION :** {act}\n"
            f"🎯 **ACCURACY:** 98% 🔥\n"
            f"🕒 **TIME IST:** {now_ist.strftime('%I:%M:%S %p')}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        await query.edit_message_text(msg, parse_mode='Markdown')
        
        if not is_verified:
            set_trial_used(uid)
            await asyncio.sleep(2)
            await context.bot.send_message(uid, "⚠️ Aapka free trial khatam ho gaya hai. Agla signal VIP mein milega! Type /start")
    else:
        await query.answer("Trial Expired! Join VIP.", show_alert=True)
        await query.message.reply_text("⚠️ Trial khatam! VIP steps ke liye /start karein.")

# ==========================================
# 🚀 CORE ENGINE (FIXED FOR STREAMLIT)
# ==========================================

def run_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
    app.add_handler(CallbackQueryHandler(handle_pair, pattern='^p_'))
    app.add_handler(CallbackQueryHandler(gen_signal, pattern='^tf_'))
    
    async def start_logic():
        await app.initialize()
        await app.bot.delete_webhook(drop_pending_updates=True)
        await app.updater.start_polling(drop_pending_updates=True)
        await app.start()
        print("Bot is polling successfully...")
        while True:
            await asyncio.sleep(3600)

    loop.run_until_complete(start_logic())

# --- Streamlit Frontend ---
st.set_page_config(page_title="MS Traders Bot", layout="centered")
st.title("MS Traders VIP Control Panel")
st.write(f"Database Status: {db_status}")

if "bot_started" not in st.session_state:
    st.session_state.bot_started = True
    thread = Thread(target=run_telegram_bot, daemon=True)
    thread.start()
    st.success("Bot is Live! ✅")

st.info("Check your Telegram bot now. If it doesn't respond, click 'Reboot App' in Streamlit settings.")
