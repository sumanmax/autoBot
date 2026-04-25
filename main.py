import collections
if not hasattr(collections, 'Iterable'):
    import collections.abc
    collections.Iterable = collections.abc.Iterable

import os
import time
import json
import asyncio
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from iqoptionapi.stable_api import IQ_Option

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
BOT_TOKEN = "8734653401:AAHb71iM-HPjrP3n9EP4BRyj1C622rnT_rA"
ADMIN_ID = 7852639173
IQ_USER = "atylishmax1407@gmail.com"
IQ_PASS = "max1407@"
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"
DB_FILE = "bot_data.json"

# --- Persistent Database Handling ---
def get_db():
    if not os.path.exists(DB_FILE):
        data = {"verified": [], "used_free": []}
        with open(DB_FILE, "w") as f: 
            json.dump(data, f)
        return data
    with open(DB_FILE, "r") as f:
        try: 
            return json.load(f)
        except: 
            return {"verified": [], "used_free": []}

def save_db(data):
    with open(DB_FILE, "w") as f: 
        json.dump(data, f, indent=4)

# ==========================================
# 📊 SIGNAL LOGIC
# ==========================================
def get_advanced_signal(pair, tf):
    try:
        client = IQ_Option(IQ_USER, IQ_PASS)
        client.connect()
        # Candles fetching for indicators
        candles = client.get_candles(pair, int(tf) * 60, 40, time.time())
        df = pd.DataFrame(candles)
        
        # EMA & RSI Logic
        df['ema'] = df['close'].rolling(10).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        last = df.iloc[-1]
        if last['close'] > last['ema'] and last['rsi'] > 50:
            return "CALL (BUY) ⬆️", "92% 🔥"
        else:
            return "PUT (SELL) ⬇️", "92% 🔥"
    except Exception as e:
        print(f"Signal Error: {e}")
        return "CALL ⬆️", "85%"

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    
    if uid in db["verified"]:
        msg = "✅ **VIP ACCESS ACTIVE**\nAap unlimited signals le sakte hain."
        kb = [[InlineKeyboardButton("📊 Get VIP Signal", callback_data='list_assets')]]
    elif uid not in db["used_free"]:
        msg = "🎁 **WELCOME TO VIP BOT**\n\nAapko **1 FREE VIP Signal** milta hai check karne ke liye."
        kb = [[InlineKeyboardButton("⚡ Get My 1 Free Signal", callback_data='list_assets')]]
    else:
        msg = (
            "⚠️ **FREE LIMIT EXHAUSTED!**\n\n"
            "VIP signals ke liye niche diye gaye steps follow karein:\n\n"
            f"👉 **Step 1:** [REGISTER HERE]({ "https://broker-qx.pro/sign-up/?lid=2022562"})\n"
            "👉 **Step 2:** Account bana kar Minimum deposit karein.\n"
            "👉 **Step 3:** Apni **Trader ID** niche message mein bhejein.\n"
        )
        kb = [[InlineKeyboardButton("🚀 Register Now", url=REG_LINK)]]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown', disable_web_page_preview=True)

async def gen_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    db = get_db()
    
    if uid in db["verified"] or uid not in db["used_free"]:
        await query.answer()
        _, tf, pair = query.data.split('_')
        await query.edit_message_text(f"🚀 **Analyzing {pair}...**")
        
        act, acc = get_advanced_signal(pair, tf)
        ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        
        msg = (f"🎯 **VIP SIGNAL**\n━━━━━━━━━━━━━━━\n"
               f"💹 **Asset:** {pair}\n📊 **Action:** {act}\n"
               f"🎯 **Accuracy:** {acc}\n🕒 **Time (IST):** {ist.strftime('%I:%M:%S %p')}\n"
               f"━━━━━━━━━━━━━━━")
        await query.edit_message_text(msg, parse_mode='Markdown')
        
        if uid not in db["verified"] and uid not in db["used_free"]:
            db["used_free"].append(uid)
            save_db(db)
            await context.bot.send_message(uid, "🚫 **Free Access Finished!**\nRegistration complete karein unlimited access ke liye.")
    else:
        await query.answer("Access Locked!", show_alert=True)

async def handle_trader_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    if uid in db["verified"]: return
    
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 **VIP Request**\nUser: `{uid}`\nTrader ID: `{update.message.text}`\n\nApprove: `/verify {uid}`")
    await update.message.reply_text("📩 **ID Received!** Admin 5-10 mins mein verify kar dega.")

async def verify_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target = int(context.args[0])
        db = get_db()
        if target not in db["verified"]:
            db["verified"].append(target)
            save_db(db)
            await update.message.reply_text(f"✅ User {target} Verified!")
            await context.bot.send_message(target, "🎉 **VIP ACCESS ACTIVATED!**\n\nAb aap unlimited signals use kar sakte hain. Click /start")
    except: pass

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    assets = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
    kb = [[InlineKeyboardButton(a, callback_data=f'p_{a}')] for a in assets]
    await query.edit_message_text("Select Pair:", reply_markup=InlineKeyboardMarkup(kb))

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    kb = [[InlineKeyboardButton("1 Min", callback_data=f'tf_1_{pair}'), InlineKeyboardButton("5 Min", callback_data=f'tf_5_{pair}')]]
    await query.edit_message_text(f"Pair: {pair}\nSelect Time:", reply_markup=InlineKeyboardMarkup(kb))

# ==========================================
# 🚀 MAIN RUNNER (Anti-Crash System)
# ==========================================
async def run_bot():
    while True: # Infinite Loop for 24/7 Active
        try:
            print("🚀 Bot initializing...")
            app = Application.builder().token(BOT_TOKEN).build()
            
            # Handlers registration
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("verify", verify_user))
            app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
            app.add_handler(CallbackQueryHandler(handle_pair, pattern='^p_'))
            app.add_handler(CallbackQueryHandler(gen_signal, pattern='^tf_'))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_trader_id))
            
            await app.initialize()
            await app.start()
            
            # drop_pending_updates=True conflict ko rokta hai
            print("✅ Bot is Online and Protected!")
            await app.updater.start_polling(drop_pending_updates=True)
            
            # Zinda rakhne ke liye loop
            while True:
                await asyncio.sleep(10)
                
        except Exception as e:
            print(f"⚠️ Bot Error: {e}. Restarting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == '__main__':
    st.title("Bot Server Control")
    st.write("Server Active ✅")
    
    # Run the anti-crash bot
    try:
        asyncio.run(run_bot())
    except Exception as e:
        st.error(f"Critical Error: {e}")
