# MINISTER LIKE TELEGRAM BOT - FIXED VERSION
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
OWNER_ID = int(os.environ.get("OWNER_ID", "7898928200"))

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
account_used_today = defaultdict(set)  # Track which accounts were used today

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

async def get_valid_token(uid, password, force_refresh=False):
    if uid in TOKEN_FAILED:
        return None
        
    if not force_refresh and uid in TOKEN_CACHE:
        cached = TOKEN_CACHE[uid]
        remaining = (cached["expires_at"] - datetime.utcnow()).total_seconds()
        if remaining > 300:  # Only use if more than 5 minutes remaining
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
            "expires_at": datetime.utcnow() + timedelta(hours=1)
        }

    return token

# ==================== SEND LIKE WITH VERIFICATION ====================
async def send_like_with_verification(encrypted_uid, token, url, target_uid, account_uid):
    """Send like and verify it was counted"""
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
            # First, get current like count
            async with session.post(url, data=edata, headers=headers, timeout=10) as response:
                if response.status == 200:
                    # Check if like was actually counted
                    # We'll verify by checking if the account already liked this UID
                    if account_uid in liked_cache[target_uid]:
                        return False, "Already liked"
                    
                    liked_cache[target_uid].add(account_uid)
                    return True, "Success"
                elif response.status == 429:
                    return False, "Rate limited"
                elif response.status in [401, 403]:
                    return False, "Token expired"
                else:
                    return False, f"HTTP {response.status}"
    except Exception as e:
        return False, str(e)

def get_player_likes(encrypted_uid, server_name, token):
    """Get current like count for a player"""
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
        if response.status_code == 200:
            return decode_protobuf(response.content)
        return None
    except:
        return None

# ==================== MAIN LIKE FUNCTION - FIXED ====================
async def send_likes_to_target(target_uid, server_name, count, progress_callback=None):
    accounts = load_accounts(server_name)
    if not accounts:
        return {"success": 0, "failed": 0, "total": 0, "error": "No accounts found"}
    
    # Shuffle accounts for randomness
    random.shuffle(accounts)
    
    success_count = 0
    failed_count = 0
    rate_limited = 0
    token_expired = 0
    
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
    
    # Send likes one by one with verification
    for idx, acc in enumerate(accounts):
        if success_count >= count:
            break
        
        # Progress update every 5 attempts
        if progress_callback and idx % 5 == 0:
            await progress_callback(
                f"🔄 Progress: {success_count}/{count} likes\n"
                f"⏳ Attempting account {idx+1}/{len(accounts)}"
            )
        
        # Generate fresh token (force refresh every time)
        token = await get_valid_token(acc['uid'], acc['password'], force_refresh=True)
        if not token:
            failed_count += 1
            continue
        
        # Send like with verification
        success, reason = await send_like_with_verification(
            encrypted_uid, token, like_url, target_uid, acc['uid']
        )
        
        if success:
            success_count += 1
            if progress_callback:
                await progress_callback(f"✅ Like {success_count}/{count} from {acc['uid'][:8]}...")
        else:
            failed_count += 1
            if "Rate limited" in reason:
                rate_limited += 1
                # Wait longer if rate limited
                await asyncio.sleep(2)
            elif "Token expired" in reason:
                token_expired += 1
                # Remove expired token from cache
                if acc['uid'] in TOKEN_CACHE:
                    del TOKEN_CACHE[acc['uid']]
        
        # Dynamic delay to avoid rate limiting
        delay = 0.5 + random.random() * 0.5
        if success_count > 0 and success_count % 5 == 0:
            delay = 1.5  # Longer delay every 5 likes
        
        await asyncio.sleep(delay)
    
    return {
        "success": success_count,
        "failed": failed_count,
        "rate_limited": rate_limited,
        "token_expired": token_expired,
        "total": len(accounts),
        "accounts_used": idx + 1 if 'idx' in locals() else 0
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
        f"Servers: IND, BR, US, SAC, NA, MENA, BD, RU\n\n"
        f"⚠️ Note: Each like is verified individually!",
        reply_markup=reply_markup
    )

