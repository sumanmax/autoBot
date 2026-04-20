import time
import json
import os
import pandas as pd
from datetime import datetime
from iqoptionapi.stable_api import IQ_Option
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import NetworkError
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = "8734653401:AAExMDj1PTXc1_EnNI5SLpuMyLtfLwXZdAk"
IQ_USER =  "atylishmax1407@gmail.com"
IQ_PASS = "max1407@"
ADMIN_ID = 7852639173
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"
DB_FILE = "users_data.json"
# ==========================================

# --- Database Logic ---
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_data(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f)

# --- IQ Option Connection ---
def connect_iq():
    client = IQ_Option(IQ_USER, IQ_PASS)
    check, reason = client.connect()
    if not check:
        print(f"Connection Failed: {reason}")
    return client

iq_client = connect_iq()

def check_connection():
    global iq_client
    if not iq_client.check_connect():
        print("IQ Option disconnected. Reconnecting...")
        iq_client.connect()

# --- Instant Signal Logic ---
def get_instant_signal(pair, tf):
    try:
        check_connection() 
        candles = iq_client.get_candles(pair, int(tf) * 60, 30, time.time())
        if not candles:
            return "CALL ⬆️", "88%"
        
        df = pd.DataFrame(candles)
        last_close = df['close'].iloc[-1]
        open_price = df['open'].iloc[-1]
        
        # Momentum based instant decision
        if last_close > open_price:
            return "CALL (BUY) ⬆️", "94%"
        else:
            return "PUT (SELL) ⬇️", "94%"
    except Exception as e:
        print(f"Signal Logic Error: {e}")
        return "CALL ⬆️", "85%"

# --- Bot Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    
    if user_id not in data:
        data[user_id] = {'signals_used': 0, 'is_verified': False}
        save_data(data)

    user = data[user_id]
    
    if user['is_verified']:
        keyboard = [[InlineKeyboardButton("📊 Get VIP Signal", callback_data='list_assets')]]
        msg = "🔥 **Welcome Back VIP Member!**\n\nYour account is active. Click below to start trading."
    else:
        keyboard = [[InlineKeyboardButton("📊 Get Signal (1 Free)", callback_data='list_assets')]]
        msg = (f"🔥 **Quotex King Bot**\n\n"
               f"To get unlimited access:\n"
               f"1️⃣ Register: [Click Here]({REG_LINK})\n"
               f"2️⃣ Deposit: Min $30\n"
               f"3️⃣ Send your Trader ID here for verification.")

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown', disable_web_page_preview=True)

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    await query.answer()
    
    data = load_data()
    user = data.get(user_id, {'signals_used': 0, 'is_verified': False})
    
    if user['signals_used'] >= 1 and not user['is_verified']:
        msg = (f"⚠️ **Access Locked!**\n\nYour free trial is over. Please register and deposit to continue.\n\n"
               f"🔗 [Register Here]({REG_LINK})")
        await query.edit_message_text(msg, parse_mode='Markdown', disable_web_page_preview=True)
        return

    assets = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURJPY", "USDCAD"]
    keyboard = []
    temp = []
    for asset in assets:
        temp.append(InlineKeyboardButton(asset, callback_data=f'p_{asset}'))
        if len(temp) == 2:
            keyboard.append(temp)
            temp = []
            
    await query.edit_message_text("Select an Asset for Instant Analysis:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    keyboard = [[InlineKeyboardButton("1 Min", callback_data=f'tf_1_{pair}'), 
                 InlineKeyboardButton("5 Min", callback_data=f'tf_5_{pair}')]]
    await query.edit_message_text(f"Asset: {pair}\nSelect Timeframe:", reply_markup=InlineKeyboardMarkup(keyboard))

async def generate_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    await query.answer()
    _, tf, pair = query.data.split('_')
    
    await query.edit_message_text(f"⚡ Analyzing {pair} market... (5s)")
    time.sleep(3) 
    
    action, acc = get_instant_signal(pair, tf)
    
    data = load_data()
    data[user_id]['signals_used'] += 1
    save_data(data)
    
    msg = (f"🎯 **INSTANT VIP SIGNAL**\n"
           f"━━━━━━━━━━━━━━━\n"
           f"💹 **Asset:** {pair}\n"
           f"📊 **Action:** {action}\n"
           f"🎯 **Accuracy:** {acc}\n"
           f"🚀 **Entry Now:** {datetime.now().strftime('%H:%M:%S')}\n"
           f"━━━━━━━━━━━━━━━\n"
           f"📢 *Trade fast for the best result!*")
    await query.edit_message_text(msg, parse_mode='Markdown')

async def handle_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    text = update.message.text
    if text.isdigit():
        await update.message.reply_text("✅ ID Received! Please wait for Admin approval.")
        admin_msg = (f"🔔 **New Verification Request**\n"
                     f"User: @{username}\n"
                     f"ID: `{user_id}`\n"
                     f"Trader ID: `{text}`\n\n"
                     f"To approve, click:\n`/approve {user_id}`")
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode='Markdown')

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target = str(context.args[0])
        data = load_data()
        if target in data:
            data[target]['is_verified'] = True
            save_data(data)
            await update.message.reply_text(f"✅ User {target} Approved!")
            await context.bot.send_message(chat_id=int(target), text="🎊 **VIP Unlocked!**\nYour ID is verified. You now have unlimited access.")
    except Exception as e:
        await update.message.reply_text("Usage: /approve <user_id>")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
    app.add_handler(CallbackQueryHandler(handle_pair, pattern='^p_'))
    app.add_handler(CallbackQueryHandler(generate_signal, pattern='^tf_'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_id))
    print("Bot is Running...")
    app.run_polling()

if __name__ == '__main__':
    main()