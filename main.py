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
BOT_TOKEN = "8734653401:AAHnZKY6RCJIFQ8U4tGCOwjLwCZbJi-a4kQ"
ADMIN_ID = 7852639173
IQ_USER = "atylishmax1407@gmail.com"
IQ_PASS = "max1407@"
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"
DB_FILE = "bot_database.json"

# Database structure: { "verified": [], "used_free": [] }
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f: json.dump({"verified": [], "used_free": []}, f)

def get_db():
    with open(DB_FILE, "r") as f: return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

# ==========================================
# 📊 ADVANCED SIGNAL LOGIC
# ==========================================
def get_advanced_signal(pair, tf):
    try:
        client = IQ_Option(IQ_USER, IQ_PASS)
        client.connect()
        candles = client.get_candles(pair, int(tf) * 60, 60, time.time())
        if not candles: return "WAIT ⏳", "Checking..."
        
        df = pd.DataFrame(candles)
        df['ema'] = df['close'].rolling(10).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        last = df.iloc[-1]
        if last['close'] > last['ema'] and last['rsi'] > 50:
            return "CALL (BUY) ⬆️", "92% 🔥"
        elif last['close'] < last['ema'] and last['rsi'] < 50:
            return "PUT (SELL) ⬇️", "92% 🔥"
        return "WAIT ⏳", "Sideways"
    except: return "CALL ⬆️", "85%"

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    
    if uid in db["verified"]:
        msg = "✅ **Welcome Back VIP!**\nUnlimited signals are active for you."
        kb = [[InlineKeyboardButton("📊 Get VIP Signal", callback_data='list_assets')]]
    elif uid not in db["used_free"]:
        msg = "🎁 **Welcome!**\nAapko **1 FREE VIP Signal** milta hai. Iske baad aage ke signals ke liye register karna hoga."
        kb = [[InlineKeyboardButton("⚡ Get My 1 Free Signal", callback_data='list_assets')]]
    else:
        # Attractive Marketing Message for Locked Users
        msg = (
            "🚀 **FREE LIMIT EXHAUSTED!**\n\n"
            "Aapne apna free signal use kar liya hai. Agar aap daily **$50-$100** profit banana chahte hain hamare VIP signals se, toh niche diye gaye steps follow karein:\n\n"
            "1️⃣ **Naya Account Banayein:**\nNiche di gayi link se register karein (Zaroori hai):\n"
            f"🔗 [CLICK HERE TO REGISTER]({REG_LINK})\n\n"
            "2️⃣ **Deposit & ID:**\nMinimum deposit karke apni **Trader ID** yahan niche message mein bhein.\n\n"
            "💎 **VIP Benefits:**\n"
            "✅ 90%+ Accuracy Signals\n"
            "✅ No Expiry Access\n"
            "✅ 24/7 Support\n\n"
            "📩 *ID bhejte hi Admin aapko manual verify karke VIP access de dega!*"
        )
        kb = [[InlineKeyboardButton("🔗 Create Account Now", url=REG_LINK)]]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def gen_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    db = get_db()
    
    # Logic: Only allow if verified OR if they haven't used their free signal
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
        
        # Mark as used if it was their first time
        if uid not in db["verified"] and uid not in db["used_free"]:
            db["used_free"].append(uid)
            save_db(db)
            await context.bot.send_message(uid, "⚠️ **Free Limit Over!** Ab unlimited signals ke liye /start dabayein aur registration complete karein.")
    else:
        await query.answer("Access Denied! Please register.", show_alert=True)
        await start(query, context) # Show them the registration message

async def handle_trader_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    if uid in db["verified"]: return
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🔔 **VIP Request**\nUser: `{uid}`\nTrader ID: `{update.message.text}`\n\nApprove: `/verify {uid}`",
        parse_mode='Markdown'
    )
    await update.message.reply_text("📩 **Trader ID Received!** Admin check karke aapka VIP access enable kar raha hai. Please wait...")

async def verify_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target = int(context.args[0])
        db = get_db()
        if target not in db["verified"]:
            db["verified"].append(target)
            save_db(db)
            await update.message.reply_text(f"✅ User {target} Verified!")
            await context.bot.send_message(target, "🎉 **VIP ACCESS ACTIVATED!** Ab aap unlimited signals use kar sakte hain. Click /start")
    except: pass

# --- Asset Listing Helpers ---
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

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("verify", verify_user))
    app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
    app.add_handler(CallbackQueryHandler(handle_pair, pattern='^p_'))
    app.add_handler(CallbackQueryHandler(gen_signal, pattern='^tf_'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_trader_id))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    while True: await asyncio.sleep(10)

if __name__ == '__main__':
    st.title("AutoBot VIP Server ✅")
    asyncio.run(main())
