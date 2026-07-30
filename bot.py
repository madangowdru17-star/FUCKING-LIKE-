# MINISTER LIKE TELEGRAM BOT
# POWERED BY : @minister_69
# CHANNEL : @minister_6T9

import os
import asyncio
import aiohttp
import requests
import json
import time
import random
import urllib.parse
import binascii
from collections import defaultdict
from datetime import datetime, timedelta
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import jwt

# ==================== CONFIG ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8752906147:AAF74qHa1BC3NU9eHFHXDotic2NgFd-GSw0")
OWNER_ID = int(os.environ.get("OWNER_ID", "7898928200"))  # Replace with your ID

# Account files
ACCOUNT_FILES = {
    "IND": "account_ind.txt",
    "BR": "account_br.txt",
    "US": "account_br.txt",
    "SAC": "account_br.txt",
    "NA": "account_br.txt",
    "MENA": "account_mena.txt",
    "BD": "account_bd.txt",
    "RU": "account_bd.txt"
}

TOKEN_CACHE = {}
TOKEN_FAILED = set()
liked_cache = defaultdict(set)
user_cooldown = defaultdict(float)

# ==================== ENCRYPTION ====================
def encrypt_message(plaintext):
    key = b'Yg&tc%DEuh6%Zc^8'
    iv = b'6oyZDr22E3ychjM%'
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_message = pad(plaintext, AES.block_size)
    return binascii.hexlify(cipher.encrypt(padded_message)).decode('utf-8')

def create_protobuf_message(user_id, region):
    try:
        import like_pb2
        message = like_pb2.like()
        message.uid = int(user_id)
        message.region = region
        return message.SerializeToString()
    except:
        return None

def create_uid_message(uid):
    try:
        import uid_generator_pb2
        message = uid_generator_pb2.uid_generator()
        message.krishna_ = int(uid)
        message.teamXdarks = 1
        return encrypt_message(message.SerializeToString())
    except:
        return None

def decode_protobuf(binary):
    try:
        import like_count_pb2
        items = like_count_pb2.Info()
        items.ParseFromString(binary)
        return items
    except:
        return None

# ==================== ACCOUNT LOADING ====================
def load_accounts(server_name):
    try:
        filename = ACCOUNT_FILES.get(server_name, "account_ind.txt")
        
        if not os.path.exists(filename):
            filename = "account_ind.txt"
            if not os.path.exists(filename):
                return []
        
        accounts = []
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if ':' in line:
                    parts = line.split(':', 1)
                    uid = parts[0].strip()
                    password = parts[1].strip()
                    
                    if uid and password:
                        accounts.append({"uid": uid, "password": password})
        
        return accounts
    except:
        return []

# ==================== TOKEN GENERATION ====================
async def generate_jwt_token(uid, password):
    try:
        encoded_password = urllib.parse.quote(password)
        url = f"https://ff-jwt-gen-api.lovable.app/api/public/token?uid={uid}&password={encoded_password}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, dict):
                        return data.get('jwt_token') or data.get('token')
                return None
    except:
        return None

async def get_valid_token(uid, password):
    if uid in TOKEN_FAILED:
        return None
        
    if uid in TOKEN_CACHE:
        cached = TOKEN_CACHE[uid]
        remaining = (cached["expires_at"] - datetime.utcnow()).total_seconds()
        if remaining > 1800:
            return cached["token"]

    token = await generate_jwt_token(uid, password)
    if not token:
        TOKEN_FAILED.add(uid)
        return None

    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        TOKEN_CACHE[uid] = {
            "token": token,
            "expires_at": datetime.utcfromtimestamp(exp)
        }
    except:
        TOKEN_CACHE[uid] = {
            "token": token,
            "expires_at": datetime.utcnow() + timedelta(hours=24)
        }

    return token

# ==================== SEND LIKE ====================
async def send_like(encrypted_uid, token, url):
    try:
        edata = bytes.fromhex(encrypted_uid)
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB54"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=edata, headers=headers, timeout=10) as response:
                return response.status == 200
    except:
        return False

def get_player_info(encrypted_uid, server_name, token):
    servers = {
        "IND": "https://client.ind.freefiremobile.com/GetPlayerPersonalShow",
        "BR": "https://client.us.freefiremobile.com/GetPlayerPersonalShow",
        "US": "https://client.us.freefiremobile.com/GetPlayerPersonalShow",
        "SAC": "https://client.us.freefiremobile.com/GetPlayerPersonalShow",
        "NA": "https://client.us.freefiremobile.com/GetPlayerPersonalShow",
        "MENA": "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow",
    }
    url = servers.get(server_name, "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow")

    edata = bytes.fromhex(encrypted_uid)
    headers = {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
        'Authorization': f"Bearer {token}",
        'Content-Type': "application/x-www-form-urlencoded",
        'X-GA': "v1 1",
        'ReleaseVersion': "OB54"
    }

    try:
        response = requests.post(url, data=edata, headers=headers, verify=False, timeout=10)
        return decode_protobuf(response.content)
    except:
        return None

