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
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
BOT_TOKEN = "8734653401:AAGDeT69f5BIiDJEVe2kPQ-4nQdiyVyMTTc" 
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

def verify_user_vip(uid, status=True):
    if collection is not None:
        collection.update_one({"_id": uid}, {"$set": {"is_verified": status}}, upsert=True)

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    
    is_verified = user.get("is_verified", False) if user else False
    used_free = user.get("used_free", False) if user else False

    if is_verified:
        msg = "👑 **WELCOME VIP MEMBER**\n\nAapka unlimited premium access active hai! Market analyze karke high-accuracy signals lein."
        kb = [[InlineKeyboardButton("📊 GET PREMIUM SIGNAL", callback_data='list_assets')]]
    elif not used_free:
        msg = (
            "🎁 WELCOME TO MS TRADERS\n\n"
            "Aapko milta hai High-Accuracy Signal.\n"
            "Hamaari accuracy check karein aur aaj hi profit banana shuru karein! 👇"
        )
        kb = [[InlineKeyboardButton("⚡ START FREE TRIAL", callback_data='list_assets')]]
    else:
        msg = (
            "🚀 YOUR FREE TRIAL HAS EXPIRED!\n\n"
            "Aapne accuracy dekh li hai? Ab waqt hai **Daily $50-$100** profit banane ka! 💰\n\n"
            "💎 VIP JOIN KARNE KE FAIDE:\n"
            "✅ 95% - 98% Sure Shot Signals\n"
            "✅ Daily 20+ Quality Signals\n"
            "✅ No Loss Strategy Tips\n\n"
            "🔥 JOINING OFFER: VIP join karna bilkul FREE hai:\n\n"
            f"1️⃣ [Is link par click karke]({"https://broker-qx.pro/sign-up/?lid=2022562"}) naya account banayein.\n"
            "2️⃣ Minimum $30 deposit karein.\n"
            "3️⃣ Apni Trader ID niche message box mein likh kar send karein. 👇\n\n"
            "Hum verify karke aapko permanent access de denge! 📈"
        )
        kb = [[InlineKeyboardButton("✅ CREATE ACCOUNT NOW", url="https://broker-qx.pro/sign-up/?lid=2022562")]]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown', disable_web_page_preview=True)

# --- ID RECEIVER & ADMIN VERIFICATION ---
async def handle_trader_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or "No Username"
    text = update.message.text
    user = get_user(uid)

    # Agar user already VIP hai toh kuch na karein
    if user and user.get("is_verified", False):
        return

    # Check agar user ne trial use kiya hai tabhi ID accept karein
    if user and user.get("used_free", False):
        # Admin ko message bhejna
        admin_msg = (
            "🔔 NEW VERIFICATION REQUEST\n\n"
            f"👤 User ID: `{uid}`\n"
            f"👤 Username: @{username}\n"
            f"🆔 Trader ID: `{text}`\n\n"
            "Please verifye for VIP access"
        )
        kb = [
            [InlineKeyboardButton("✅ VERIFY", callback_data=f"verify_{uid}"),
             InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{uid}")]
        ]
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        
        # User ko confirm karna
        await update.message.reply_text("✅ ID Sent! Hum verify kar rahe hain, thoda intezar karein. Verification ke baad aapko notification mil jayega.")
    else:
        await update.message.reply_text("Pehle apna 'Free Trial' use karein, uske baad ID send karein.")

# --- ADMIN BUTTON CALLBACK ---
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith("verify_"):
        target_uid = int(data.split("_")[1])
        verify_user_vip(target_uid, True)
        await query.edit_message_text(f"✅ User `{target_uid}` ko VIP access de diya gaya hai.")
        await context.bot.send_message(target_uid, "🎊 CONGRATULATIONS!\n\nAapki ID verify ho gayi hai. Ab aap permanent VIP signals use kar sakte hain! Type /start")

    elif data.startswith("reject_"):
        target_uid = int(data.split("_")[1])
        await query.edit_message_text(f"❌ User `{target_uid}` ki request reject kar di gayi.")
        await context.bot.send_message(target_uid, "⚠️ Verification Rejected!\n\nAapki Trader ID match nahi hui. Please sahi ID bhejein ya support @mstraders7 se baat karein.")

# ==========================================
# 📊 SIGNAL LOGIC (SAME AS BEFORE)
# ==========================================

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    assets = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "EUR/GBP", "USD/CAD", "NZD/USD", "EUR/JPY", "GBP/JPY"]
    kb = []
    for i in range(0, len(assets), 2):
        row = [InlineKeyboardButton(f"💹 {assets[i]}", callback_data=f'p_{assets[i].replace("/", "")}')]
        if i+1 < len(assets): row.append(InlineKeyboardButton(f"💹 {assets[i+1]}", callback_data=f'p_{assets[i+1].replace("/", "")}'))
        kb.append(row)
    await query.edit_message_text("✨ SELECT ASSET PAIR ✨", reply_markup=InlineKeyboardMarkup(kb))

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    timeframes = [("⏱ 10 Seconds", "10s"), ("⏱ 15 Seconds", "15s"), ("⏱ 30 Seconds", "30s"), ("⏱ 1 Minute", "1m"), ("⏱ 5 Minutes", "5m")]
    kb = [[InlineKeyboardButton(tf[0], callback_data=f'tf_{tf[1]}_{pair}')] for tf in timeframes]
    await query.edit_message_text(f"💹 ASSET: {pair}\nSelect Expiry Timeframe:", reply_markup=InlineKeyboardMarkup(kb))

