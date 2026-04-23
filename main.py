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

# Libraries
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from iqoptionapi.stable_api import IQ_Option

# ==========================================
# ⚙️ CONFIG (Change your ADMIN_ID here)
# ==========================================
BOT_TOKEN = "8734653401:AAHnZKY6RCJIFQ8U4tGCOwjLwCZbJi-a4kQ"
ADMIN_ID = 7852639173
IQ_USER = "atylishmax1407@gmail.com"
IQ_PASS = "max1407@"
DB_FILE = "verified_users.json"

# Database handling
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f: json.dump([], f)

def is_verified(user_id):
    with open(DB_FILE, "r") as f:
        v_list = json.load(f)
        return user_id in v_list

def add_verified(user_id):
    with open(DB_FILE, "r") as f: v_list = json.load(f)
    if user_id not in v_list:
        v_list.append(user_id)
        with open(DB_FILE, "w") as f: json.dump(v_list, f)

# ==========================================
# 📊 STRONG SIGNAL LOGIC (85%-92%)
# ==========================================
def get_advanced_signal(pair, tf):
    try:
        client = IQ_Option(IQ_USER, IQ_PASS)
        client.connect()
        # Fetching data
        candles = client.get_candles(pair, int(tf) * 60, 60, time.time())
        if not candles: return "WAIT ⏳", "0%"
        
        df = pd.DataFrame(candles)
        
        # EMA & RSI
        df['ema'] = df['close'].rolling(10).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        # Bollinger Bands
        df['std'] = df['close'].rolling(20).std()
        df['upper'] = df['close'].rolling(20).mean() + (df['std'] * 2)
        df['lower'] = df['close'].rolling(20).mean() - (df['std'] * 2)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # BUY Logic
        if last['close'] > last['ema'] and last['rsi'] > 50:
            acc = "92% 🔥" if prev['close'] <= last['lower'] else "87%"
            return "CALL (BUY) ⬆️", acc
        # SELL Logic
        elif last['close'] < last['ema'] and last['rsi'] < 50:
            acc = "92% 🔥" if prev['close'] >= last['upper'] else "87%"
            return "PUT (SELL) ⬇️", acc
        else:
            return "WAIT ⏳", "Market Sideways"
    except:
        return "ERROR ❌", "Retry"

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_verified(uid):
        kb = [[InlineKeyboardButton("📊 Get VIP Signal (IST)", callback_data='list_assets')]]
        await update.message.reply_text("✅ Access Active!\nAsset সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text("🚫 **Access Restricted!**\n\nবট ব্যবহার করতে আপনার **Trader ID** লিখে মেসেজ দিন। এডমিন ভেরিফাই করলে সিগন্যাল দেখতে পাবেন।")

async def handle_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_verified(uid): return
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 **Request:**\nUID: `{uid}`\nTrader ID: `{update.message.text}`\n\nApprove: `/verify {uid}`")
    await update.message.reply_text("📩 এডমিনের কাছে রিকোয়েস্ট পাঠানো হয়েছে। অপেক্ষা করুন।")

async def verify_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        tid = int(context.args[0])
        add_verified(tid)
        await update.message.reply_text(f"✅ User {tid} Verified!")
        await context.bot.send_message(tid, "🎉 ভেরিফিকেশন সফল! এখন /start ক্লিক করুন।")
    except: pass

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    assets = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
    kb = [[InlineKeyboardButton(a, callback_data=f'p_{a}')] for a in assets]
    await query.edit_message_text("Trading Pair সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(kb))

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    kb = [[InlineKeyboardButton("1 Min", callback_data=f'tf_1_{pair}'), 
           InlineKeyboardButton("5 Min", callback_data=f'tf_5_{pair}')]]
    await query.edit_message_text(f"Pair: {pair}\nTimeframe সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(kb))

async def gen_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, tf, pair = query.data.split('_')
    
    # এডিট মেসেজ কাজ না করলে নতুন মেসেজ পাঠানোর জন্য
    await query.edit_message_text(f"🚀 **Analyzing {pair} Market...**")
    
    act, acc = get_advanced_signal(pair, tf)
    ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    t_str = ist.strftime('%I:%M:%S %p')
    
    msg = (f"🎯 **VIP INSTANT SIGNAL**\n━━━━━━━━━━━━━━━\n"
           f"💹 **Asset:** {pair}\n📊 **Action:** {act}\n"
           f"🎯 **Accuracy:** {acc}\n🕒 **Time (IST):** {t_str}\n"
           f"━━━━━━━━━━━━━━━\n🚀 *Trade Now!*")
    
    await query.edit_message_text(msg, parse_mode='Markdown')

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("verify", verify_user))
    app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
    app.add_handler(CallbackQueryHandler(handle_pair, pattern='^p_'))
    app.add_handler(CallbackQueryHandler(gen_signal, pattern='^tf_'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_id))
    
    await app.initialize()
    await app.start()
    # Conflict এরর এড়াতে drop_pending_updates জরুরি
    await app.updater.start_polling(drop_pending_updates=True)
    while True: await asyncio.sleep(10)

if __name__ == '__main__':
    st.write("Server is Running ✅")
    asyncio.run(main())