# ==================== MAIN LIKE FUNCTION ====================
async def send_likes_to_target(target_uid, server_name, count, progress_callback=None):
    accounts = load_accounts(server_name)
    if not accounts:
        return {"success": 0, "failed": 0, "total": 0, "error": "No accounts found"}
    
    random.shuffle(accounts)
    
    success_count = 0
    failed_count = 0
    
    # Get server URL
    like_urls = {
        "IND": "https://client.ind.freefiremobile.com/LikeProfile",
        "BR": "https://client.us.freefiremobile.com/LikeProfile",
        "US": "https://client.us.freefiremobile.com/LikeProfile",
        "SAC": "https://client.us.freefiremobile.com/LikeProfile",
        "NA": "https://client.us.freefiremobile.com/LikeProfile",
        "MENA": "https://clientbp.ggpolarbear.com/LikeProfile",
    }
    like_url = like_urls.get(server_name, "https://clientbp.ggpolarbear.com/LikeProfile")
    
    # Prepare encrypted message
    protobuf_message = create_protobuf_message(target_uid, server_name)
    if not protobuf_message:
        return {"success": 0, "failed": 0, "total": 0, "error": "Protobuf creation failed"}
    
    encrypted_uid = encrypt_message(protobuf_message)
    
    # Send likes one by one
    for idx, acc in enumerate(accounts):
        if success_count >= count:
            break
            
        # Progress update
        if progress_callback and idx % 5 == 0:
            await progress_callback(f"🔄 Sending {success_count}/{count} likes...")
        
        # Get token
        token = await get_valid_token(acc['uid'], acc['password'])
        if not token:
            failed_count += 1
            continue
        
        # Send like
        success = await send_like(encrypted_uid, token, like_url)
        
        if success:
            success_count += 1
            liked_cache[target_uid].add(acc['uid'])
        else:
            failed_count += 1
        
        # Random delay to avoid rate limiting
        await asyncio.sleep(0.3 + random.random() * 0.5)
    
    return {
        "success": success_count,
        "failed": failed_count,
        "total": len(accounts)
    }