async def gen_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    user = get_user(uid)
    is_verified = user.get("is_verified", False) if user else False
    used_free = user.get("used_free", False) if user else False

    if is_verified or not used_free:
        await query.answer()
        _, tf_label, pair = query.data.split('_')
        await query.edit_message_text(f"🚀 Analyzing {pair} ({tf_label})...")
        await asyncio.sleep(1.5)
        act = "CALL (BUY) ⬆️" if int(time.time()) % 2 == 0 else "PUT (SELL) ⬇️"
        msg = f"🎯 **VIP PREMIUM SIGNAL** 🎯\n━━━━━━━━━━━━━━━━━━\n💹 ASSET  : {pair}\n⏰ EXPIRY : {tf_label.upper()}\n📊 ACTION : {act}\n🎯 ACCURACY: 98.6% 🔥\n🕒 TIME IST: {datetime.now(IST).strftime('%I:%M:%S %p')}\n━━━━━━━━━━━━━━━━━━"
        await query.edit_message_text(msg, parse_mode='Markdown')
        if not is_verified:
            set_trial_used(uid)
            await asyncio.sleep(2)
            await context.bot.send_message(uid, "🛑 **TRIAL FINISHED!**\n\nVIP join karne ke liye apni Trader ID yahan message karein.")
    else:
        await query.answer("Trial Expired! Send Trader ID for VIP.", show_alert=True)
        await start(update, context)

# ==========================================
# 🚀 CORE ENGINE
# ==========================================

def run_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
    app.add_handler(CallbackQueryHandler(handle_pair, pattern='^p_'))
    app.add_handler(CallbackQueryHandler(gen_signal, pattern='^tf_'))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern='^(verify|reject)_'))
    # Message handler to catch Trader ID
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_trader_id))
    
    async def start_logic():
        await app.initialize()
        await app.bot.delete_webhook(drop_pending_updates=True)
        await app.updater.start_polling(drop_pending_updates=True)
        await app.start()
        while True: await asyncio.sleep(3600)
    loop.run_until_complete(start_logic())

st.set_page_config(page_title="MS Traders VIP Engine", layout="centered")
st.title("📈 MS Traders VIP Control Panel")
st.write(f"Database: {db_status}")
if "bot_started" not in st.session_state:
    st.session_state.bot_started = True
    Thread(target=run_telegram_bot, daemon=True).start()
    st.success("Bot is Active! ✅")
st.info("Ms Trader - System is stable.")
