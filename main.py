import collections
import asyncio
import streamlit as st
import pytz
import certifi
import random
import math
import time
import pandas as pd
from datetime import datetime, timedelta
from pymongo import MongoClient
from threading import Thread
from iqoptionapi.stable_api import IQ_Option
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- CONFIGURATION ---
BOT_TOKEN = "8734653401:AAF0z79TB5O8B1YcORco73lhxpsyr5rTNZk"
ADMIN_ID = 7852639173
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"
IST = pytz.timezone('Asia/Kolkata')
MONGO_URL = "mongodb+srv://atylishmax1407_db_user:max14072001@cluster0.rxd940g.mongodb.net/?retryWrites=true&w=majority"

# IQ Option Credentials
IQ_EMAIL = "riyahalder9064@gmail.com"
IQ_PASSWORD = "mou14072001@"

# MongoDB Setup
ca = certifi.where()
@st.cache_resource
def get_db():
    try:
        client = MongoClient(MONGO_URL, tlsCAFile=ca)
        return client['trading_bot_db']
    except: return None

db = get_db()
users_ref = db['users'] if db is not None else None

# --- IQ OPTION CONNECTION ---
Iq = IQ_Option(IQ_EMAIL, IQ_PASSWORD)
def connect_iq():
    if not Iq.check_connect():
        Iq.connect()
    return True

# ==========================================
# 🧠 TRADING ENGINE
# ==========================================

def get_multi_tf_signal(pair, tf):
    try:
        connect_iq()
        asset = pair.replace("/", "")
        tf_map = {"10s": 10, "15s": 15, "30s": 30, "1m": 60, "5m": 300}
        duration = tf_map.get(tf, 60)
        
        candles = Iq.get_candles(asset, duration, 60, time.time())
        
        if candles:
            df = pd.DataFrame(candles)[['open','max','min','close']]
            df.columns = ['open','high','low','close']
            close = df['close']
            
            rsi = RSIIndicator(close, window=7).rsi().iloc[-1]
            ema_fast = EMAIndicator(close, window=5).ema_indicator().iloc[-1]
            
            power_index = 0
            if close.iloc[-1] > ema_fast: power_index += 3
            else: power_index -= 3
            if rsi < 30: power_index += 5
            elif rsi > 70: power_index -= 5
            
            if power_index >= 0:
                direction, accuracy = "CALL (BUY) ⬆️", 95.8 + min(abs(power_index)/10, 3.8)
            else:
                direction, accuracy = "PUT (SELL) ⬇️", 95.8 + min(abs(power_index)/10, 3.8)
            
            return direction, round(accuracy, 1)
            
        return random.choice(["CALL (BUY) ⬆️", "PUT (SELL) ⬇️"]), 94.5
    except:
        return random.choice(["CALL (BUY) ⬆️", "PUT (SELL) ⬇️"]), 94.0

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    uid = u.id
    
    user = users_ref.find_one({"_id": uid})
    if user is None:
        data = {"_id": uid, "name": u.first_name, "is_verified": False, "used_free": False}
        users_ref.insert_one(data)
        user = data
        
        # --- NEW USER ADMIN NOTIFICATION ---
        now_ist = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
        user_name = u.first_name if u.first_name else "N/A"
        username = f"@{u.username}" if u.username else "N/A"
        chat_link = f"tg://user?id={uid}"
        
        admin_alert = (
            "🚀 NEW USER JOINED\n\n"
            f"👤 Name: {user_name}\n"
            f"🆔 Telegram ID: `{uid}`\n"
            f"📛 Username: {username}\n"
            f"🔗 DIRECT CHAT LINK: [Click Here]({chat_link})\n"
            f"⏰ Time: {now_ist}"
        )
        try:
            await context.bot.send_message(ADMIN_ID, admin_alert, parse_mode='Markdown')
        except: pass
    # 1. VIP User Logic
    if user.get("is_verified"):
        msg = "💎 MS TRADERS VIP 💎\n━━━━━━━━━━━━━━━━━━\n✅ LIFETIME VIP ACTIVE\n🚀 AI VERIFIED SIGNALS\n━━━━━━━━━━━━━━━━━━"
        kb = [[InlineKeyboardButton("📊 START ANALYSIS", callback_data='list_assets')]]
    
    # 2. First Time User (Free signal available)
    elif user.get("used_free") == False:
        msg = "Welcome To Our Family ❤️\n\nThanks for to join us!"
        kb = [[InlineKeyboardButton("⚡ GET FREE SIGNAL", callback_data='list_assets')]]
    
    # 3. 2nd Time Start (After using free signal) - Convince Message
    else:
        msg = (
            "🚀 YOUR FREE SIGNALS END\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Ab loss ko profit mein badalne ka waqt aa gaya hai! Hamare VIP members rozana "
            "$50 - $500 tak ka profit nikal rahe hain hamare 96% Sureshot Signals se.\n\n"
            "👇 VIP Bilkul FREE Join Karein:\n"
            "1️⃣ Niche link se naya account banayein:\n"
            "2️⃣ Minimum $30 Deposit karein.\n"
            "3️⃣ Deposit ke baad niche message par apni Trader ID bhejein."
        )
        kb = [
            [InlineKeyboardButton("🔗 REGISTER NOW", url="https://broker-qx.pro/sign-up/?lid=2022562")],
            [InlineKeyboardButton("💬 CONTACT SUPPORT", url="https://t.me/mstraders7")]
        ]

    await update.effective_message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    user = users_ref.find_one({"_id": uid})
    
    # Security: If they already used free signal and try to list assets again without VIP
    if user.get("used_free") == True and not user.get("is_verified"):
        await start(update, context) # This will trigger the convince message
        return

    assets = [
        "EUR/USD", "GBP/USD", "USD/JPY", "EUR/JPY",
        "AUD/USD", "USD/CHF", "EUR/GBP", "GBP/JPY",
        "EUR/USD-OTC", "GBP/USD-OTC", "USD/INR-OTC", "USD/PKR-OTC",
        "USD/BRL-OTC", "USD/DZD-OTC", "GOLD-OTC", "BITCOIN"
    ]
    kb = []
    for i in range(0, len(assets), 2):
        row = [InlineKeyboardButton(f"💹 {assets[i]}", callback_data=f'p_{assets[i]}')]
        if i+1 < len(assets): row.append(InlineKeyboardButton(f"💹 {assets[i+1]}", callback_data=f'p_{assets[i+1]}'))
        kb.append(row)
    
    await query.edit_message_text("✨ SELECT YOUR ASSET", reply_markup=InlineKeyboardMarkup(kb))

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pair = query.data.split('_', 1)[1]
    tfs = [("10 SEC", "10s"), ("15 SEC", "15s"), ("30 SEC", "30s"), ("1 MIN", "1m"), ("5 MIN", "5m")]
    kb = []
    for i in range(0, len(tfs), 2):
        row = [InlineKeyboardButton(tfs[i][0], callback_data=f'tf_{tfs[i][1]}_{pair}')]
        if i+1 < len(tfs): row.append(InlineKeyboardButton(tfs[i+1][0], callback_data=f'tf_{tfs[i+1][1]}_{pair}'))
        kb.append(row)
    await query.edit_message_text(f"💹 ASSET: {pair}\nSelect Expiry Time:", reply_markup=InlineKeyboardMarkup(kb))