# ==================== TELEGRAM BOT ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [
            InlineKeyboardButton("📤 Send Likes", callback_data="send_likes"),
            InlineKeyboardButton("📊 Account Status", callback_data="status")
        ],
        [
            InlineKeyboardButton("🔄 Reset Cache", callback_data="reset_cache"),
            InlineKeyboardButton("ℹ️ Help", callback_data="help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Welcome {user.first_name}!\n\n"
        f"🤖 Free Fire Like Bot\n"
        f"📌 Send likes to any Free Fire player\n\n"
        f"Use /like <UID> <SERVER> <COUNT>\n"
        f"Example: /like 123456789 IND 10\n\n"
        f"Servers: IND, BR, US, SAC, NA, MENA, BD, RU",
        reply_markup=reply_markup
    )

async def like_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Cooldown check (10 seconds)
    if user_id in user_cooldown:
        if time.time() - user_cooldown[user_id] < 10:
            await update.message.reply_text("⏳ Please wait 10 seconds between requests!")
            return
    
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "❌ Usage: /like <UID> <SERVER> <COUNT>\n"
            "Example: /like 123456789 IND 10\n\n"
            "📌 Count max: 50 likes per request"
        )
        return
    
    target_uid = args[0]
    server_name = args[1].upper()
    
    try:
        count = int(args[2])
        if count > 50:
            count = 50
            await update.message.reply_text("⚠️ Max 50 likes per request. Using 50.")
        if count < 1:
            count = 1
    except:
        await update.message.reply_text("❌ Count must be a number!")
        return
    
    valid_servers = ["IND", "BR", "US", "SAC", "NA", "MENA", "BD", "RU"]
    if server_name not in valid_servers:
        await update.message.reply_text(f"❌ Invalid server. Use: {', '.join(valid_servers)}")
        return
    
    # Check if accounts exist
    accounts = load_accounts(server_name)
    if not accounts:
        await update.message.reply_text(f"❌ No accounts found for server {server_name}")
        return
    
    # Send initial message
    progress_msg = await update.message.reply_text(
        f"🔄 Starting to send {count} likes to UID: {target_uid}\n"
        f"📡 Server: {server_name}\n"
        f"👥 Total accounts: {len(accounts)}\n\n"
        f"⏳ Processing..."
    )
    
    # Set cooldown
    user_cooldown[user_id] = time.time()
    
    # Get initial likes
    check_uid = create_uid_message(target_uid)
    before_likes = 0
    if check_uid:
        token = await get_valid_token(accounts[0]['uid'], accounts[0]['password'])
        if token:
            player_info = get_player_info(check_uid, server_name, token)
            if player_info:
                try:
                    from google.protobuf.json_format import MessageToJson
                    data = json.loads(MessageToJson(player_info))
                    before_likes = int(data.get('AccountInfo', {}).get('Likes', 0))
                except:
                    pass
    
    # Progress callback
    async def progress_callback(message):
        await progress_msg.edit_text(message)
    
    # Send likes
    result = await send_likes_to_target(target_uid, server_name, count, progress_callback)
    
    # Get after likes
    after_likes = 0
    if check_uid and token:
        player_info = get_player_info(check_uid, server_name, token)
        if player_info:
            try:
                from google.protobuf.json_format import MessageToJson
                data = json.loads(MessageToJson(player_info))
                after_likes = int(data.get('AccountInfo', {}).get('Likes', 0))
            except:
                pass
    
    # Final response
    response = (
        f"✅ <b>Likes Sent Successfully!</b>\n\n"
        f"🎯 Target UID: <code>{target_uid}</code>\n"
        f"📡 Server: {server_name}\n"
        f"❤️ Likes Sent: <b>{result['success']}</b>\n"
        f"❌ Failed: {result['failed']}\n"
        f"👥 Accounts Used: {result['success'] + result['failed']}\n"
        f"📊 Total Accounts: {result['total']}\n"
        f"📈 Before Likes: {before_likes}\n"
        f"📈 After Likes: {after_likes}\n"
        f"📈 Increase: {after_likes - before_likes}\n\n"
        f"💡 Use /like again to send more!"
    )
    
    await progress_msg.edit_text(response, parse_mode="HTML")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_accounts = 0
    status_text = "📊 <b>Account Status</b>\n\n"
    
    for server, filename in ACCOUNT_FILES.items():
        if os.path.exists(filename):
            with open(filename, "r") as f:
                count = sum(1 for line in f if line.strip() and not line.startswith('#'))
            if count > 0:
                status_text += f"✅ {server}: {count} accounts\n"
                total_accounts += count
            else:
                status_text += f"⚠️ {server}: 0 accounts (empty file)\n"
        else:
            status_text += f"❌ {server}: File not found\n"
    
    status_text += f"\n📦 <b>Total: {total_accounts} accounts</b>\n"
    status_text += f"🔑 Cached tokens: {len(TOKEN_CACHE)}\n"
    status_text += f"⚠️ Failed tokens: {len(TOKEN_FAILED)}\n"
    
    await update.message.reply_text(status_text, parse_mode="HTML")

async def reset_cache_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TOKEN_CACHE, TOKEN_FAILED, liked_cache
    TOKEN_CACHE.clear()
    TOKEN_FAILED.clear()
    liked_cache.clear()
    await update.message.reply_text("✅ Cache cleared successfully!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 <b>Free Fire Like Bot Help</b>\n\n"
        "📌 <b>Commands:</b>\n"
        "/start - Start the bot\n"
        "/like <UID> <SERVER> <COUNT> - Send likes\n"
        "/status - Check account status\n"
        "/reset - Reset cache\n"
        "/help - Show this help\n\n"
        "📌 <b>Example:</b>\n"
        "<code>/like 123456789 IND 20</code>\n\n"
        "📌 <b>Servers:</b>\n"
        "IND, BR, US, SAC, NA, MENA, BD, RU\n\n"
        "📌 <b>Limits:</b>\n"
        "• Max 50 likes per request\n"
        "• 10 second cooldown between requests\n\n"
        "💡 <b>Pro Tip:</b> Send likes in batches of 50 for best results!"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "send_likes":
        await query.message.reply_text(
            "📤 Use /like <UID> <SERVER> <COUNT>\n"
            "Example: /like 123456789 IND 10"
        )
    elif query.data == "status":
        await status_command(update, context)
    elif query.data == "reset_cache":
        await reset_cache_command(update, context)
    elif query.data == "help":
        await help_command(update, context)

# ==================== MAIN ====================
def main():
    print("🚀 Starting Free Fire Like Telegram Bot...")
    print("📌 Bot Token: " + BOT_TOKEN[:10] + "...")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("like", like_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("reset", reset_cache_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start bot
    print("✅ Bot started! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()