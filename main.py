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
# IMPORTANT: Make sure this token is 100% correct
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
        return None, f"Auth Error ❌ ({e})"

db_mongo, db_status = get_db_connection()
collection = db_mongo['users'] if db_mongo is not None else None

# ==========================================
# 🤖 BOT LOGIC & HANDLERS
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = collection.find_one({"_id": uid}) if collection else None
    
    is_verified = user.get("is_verified", False) if user else False
    used_free = user.get("used_free", False) if user else False

    if is_verified:
        msg = "👑 **WELCOME VIP MEMBER**\n\nUnlimited signals active hain!"
        kb = [[InlineKeyboardButton("📊 GET PREMIUM SIGNAL", callback_data='list_assets')]]
    elif not used_free:
        msg = "🎁 **WELCOME**\n\nAapko milta hai **1 FREE Trial Signal**.\nClick niche 👇"
        kb = [[InlineKeyboardButton("⚡ START FREE TRIAL", callback_data='list_assets')]]
    else:
        msg = f"🚀 **TRIAL EXPIRED!**\n\nJoin VIP now:\n1️⃣ [Register]({REG_LINK})\n2️⃣ Deposit $10\n3️⃣ Send ID to {SUPPORT_USER}"
        kb = [[InlineKeyboardButton("✅ REGISTER", url=REG_LINK)]]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    assets = ["EURUSD", "GBPUSD", "USDJPY"]
    kb = [[InlineKeyboardButton(f"💹 {a}", callback_data=f'p_{a}')] for a in assets]
    await query.edit_message_text("✨ **SELECT ASSET**", reply_markup=InlineKeyboardMarkup(kb))

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    kb = [[InlineKeyboardButton("⏱ 1 Minute", callback_data=f'tf_{pair}')]]
    await query.edit_message_text(f"💹 Asset: {pair}\nSelect Timeframe:", reply_markup=InlineKeyboardMarkup(kb))

async def gen_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    user = collection.find_one({"_id": uid}) if collection else None
    
    is_verified = user.get("is_verified", False) if user else False
    used_free = user.get("used_free", False) if user else False

    if is_verified or not used_free:
        await query.answer()
        pair = query.data.split('_')[1]
        act = "CALL ⬆️" if time.time() % 2 == 0 else "PUT ⬇️"
        
        await query.edit_message_text(f"🎯 **SIGNAL**\nAsset: {pair}\nAction: {act}\nTime: {datetime.now(IST).strftime('%I:%M %p')}")
        
        if not is_verified and collection:
            collection.update_one({"_id": uid}, {"$set": {"used_free": True}}, upsert=True)
            await context.bot.send_message(uid, "⚠️ Free trial used! Join VIP for more.")
    else:
        await query.answer("Trial Expired!", show_alert=True)

# ==========================================
# 🚀 BOT RUNNER
# ==========================================

def run_telegram_bot():
    # Naya event loop create karna thread ke liye
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
    app.add_handler(CallbackQueryHandler(handle_pair, pattern='^p_'))
    app.add_handler(CallbackQueryHandler(gen_signal, pattern='^tf_'))
    
    print("Bot is polling...")
    app.run_polling(drop_pending_updates=True, close_loop=False)

# --- Streamlit UI ---
st.title("MS Traders VIP Dashboard")
st.write(f"Database: {db_status}")

# Bot ko ek alag thread mein start karna
if "bot_thread" not in st.session_state:
    st.session_state.bot_thread = Thread(target=run_telegram_bot, daemon=True)
    st.session_state.bot_thread.start()
    st.success("Bot is Running! ✅ Check Telegram.")

st.info("Agar bot respond nahi kar raha, toh Streamlit mein 'Reboot App' dabayein.")
