import collections
# IQ Option compatibility fix
if not hasattr(collections, 'Iterable'):
    import collections.abc
    collections.Iterable = collections.abc.Iterable

import os
import time
import asyncio
import pandas as pd
import streamlit as st
import pytz
from datetime import datetime, timedelta
from pymongo import MongoClient
from iqoptionapi.stable_api import IQ_Option
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
BOT_TOKEN = "8734653401:AAGWuJrAEV7YTUldr45reN-imN6WtSUnuxE"
ADMIN_ID = 7852639173
SUPPORT_USER = "@mstraders7"
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"
IST = pytz.timezone('Asia/Kolkata')
MONGO_URI = "mongodb+srv://atylishmax1407_db_user:L6T5cl4gztJIaRRs@cluster0.rxd940g.mongodb.net/?appName=Cluster0"

# --- Database Connection ---
client_db = MongoClient(MONGO_URI)
db_col = client_db['trading_bot_db']['bot_data']

def get_db():
    data = db_col.find_one({"_id": "bot_storage"})
    if not data:
        initial = {"_id": "bot_storage", "verified": [], "used_free": []}
        db_col.insert_one(initial)
        return initial
    return data

def save_db(data):
    db_col.replace_one({"_id": "bot_storage"}, data, upsert=True)

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================

# 1. Start Command Logic
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    
    if uid in db["verified"]:
        msg = "✅ VIP ACCESS ACTIVE\nUnlimited premium signals are ready!"
        kb = [[InlineKeyboardButton("📊 Get VIP Signal", callback_data='list_assets')]]
    elif uid not in db["used_free"]:
        msg = "🎁 WELCOME**\nAapko 1 FREE VIP Signal** diya gaya hai.\n\nNiche button par click karke signal lein."
        kb = [[InlineKeyboardButton("⚡ Get Free Signal", callback_data='list_assets')]]
    else:
        # Register Message Logic
        msg = (f"🚀 VIP ACCESS LOCKED\n\nUnlimited signals ke liye niche steps follow karein:\n\n"
               f"1️⃣ Is link se register karein: [CLICK HERE]({"https://broker-qx.pro/sign-up/?lid=2022562"})\n"
               f"2️⃣ Minimum $30 deposit karein.\n"
               f"3️⃣ Apni **Trader ID** yahan niche message mein bhejein.\n\n"
               f"Admin verify karke aapka VIP access chalu kar dega.")
        kb = [[InlineKeyboardButton("✅ REGISTER NOW", url="https://broker-qx.pro/sign-up/?lid=2022562")],
              [InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{"@mstraders7"[1:]}")]]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown', disable_web_page_preview=True)

# 2. Trader ID Handling (Admin Notification)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    db = get_db()

    if uid in db["verified"]:
        await update.message.reply_text("Aapka VIP access pehle se active hai! 📊")
        return

    # Send Trader ID to Admin
    admin_msg = (f"🔔 **NEW VIP REQUEST**\n\n"
                 f"👤 User: {update.effective_user.first_name}\n"
                 f"🆔 Telegram UID: `{uid}`\n"
                 f"📝 Trader ID: `{text}`\n\n"
                 f"Approve karne ke liye click karein:\n`/verify {uid}`")
    
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode='Markdown')
    await update.message.reply_text("📩 Trader ID received!\nAdmin verify kar raha hai, thoda intezar karein.")

# 3. Admin Verify Command
async def verify_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    try:
        target_id = int(context.args[0])
        db = get_db()
        if target_id not in db["verified"]:
            db["verified"].append(target_id)
            save_db(db)
            await update.message.reply_text(f"✅ User `{target_id}` verified successfully!")
            await context.bot.send_message(chat_id=target_id, text="🎉 CONGRATULATIONS!\nAapka VIP access active ho gaya hai. Ab aap unlimited signals le sakte hain! /start")
    except:
        await update.message.reply_text("❌ Format: `/verify [UID]`")

# ==========================================
# 🔄 ASSET & SIGNAL LOGIC (SAME AS BEFORE)
# ==========================================
async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    assets = ["EURUSD", "GBPUSD", "USDJPY", "EURJPY"]
    kb = [[InlineKeyboardButton(f"💹 {a}", callback_data=f'p_{a}')] for a in assets]
    await query.edit_message_text("✨ **SELECT ASSET** ✨", reply_markup=InlineKeyboardMarkup(kb))

# ... (Include handle_timeframe and send_signal from previous code)

# ==========================================
# 🔄 ENGINE
# ==========================================
async def run_bot():
    while True:
        try:
            app = Application.builder().token(BOT_TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("verify", verify_user))
            app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            await app.initialize()
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            while True: await asyncio.sleep(3600)
        except:
            await asyncio.sleep(10)

if __name__ == '__main__':
    st.title("📈 VIP Trading Server")
    if "running" not in st.session_state:
        st.session_state.running = True
        import threading
        threading.Thread(target=lambda: asyncio.run(run_bot()), daemon=True).start()
    st.success("Bot is Live with Registration Logic! ✅")
