import collections
if not hasattr(collections, 'Iterable'):
    import collections.abc
    collections.Iterable = collections.abc.Iterable

import os
import time
import asyncio
import streamlit as st
import pytz
import certifi
from datetime import datetime
from pymongo import MongoClient
from threading import Thread

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
# Password 'max14072001' ke saath connection string
MONGO_URL = "mongodb+srv://atylishmax1407_db_user:max14072001@cluster0.rxd940g.mongodb.net/?retryWrites=true&w=majority"
ca = certifi.where()

try:
    # Connection logic with SSL and Timeout
    client_db = MongoClient(MONGO_URL, tlsCAFile=ca, serverSelectionTimeoutMS=5000)
    db_mongo = client_db['trading_bot_db']
    collection = db_mongo['users']
    # Connection verify karne ke liye ping
    client_db.admin.command('ping')
    db_status = "Connected ✅"
except Exception as e:
    db_status = "Auth Error ❌ (Check MongoDB Password)"
    collection = None

# ==========================================
# 🛠 DATABASE LOGIC
# ==========================================

def get_user_data(uid):
    if collection is None: return None
    try:
        return collection.find_one({"_id": uid})
    except:
        return None

def update_user_trial(uid):
    if collection is not None:
        try:
            # User ka trial status update karna
            collection.update_one({"_id": uid}, {"$set": {"used_free": True}}, upsert=True)
        except:
            pass

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user_data(uid)
    
    is_verified = user.get("is_verified", False) if user else False
    used_free = user.get("used_free", False) if user else False

    if is_verified:
        msg = "👑 **WELCOME VIP MEMBER**\n\nAapka unlimited access active hai. Niche click karke signals lein."
        kb = [[InlineKeyboardButton("📊 GET PREMIUM SIGNAL", callback_data='list_assets')]]
    elif not used_free:
        msg = (
            "🎁 **WELCOME TO MS TRADERS**\n\n"
            "Aapko milta hai **1 High-Accuracy Trial Signal** bilkul free.\n"
            "Accuracy check karne ke liye niche click karein 👇"
        )
        kb = [[InlineKeyboardButton("⚡ START FREE TRIAL", callback_data='list_assets')]]
    else:
        # Trial expired message with clear instructions
        msg = (
            f"🚀 **YOUR FREE TRIAL EXPIRED!**\n\n"
            f"Ab real profit ka waqt hai! 💰\n\n"
            f"💎 **VIP JOINING STEPS:**\n"
            f"1️⃣ Account banayein: [REGISTER HERE]({REG_LINK})\n"
            f"2️⃣ Minimum $10 deposit karein.\n"
            f"3️⃣ Apni **Trader ID** Admin ko message karein.\n\n"
            f"🆘 Support: {SUPPORT_USER}"
        )
        kb = [
            [InlineKeyboardButton("✅ REGISTER NOW", url=REG_LINK)],
            [InlineKeyboardButton("💬 CONTACT ADMIN", url="https://t.me/mstraders7")]
        ]
    
    await update.message.reply_text(
        msg, 
        reply_markup=InlineKeyboardMarkup(kb), 
        parse_mode='Markdown', 
        disable_web_page_preview=True
    )

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    assets = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURGBP", "USDCAD"]
    kb = [[InlineKeyboardButton(f"💹 {a}", callback_data=f'p_{a}')] for a in assets]
    await query.edit_message_text("✨ **SELECT ASSET PAIR** ✨", reply_markup=InlineKeyboardMarkup(kb))

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    kb = [
        [InlineKeyboardButton("⏱ 1 Minute", callback_data=f'tf_60_{pair}')],
        [InlineKeyboardButton("⏱ 5 Minutes", callback_data=f'tf_300_{pair}')]
    ]
    await query.edit_message_text(f"💹 **ASSET:** {pair}\nSelect Timeframe:", reply_markup=InlineKeyboardMarkup(kb))

async def gen_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    user = get_user_data(uid)
    
    is_verified = user.get("is_verified", False) if user else False
    used_free = user.get("used_free", False) if user else False

    # VIP user ho ya jiska trial bacha ho, wahi signal le sakta hai
    if is_verified or not used_free:
        await query.answer()
        _, tf, pair = query.data.split('_')
        await query.edit_message_text(f"🚀 **Analyzing {pair} Market...**")
        await asyncio.sleep(1.5) # Fake analysis delay
        
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
        
        # Agar trial user hai toh database update karo
        if not is_verified:
            update_user_trial(uid)
            await asyncio.sleep(3)
            await context.bot.send_message(
                uid, 
                "🛑 **Trial Completed!**\n\nAb unlimited signals ke liye VIP join karein. Type /start"
            )
    else:
        await query.answer("Trial Expired! Register for VIP.", show_alert=True)
        # Redirect back to start
        await query.message.reply_text("⚠️ Aapka free trial khatam ho chuka hai. VIP join karein!")

# ==========================================
# 🚀 RUNNER ENGINE
# ==========================================

async def run_bot():
    while True:
        try:
            app = Application.builder().token(BOT_TOKEN).build()
            await app.initialize()
            # Conflicts hatane ke liye webhook delete
            await app.bot.delete_webhook(drop_pending_updates=True)
            
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
            app.add_handler(CallbackQueryHandler(handle_pair, pattern='^p_'))
            app.add_handler(CallbackQueryHandler(gen_signal, pattern='^tf_'))
            
            await app.updater.start_polling(drop_pending_updates=True)
            while True: await asyncio.sleep(3600)
        except Exception as e:
            print(f"Bot Error: {e}")
            await asyncio.sleep(15)

def start_bot_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

# --- Streamlit Frontend ---
st.set_page_config(page_title="MS Traders Bot", page_icon="📈")
st.title("MS Traders VIP Dashboard")
st.markdown("---")
st.write(f"📡 **Database:** {db_status}")

if "bot_started" not in st.session_state:
    st.session_state.bot_started = True
    Thread(target=start_bot_thread, daemon=True).start()
    st.success("Bot Engine Started Successfully! ✅")

st.info("Aapka bot Telegram par background mein chal raha hai. Kisi bhi issue ke liye log check karein.")