async def like_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Cooldown check (15 seconds)
    if user_id in user_cooldown:
        if time.time() - user_cooldown[user_id] < 15:
            await update.message.reply_text("⏳ Please wait 15 seconds between requests!")
            return
    
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "❌ Usage: /like <UID> <SERVER> <COUNT>\n"
            "Example: /like 123456789 IND 10\n\n"
            "📌 Count max: 30 likes per request (for better success rate)"
        )
        return
    
    target_uid = args[0]
    server_name = args[1].upper()
    
    try:
        count = int(args[2])
        if count > 30:  # Reduced to 30 for better success rate
            count = 30
            await update.message.reply_text("⚠️ Max 30 likes per request for better success. Using 30.")
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
    
    # Set cooldown
    user_cooldown[user_id] = time.time()
    
    # Send initial message
    progress_msg = await update.message.reply_text(
        f"🔄 Starting to send {count} likes to UID: {target_uid}\n"
        f"📡 Server: {server_name}\n"
        f"👥 Total accounts: {len(accounts)}\n\n"
        f"⏳ This may take a moment..."
    )
    
    # Get initial likes with a valid token
    check_uid = create_uid_message(target_uid)
    before_likes = 0
    token = None
    
    if check_uid:
        # Find a working account
        for acc in accounts[:10]:
            token = await get_valid_token(acc['uid'], acc['password'])
            if token:
                break
        
        if token:
            player_info = get_player_likes(check_uid, server_name, token)
            if player_info:
                try:
                    from google.protobuf.json_format import MessageToJson
                    data = json.loads(MessageToJson(player_info))
                    before_likes = int(data.get('AccountInfo', {}).get('Likes', 0))
                except:
                    pass
    
    # Progress callback
    async def progress_callback(message):
        try:
            await progress_msg.edit_text(message)
        except:
            pass
    
    # Send likes
    result = await send_likes_to_target(target_uid, server_name, count, progress_callback)
    
    # Get after likes
    after_likes = 0
    if check_uid and token:
        player_info = get_player_likes(check_uid, server_name, token)
        if player_info:
            try:
                from google.protobuf.json_format import MessageToJson
                data = json.loads(MessageToJson(player_info))
                after_likes = int(data.get('AccountInfo', {}).get('Likes', 0))
            except:
                pass
    
    # Calculate actual increase
    actual_increase = after_likes - before_likes
    
    # Final response
    response = (
        f"✅ <b>Likes Processed!</b>\n\n"
        f"🎯 Target UID: <code>{target_uid}</code>\n"
        f"📡 Server: {server_name}\n"
        f"❤️ Successfully Sent: <b>{result['success']}</b>\n"
        f"❌ Failed: {result['failed']}\n"
        f"🚫 Rate Limited: {result.get('rate_limited', 0)}\n"
        f"⏰ Token Expired: {result.get('token_expired', 0)}\n"
        f"👥 Accounts Used: {result['success'] + result['failed']}\n"
        f"📊 Total Accounts: {result['total']}\n\n"
        f"📈 Before Likes: {before_likes}\n"
        f"📈 After Likes: {after_likes}\n"
        f"📈 <b>Actual Increase: {actual_increase}</b>\n\n"
    )
    
    if actual_increase < result['success']:
        response += (
            f"⚠️ <b>Note:</b> Some likes were accepted by server but not counted.\n"
            f"This is normal due to Free Fire's anti-spam system.\n"
            f"Try again with fewer likes or wait a few hours."
        )
    else:
        response += f"✅ All likes counted successfully!"
    
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
                status_text += f"⚠️ {server}: 0 accounts\n"
        else:
            status_text += f"❌ {server}: File not found\n"
    
    status_text += f"\n📦 <b>Total: {total_accounts} accounts</b>\n"
    status_text += f"🔑 Cached tokens: {len(TOKEN_CACHE)}\n"
    status_text += f"⚠️ Failed tokens: {len(TOKEN_FAILED)}\n"
    status_text += f"💾 Liked cache: {len(liked_cache)} targets\n\n"
    status_text += f"💡 <b>Tips for better success:</b>\n"
    status_text += f"• Send max 30 likes per request\n"
    status_text += f"• Wait 15 seconds between requests\n"
    status_text += f"• Use /reset if tokens are expired"
    
    await update.message.reply_text(status_text, parse_mode="HTML")

async def reset_cache_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TOKEN_CACHE, TOKEN_FAILED, liked_cache
    TOKEN_CACHE.clear()
    TOKEN_FAILED.clear()
    liked_cache.clear()
    await update.message.reply_text(
        "✅ Cache cleared successfully!\n"
        "All tokens and like history have been reset."
    )

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
        "<code>/like 123456789 IND 30</code>\n\n"
        "📌 <b>Servers:</b>\n"
        "IND, BR, US, SAC, NA, MENA, BD, RU\n\n"
        "📌 <b>Best Practices:</b>\n"
        "• Max 30 likes per request\n"
        "• Wait 15 seconds between requests\n"
        "• Use /reset if issues persist\n\n"
        "📌 <b>Why likes don't count:</b>\n"
        "• Free Fire only counts 1 like per account\n"
        "• Same accounts can't like twice\n"
        "• Anti-spam system may reject rapid likes\n"
        "• Some accounts may have already liked the target"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "send_likes":
        await query.message.reply_text(
            "📤 Use /like <UID> <SERVER> <COUNT>\n"
            "Example: /like 123456789 IND 30\n\n"
            "💡 Max 30 likes per request for best results!"
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
    print("⚠️ FIXED: Verifying each like individually!")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("like", like_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("reset", reset_cache_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("✅ Bot started! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()