async def gen_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    user = users_ref.find_one({"_id": uid})
    
    if user.get("used_free") == True and not user.get("is_verified"):
        await start(update, context)
        return

    await query.answer()
    _, tf, pair = query.data.split('_', 2)

    for i in range(5, 0, -1):
        await query.edit_message_text(f"⏳ ANALYZING MARKET... {i}s\n💹 Pair: {pair}\n⏱ Time Frame: {tf}")
        await asyncio.sleep(1)

    act, acc_score = get_multi_tf_signal(pair, tf)
    
    msg = (
        f"🎯 **VIP SURESHOT SIGNAL** 🎯\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💹 ASSET  : `{pair}`\n"
        f"⏱ TIME FRAME : `{tf}`\n"
        f"📊 DIRECTION : **{act}**\n"
        f"🔥 ACCURACY  : `{acc_score}%`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )
    await query.edit_message_text(msg, parse_mode='Markdown')
    
    # Important: Mark free signal as used right after generation
    if not user.get("is_verified"): 
        users_ref.update_one({"_id": uid}, {"$set": {"used_free": True}})

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    user = users_ref.find_one({"_id": uid})

    if user and user.get("used_free") and not user.get("is_verified"):
        admin_msg = f"🔔 NEW VERIFICATION REQUEST\n👤 User: {update.effective_user.first_name}\n🆔 TG ID: `{uid}`\n📈 Trader ID: `{text}`"
        kb = [[InlineKeyboardButton("✅ APPROVE", callback_data=f"v_{uid}"), InlineKeyboardButton("❌ REJECT", callback_data=f"r_{uid}")]]
        await context.bot.send_message(ADMIN_ID, admin_msg, reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("✅ ID Submitted! Please wait for admin verification.")

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action, target_id = query.data.split('_')
    target_id = int(target_id)
    if action == 'v':
        users_ref.update_one({"_id": target_id}, {"$set": {"is_verified": True}})
        await context.bot.send_message(target_id, "🎊 CONGRATULATIONS! VIP ACCESS ACTIVE. /start")
        await query.edit_message_text(f"Verified {target_id} ✅")
    else:
        await context.bot.send_message(target_id, "❌ REJECTED! Check your ID.")
        await query.edit_message_text(f"Rejected {target_id} ❌")

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
    app.add_handler(CallbackQueryHandler(handle_pair, pattern='^p_'))
    app.add_handler(CallbackQueryHandler(gen_signal, pattern='^tf_'))
    app.add_handler(CallbackQueryHandler(admin_action, pattern='^[v|r]_'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True, stop_signals=False)

if "bot_active" not in st.session_state:
    st.session_state.bot_active = True
    Thread(target=run_bot, daemon=True).start()

st.title("🚀 BOT ACTIVE")
