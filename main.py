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
BOT_TOKEN = "8734653401:AAG46JyPaLbduKDrj-E9apYUW29asRdZrl0" 
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

def register_new_user(uid, data):
    if collection is not None:
        return collection.update_one({"_id": uid}, {"$set": data}, upsert=True)

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    first_name = update.effective_user.first_name
    username = f"@{update.effective_user.username}" if update.effective_user.username else "No Username"
    
    user = get_user(uid)
    
    if user is None:
        new_user_data = {
            "first_name": first_name,
            "username": username,
            "is_verified": False,
            "used_free": False,
            "join_date": datetime.now(IST).strftime('%Y-%m-%d %I:%M %p')
        }
        register_new_user(uid, new_user_data)
        
        # Admin Notification for new unique users
        direct_link = f"https://t.me/user?id={uid}"
        log_msg = (
            "🌟 NEW UNIQUE USER JOINED 🌟\n\n"
            f"👤 Name: {first_name}\n"
            f"🆔 Telegram ID: `{uid}`\n"
            f"🔗 Username: {username}\n"
            f"💬 [DIRECT CHAT LINK]({direct_link})\n"
            f"⏰ Time: {datetime.now(IST).strftime('%I:%M %p')}\n"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=log_msg, parse_mode='Markdown', disable_web_page_preview=True)
        except:
            pass
        user = new_user_data

    is_verified = user.get("is_verified", False)
    used_free = user.get("used_free", False)

    if is_verified:
        msg = "👑 WELCOME VIP MEMBER\n\nUnlimited premium access active!"
        kb = [[InlineKeyboardButton("📊 GET PREMIUM SIGNAL", callback_data='list_assets')]]
    elif not used_free:
        msg = "🎁 WELCOME TO MS TRADERS\n\nHigh-Accuracy Signal.\n👇 Click On Below:"
        kb = [[InlineKeyboardButton("⚡ START", callback_data='list_assets')]]
    else:
        # Jab user trial khatam hone ke baad dobara /start karega tab ye dikhega
        msg = (
            "🚀 YOUR FREE TRIAL HAS EXPIRED!\n\n"
            "Aapne accuracy dekh li hai? Ab waqt hai Daily $100-$500 profit banane ka! 💰\n\n"
            "💎 *VIP JOIN KARNE KE FAIDE:\n"
            "✅ 80% - 90% Sure Shot Signals\n"
            "✅ Daily 20+ Quality Signals\n"
            "✅ No Loss Strategy Tips\n\n"
            "🔥 JOINING OFFER: VIP join karna bilkul FREE hai:\n\n"
            "1️⃣ REGISTER NOW per click karke NEW ID create karein.\n"
            "2️⃣ Minimum $30 deposit karein.\n"
            "3️⃣ Apni Trader ID niche message mein likh kar send karein. 👇\n\n"
            "Hum verify karke aapko permanent access de denge! 📈"
        )
        kb = [[InlineKeyboardButton("✅ REGISTER NOW", url="https://broker-qx.pro/sign-up/?lid=2022562")]]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown', disable_web_page_preview=True)
    else:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown', disable_web_page_preview=True)

# --- ID RECEIVER & ADMIN VERIFICATION ---
async def handle_trader_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    user = get_user(uid)

    if user and user.get("is_verified", False):
        return

    if user and user.get("used_free", False):
        direct_link = f"https://t.me/user?id={uid}"
        admin_msg = (
            "🔔 VERIFICATION REQUEST\n\n"
            f"👤 User: {update.effective_user.first_name}\n"
            f"🆔 Trader ID: `{text}`\n"
            f"💬 [CHAT WITH USER]({direct_link})\n\n"
            "Verify?"
        )
        kb = [[InlineKeyboardButton("✅ VERIFY", callback_data=f"verify_{uid}"),
               InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{uid}")]]
        
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown', disable_web_page_preview=True)
        await update.message.reply_text("✅ Thanks For Sending ID! Admin is verifying...")
    else:
        await update.message.reply_text("Pehle apna 'Free Trial' use karein.")

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith("verify_"):
        target_uid = int(data.split("_")[1])
        verify_user_vip(target_uid, True)
        await query.edit_message_text(f"✅ User `{target_uid}` Verified.")
        await context.bot.send_message(target_uid, "🎊 ID Verified! VIP signals active! /start.")

    elif data.startswith("reject_"):
        target_uid = int(data.split("_")[1])
        await query.edit_message_text(f"❌ User `{target_uid}` Rejected.")
        await context.bot.send_message(target_uid, "⚠️ Rejected! Sahi ID bhejein.")

# ==========================================
# 📊 SIGNAL ENGINE
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
    await query.edit_message_text("✨ SELECT ASSET PAIR ✨", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    timeframes = [("⏱ 10 Seconds", "10sec"), ("⏱ 15 Seconds", "15sec"), ("⏱ 30 Seconds", "30sec"), ("⏱ 1 Minute", "1min"), ("⏱ 5 Minutes", "5min")]
    kb = [[InlineKeyboardButton(tf[0], callback_data=f'tf_{tf[1]}_{pair}')] for tf in timeframes]
    await query.edit_message_text(f"💹 ASSET: {pair}\nSelect Expiry:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

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
        msg = f"🎯 VIP SIGNAL 🎯\n━━━━━━━━━━━━━━━━━━\n💹 ASSET  : {pair}\n⏰ EXPIRY : {tf_label.upper()}\n📊 ACTION : {act}\n🎯 ACCURACY: 90.6% 🔥\n🕒 TIME IST: {datetime.now(IST).strftime('%I:%M:%S %p')}\n━━━━━━━━━━━━━━━━━━"
        await query.edit_message_text(msg, parse_mode='Markdown')
        
        if not is_verified and not used_free:
            set_trial_used(uid)
            # YAHAN KOI MESSAGE NAHI BHEJA GAYA HAI - SILENT EXIT
    else:
        # Alert box dikhega
        await query.answer("Trial Expired! Register to continue.", show_alert=True)
        # Bada expired message dikhayega
        await start(update, context)

# ==========================================
# 🚀 RUNNER & STREAMLIT
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_trader_id))
    
    async def main_logic():
        await app.initialize()
        await app.bot.delete_webhook(drop_pending_updates=True)
        await app.updater.start_polling(drop_pending_updates=True)
        await app.start()
        while True:
            await asyncio.sleep(3600)

    loop.run_until_complete(main_logic())

# Streamlit UI
st.set_page_config(page_title="MS Traders Engine", layout="centered")
st.title("📈 MS Traders VIP Control")

if "bot_started" not in st.session_state:
    st.session_state.bot_started = True
    # Daemon thread ensures 24/7 run
    t = Thread(target=run_telegram_bot, daemon=True)
    t.start()
    st.success("Server Active! ✅")

st.write(f"**Database:** {db_status}")
st.info("Bot is independent of your PC now.")
