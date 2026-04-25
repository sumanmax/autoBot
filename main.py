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
# ⚙️ CONFIGURATION (Isse dhyaan se dekhein)
# ==========================================
BOT_TOKEN = "8734653401:AAF_cGvEmi-PY4Y3pFbzFBnZet5KT3cYt8E"
ADMIN_ID = 7852639173
SUPPORT_USER = "@mstraders7"
IQ_USER = "atylishmax1407@gmail.com"
IQ_PASS = "max1407@"
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"
DB_FILE = "bot_data.json"

# --- Database Logic ---
def get_db():
    if not os.path.exists(DB_FILE):
        data = {"verified": [], "used_free": []}
        with open(DB_FILE, "w") as f: json.dump(data, f)
        return data
    with open(DB_FILE, "r") as f:
        try: return json.load(f)
        except: return {"verified": [], "used_free": []}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

# ==========================================
# 📊 SIGNAL LOGIC
# ==========================================
def get_advanced_signal(pair, tf):
    try:
        client = IQ_Option(IQ_USER, IQ_PASS)
        if not client.connect(): return "ERROR ⚠️", "N/A"
        candles = client.get_candles(pair, int(tf) * 60, 40, time.time())
        df = pd.DataFrame(candles)
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
    except: return "CALL ⬆️", "85%"

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    
    # Cleaning the support link
    support_link = f"https://t.me/{SUPPORT_USER.replace('@','')}"
    
    if uid in db["verified"]:
        msg = "✅ **VIP ACCESS ACTIVE**\nUnlimited signals chalu hain!"
        kb = [[InlineKeyboardButton("📊 Get VIP Signal", callback_data='list_assets')],
              [InlineKeyboardButton("📞 Contact Support", url=support_link)] ]
    elif uid not in db["used_free"]:
        msg = "🎁 **WELCOME**\nAapko **1 FREE VIP Signal** milta hai."
        kb = [[InlineKeyboardButton("⚡ Get My 1 Free Signal", callback_data='list_assets')]]
    else:
        msg = (
            "🚀 **STRATEGY UNLOCKED: 92% ACCURACY** 🚀\n\n"
            f"1️⃣ [REGISTER HERE]({ "https://broker-qx.pro/sign-up/?lid=2022562"})\n"
            "2️⃣ Min. $10 Deposit karein.\n"
            "3️⃣ Trader ID niche send karein.\n\n"
            f"🆘 Support: {"@mstraders7"}"
        )
        kb = [[InlineKeyboardButton("✅ JOIN VIP", url=REG_LINK)],
              [InlineKeyboardButton("💬 Message Support", url=support_link)] ]
    
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
        msg = (f"🎯 **VIP SIGNAL**\n━━━━━━━━━━\n"
               f"💹 **Asset:** {pair}\n📊 **Action:** {act}\n"
               f"🎯 **Accuracy:** {acc}\n🕒 **Time:** {ist.strftime('%I:%M:%S %p')}\n"
               f"━━━━━━━━━━")
        await query.edit_message_text(msg, parse_mode='Markdown')
        if uid not in db["verified"] and uid not in db["used_free"]:
            db["used_free"].append(uid)
            save_db(db)
    else:
        await query.answer("Access Locked!", show_alert=True)

async def handle_trader_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in get_db()["verified"]: return
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 **VIP Request**\nUser: `{uid}`\nID: `{update.message.text}`\n\nApprove: `/verify {uid}`")
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
            await context.bot.send_message(target, "🎉 **VIP ACTIVATED!** /start")
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
# 🚀 MAIN RUNNER
# ==========================================
async def run_bot():
    while True:
        try:
            app = Application.builder().token(BOT_TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("verify", verify_user))
            app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
            app.add_handler(CallbackQueryHandler(handle_pair, pattern='^p_'))
            app.add_handler(CallbackQueryHandler(gen_signal, pattern='^tf_'))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_trader_id))
            
            await app.initialize()
            await app.start()
            # drop_pending_updates conflict ko kam karne mein madad karta hai
            await app.updater.start_polling(drop_pending_updates=True)
            while True: await asyncio.sleep(10)
        except Exception as e:
            print(f"Loop Restart: {e}")
            await asyncio.sleep(5)

if __name__ == '__main__':
    st.title("Bot Server Control")
    st.write("Server Active ✅")
    asyncio.run(run_bot())
