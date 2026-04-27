import collections
if not hasattr(collections, 'Iterable'):
    import collections.abc
    collections.Iterable = collections.abc.Iterable

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

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
BOT_TOKEN = "8734653401:AAG5Ng8cG3mLbBxxTq-LQQZ6yZdTO8LLIP8"
ADMIN_ID = 7852639173
SUPPORT_USER = "@mstraders7"
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"
IST = pytz.timezone('Asia/Kolkata')

# --- MongoDB Setup (Password check karein) ---
MONGO_URL = "mongodb+srv://atylishmax1407_db_user:<db_password>@cluster0.rxd940g.mongodb.net/?appName=Cluster0"

try:
    client_db = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    db_mongo = client_db['trading_bot_db']
    collection = db_mongo['users']
    client_db.server_info() # Test connection
except Exception as e:
    st.error(f"Database Connection Error: {e}")

def get_db():
    try:
        verified = []
        used_free = []
        for user in collection.find():
            if user.get("is_verified"): verified.append(user["_id"])
            if user.get("used_free"): used_free.append(user["_id"])
        return {"verified": verified, "used_free": used_free}
    except:
        return {"verified": [], "used_free": []}

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id
        db = get_db()
        
        if uid in db["verified"]:
            msg = "👑 **WELCOME VIP TRADER**\n\nUnlimited signals ready hain!"
            kb = [[InlineKeyboardButton("📊 GET PREMIUM SIGNAL", callback_data='list_assets')]]
        elif uid not in db["used_free"]:
            msg = "🎁 **WELCOME**\nAapko **1 FREE Signal** milta hai.\nNeeche click karein 👇"
            kb = [[InlineKeyboardButton("⚡ GET FREE SIGNAL", callback_data='list_assets')]]
        else:
            msg = f"🚀 **TRIAL EXPIRED!**\n\nVIP join karne ke liye [REGISTER]({REG_LINK}) karein aur ID bhejein."
            kb = [[InlineKeyboardButton("✅ REGISTER", url=REG_LINK)]]
            
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    except Exception as e:
        print(f"Start Error: {e}")

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    assets = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
    kb = [[InlineKeyboardButton(f"💹 {a}", callback_data=f'p_{a}')] for a in assets]
    await query.edit_message_text("✨ **SELECT PAIR** ✨", reply_markup=InlineKeyboardMarkup(kb))

# ==========================================
# 🚀 RUNNER (Fixed Conflict & Crash)
# ==========================================

async def run_bot():
    while True:
        try:
            app = Application.builder().token(BOT_TOKEN).build()
            
            await app.initialize()
            await app.bot.delete_webhook(drop_pending_updates=True)
            
            # Handlers registration
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
            
            await app.start()
            print("Bot is Polling...")
            await app.updater.start_polling(drop_pending_updates=True)
            
            # Keep alive
            while True:
                await asyncio.sleep(10)
                
        except Exception as e:
            print(f"Bot Crashed: {e}. Restarting in 10s...")
            await asyncio.sleep(10)

def start_bot_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

# --- Streamlit UI ---
st.title("MS Traders Bot Control")

if "bot_running" not in st.session_state:
    st.session_state.bot_running = True
    Thread(target=start_bot_thread, daemon=True).start()
    st.success("Bot process initiated! Check Telegram.")

st.write("If bot doesn't reply, check your Terminal/Logs for MongoDB errors.")
