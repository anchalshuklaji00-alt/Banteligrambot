import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telethon import TelegramClient
import requests
import json
import os
import time
from datetime import datetime
import threading
import re
import asyncio
import io
from concurrent.futures import ThreadPoolExecutor

try:
    from keep_alive import keep_alive
except ImportError:
    print("keep_alive module nahi mila. Local PC pe ho toh ignore karo.")
    def keep_alive(): pass

# ==========================================
# ⚙️ 1. CONFIGURATION & TOKENS
# ==========================================
TOKEN = '8612076056:AAEGpfzcl5S0S9_xjBQD9Ps5bfDiC90xQwU'
bot = telebot.TeleBot(TOKEN)

MY_API_BASE_URL = "https://ban-wishlist.vercel.app"
INFO_API_URL    = "https://info-43yp.vercel.app/player-info"

# ==========================================
# ⚙️ 2. FORCE SUBSCRIBE SETUP
# ==========================================
GROUP_USERNAME = "@LikeBotFreeFireMax"
CHANNEL_1      = "@ROLEX857J"
CHANNEL_2      = "@rolexlike"

BOT_1_USERNAME = "@Rolex_KnowInfo_bot"
BOT_1_LINK     = "https://t.me/Rolex_KnowInfo_bot"
BOT_2_USERNAME = "@RolexLike_bot"
BOT_2_LINK     = "https://t.me/RolexLike_bot"

REQUIRED_CHATS = [GROUP_USERNAME, CHANNEL_1, CHANNEL_2]

# ==========================================
# ⚙️ 3. DATABASE FILES
# ==========================================
USER_FILE       = "verified_users.txt"
ALL_USERS_FILE  = "all_users_bot.txt"
LEFT_USERS_FILE = "left_users_log.txt"

for _f in [USER_FILE, ALL_USERS_FILE, LEFT_USERS_FILE]:
    if not os.path.exists(_f):
        open(_f, "w").close()

user_cooldowns   = {}
user_locks       = {}
user_locks_mutex = threading.Lock()
bot_executor     = ThreadPoolExecutor(max_workers=15)

def get_user_lock(user_id):
    with user_locks_mutex:
        if user_id not in user_locks:
            user_locks[user_id] = threading.Lock()
        return user_locks[user_id]

def is_user_verified(user_id):
    with open(USER_FILE, "r") as f:
        return str(user_id) in f.read().splitlines()

def add_verified_user(user_id):
    if not is_user_verified(user_id):
        with open(USER_FILE, "a") as f:
            f.write(f"{user_id}\n")

def remove_verified_user(user_id):
    if is_user_verified(user_id):
        with open(USER_FILE, "r") as f:
            users = f.read().splitlines()
        users.remove(str(user_id))
        with open(USER_FILE, "w") as f:
            f.write("\n".join(users) + "\n")

def log_active_user(user_id):
    with open(ALL_USERS_FILE, "r") as f:
        users = f.read().splitlines()
    if str(user_id) not in users:
        with open(ALL_USERS_FILE, "a") as f:
            f.write(f"{user_id}\n")

def log_left_user(user_id):
    with open(LEFT_USERS_FILE, "a") as f:
        f.write(f"{user_id} left at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ==========================================
# 📦 4. ITEM DATABASE LOADER (5 JSON FILES)
# ==========================================
ITEM_DB = {}

def load_item_database():
    """
    Priority order (baad wali file pehli ko override karti hai):
    1. ItemData.json         — base items (description field)
    2. items-OB50-live.json  — 30k+ named items (name field)
    3. ItemDataOB46.json     — OB46 new items (description field)
    4. ItemDataOB47.json     — OB47 new items (description field)
    5. OB51-Items.json       — OB51 items jo named hain (name field)
    """
    global ITEM_DB

    # --- File 1: ItemData.json
    try:
        with open("ItemData.json", "r", encoding="utf-8") as f:
            for item in json.load(f):
                name = (item.get("description") or "").strip()
                if name and name.lower() not in ("none", "null", ""):
                    ITEM_DB[str(item["itemID"])] = name
        print(f"[DB] ItemData.json       => {len(ITEM_DB)} items so far")
    except Exception as e:
        print(f"[DB] ItemData.json error: {e}")

    # --- File 2: items-OB50-live.json
    try:
        c = 0
        with open("items-OB50-live.json", "r", encoding="utf-8") as f:
            for item in json.load(f):
                name = (item.get("name") or "").strip()
                if name and name.lower() not in ("none", "null", ""):
                    ITEM_DB[str(item["Id"])] = name
                    c += 1
        print(f"[DB] items-OB50-live.json=> {c} named items added | Total: {len(ITEM_DB)}")
    except Exception as e:
        print(f"[DB] items-OB50-live.json error: {e}")

    # --- File 3: ItemDataOB46.json
    try:
        c = 0
        with open("ItemDataOB46.json", "r", encoding="utf-8") as f:
            for item in json.load(f):
                name = (item.get("description") or "").strip()
                if name and name.lower() not in ("none", "null", ""):
                    ITEM_DB[str(item["itemID"])] = name
                    c += 1
        print(f"[DB] ItemDataOB46.json   => {c} items added | Total: {len(ITEM_DB)}")
    except Exception as e:
        print(f"[DB] ItemDataOB46.json error: {e}")

    # --- File 4: ItemDataOB47.json
    try:
        c = 0
        with open("ItemDataOB47.json", "r", encoding="utf-8") as f:
            for item in json.load(f):
                name = (item.get("description") or "").strip()
                if name and name.lower() not in ("none", "null", ""):
                    ITEM_DB[str(item["itemID"])] = name
                    c += 1
        print(f"[DB] ItemDataOB47.json   => {c} items added | Total: {len(ITEM_DB)}")
    except Exception as e:
        print(f"[DB] ItemDataOB47.json error: {e}")

    # --- File 5: OB51-Items.json (sirf named items)
    try:
        c = 0
        with open("OB51-Items.json", "r", encoding="utf-8") as f:
            for item in json.load(f):
                name = (item.get("name") or "").strip()
                if name and name.lower() not in ("none", "null", ""):
                    ITEM_DB[str(item["id"])] = name
                    c += 1
        print(f"[DB] OB51-Items.json     => {c} named items added | Total: {len(ITEM_DB)}")
    except Exception as e:
        print(f"[DB] OB51-Items.json error: {e}")

    print(f"[DB] ✅ MASTER ITEM DATABASE READY: {len(ITEM_DB)} total unique items")

# Bot start hone par load karo
load_item_database()

def get_item_name(item_id):
    """Item ID se name lookup — nahi mila toh ID ke saath unknown return"""
    return ITEM_DB.get(str(item_id), f"Unknown Item (ID: {item_id})")

# ==========================================
# 🛑 5. LEAVE & BLOCK TRACKER
# ==========================================
@bot.message_handler(content_types=['left_chat_member'])
def handle_left_member(message):
    user_id = message.left_chat_member.id
    remove_verified_user(user_id)
    log_left_user(user_id)

@bot.message_handler(content_types=['new_chat_members'])
def handle_new_member(message):
    for member in message.new_chat_members:
        log_active_user(member.id)

@bot.my_chat_member_handler()
def handle_bot_block(message: telebot.types.ChatMemberUpdated):
    if message.new_chat_member.status in ['kicked', 'left']:
        remove_verified_user(message.from_user.id)
        log_left_user(message.from_user.id)

# ==========================================
# ⚙️ 6. USERBOT (sirf /token & /bio2 ke liye)
# ==========================================
API_ID     = 34263972
API_HASH   = 'fd80c37158f3e65b444fa656e0313b18'
TARGET_BOT = '@FFPlayerInfoBot'

ubot      = TelegramClient('rolex_session', API_ID, API_HASH)
ubot_loop = asyncio.new_event_loop()

def start_userbot():
    asyncio.set_event_loop(ubot_loop)
    print("\n" + "="*50)
    print("⏳ ROLEX USERBOT START HO RAHA HAI...")
    print("⚠️  Pehli baar: Number aur OTP dalein!")
    print("="*50 + "\n")
    ubot.start()
    print("🤖 UserBot background mein connect ho gaya!")
    ubot_loop.run_forever()

threading.Thread(target=start_userbot, daemon=True).start()

async def fetch_jwt_from_target_bot(access_token):
    try:
        prev = await ubot.get_messages(TARGET_BOT, limit=1)
        last_id_before = prev[0].id if prev else 0
        await ubot.send_message(TARGET_BOT, f"/access {access_token}")
        await asyncio.sleep(10)
        messages = await ubot.get_messages(TARGET_BOT, limit=5)
        for msg in messages:
            if msg.id <= last_id_before:
                continue
            if msg.text and 'eyJ' in msg.text:
                for line in msg.text.split('\n'):
                    if 'Token:' in line and 'eyJ' in line:
                        return line.split('Token:')[1].replace('*', '').replace('`', '').strip()
        return None
    except Exception as e:
        print(f"[JWT ERROR] {e}")
        return None

def run_jwt_fetch_task(access_token):
    future = asyncio.run_coroutine_threadsafe(fetch_jwt_from_target_bot(access_token), ubot_loop)
    return future.result(timeout=40)

# ==========================================
# 🔒 7. FORCE JOIN & SECURITY
# ==========================================
def check_join_status(user_id):
    not_joined = []
    valid = ['creator', 'administrator', 'member', 'restricted']
    for chat in REQUIRED_CHATS:
        try:
            if bot.get_chat_member(chat, user_id).status not in valid:
                not_joined.append(chat)
        except Exception:
            not_joined.append(chat)
    return not_joined

def send_force_join_msg(message):
    user_id    = message.from_user.id
    first_name = message.from_user.first_name
    markup     = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🌟 JOIN VIP GROUP 🌟",           url=f"https://t.me/{GROUP_USERNAME.replace('@','')}"))
    markup.row(InlineKeyboardButton("📢 Join Channel 1 (@ROLEX857J)", url=f"https://t.me/{CHANNEL_1.replace('@','')}"))
    markup.row(InlineKeyboardButton("📢 Join Channel 2 (@rolexlike)",  url=f"https://t.me/{CHANNEL_2.replace('@','')}"))
    markup.row(InlineKeyboardButton(f"🤖 Start {BOT_1_USERNAME}",      url=BOT_1_LINK))
    markup.row(InlineKeyboardButton(f"🤖 Start {BOT_2_USERNAME}",      url=BOT_2_LINK))
    markup.row(InlineKeyboardButton("🔄 VERIFY KAR — CHECK KARO ✅",  callback_data=f"verify_{user_id}"))
    text = (
        f"🚫 **ACCESS DENIED — {first_name}** 🚫\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "❗ **Bot use karne ke liye pehle yeh karo:**\n\n"
        "1️⃣ **VIP Group join karo**\n"
        "2️⃣ **Dono Channels join karo**\n"
        "3️⃣ **Dono Bots start karo**\n"
        "4️⃣ ✅ **'VERIFY KAR'** button dabao\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Ek baar verify = hamesha ke liye access!*"
    )
    try:
        with open('1.png', 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=text, reply_markup=markup, parse_mode="Markdown")
    except FileNotFoundError:
        bot.reply_to(message, text, reply_markup=markup, parse_mode="Markdown")

def check_security(message):
    """
    ✅ GROUP RESTRICTION HATA DIYA — bot ab har group mein reply dega.
    Sirf force-join check aur 5-sec cooldown.
    """
    user_id = message.from_user.id
    log_active_user(user_id)

    if check_join_status(user_id):
        remove_verified_user(user_id)
        send_force_join_msg(message)
        return False

    current_time = time.time()
    if user_id in user_cooldowns:
        elapsed = current_time - user_cooldowns[user_id]
        if elapsed < 5:
            remaining = int(5 - elapsed)
            bot.reply_to(
                message,
                f"⏳ *Thoda ruk bhai!*\nAgla command *{remaining} second* baad de.\n_(Spam se server slow hota hai!)_",
                parse_mode="Markdown"
            )
            return False
    user_cooldowns[user_id] = current_time
    return True

# Helper: Result text ko done.mp4 ke CAPTION mein daal ke bhejo (ek hi message)
# Agar done.mp4 nahi mila toh sirf text message bhejo
def send_result_with_video(chat_id, result_text):
    try:
        with open('done.mp4', 'rb') as video:
            cap = result_text[:1020] + "..." if len(result_text) > 1024 else result_text
            bot.send_video(chat_id, video, caption=cap, parse_mode="Markdown")
    except FileNotFoundError:
        bot.send_message(chat_id, result_text, parse_mode="Markdown")

# ==========================================
# ✅ VERIFY CALLBACK
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('verify_'))
def verify_callback(call):
    original_user_id = int(call.data.split('_')[1])
    clicker_id       = call.from_user.id

    if clicker_id != original_user_id:
        bot.answer_callback_query(call.id, "❌ Ye button sirf us user ke liye hai jisne start kiya!", show_alert=True)
        return

    not_joined = check_join_status(clicker_id)
    if not not_joined:
        add_verified_user(clicker_id)
        log_active_user(clicker_id)
        bot.answer_callback_query(call.id, "✅ Verified! Ab bot use kar sakte ho!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        success_text = (
            f"🎉 **WELCOME, {call.from_user.first_name}!** 🎉\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ **Verification Complete!**\n"
            "👑 *Rolex VIP System mein swagat hai!*\n\n"
            "📋 **Ab ye commands use kar sakte ho:**\n\n"
            "🔥 `/ban IND 12345678`\n"
            "🏴‍☠️ `/blacklist IND 12345678`\n"
            "❤️ `/checklike IND 12345678`\n"
            "🎒 `/wishlist IND 12345678`\n"
            "✍️ `/bio IND UID JWT NAYA_BIO`\n"
            "⚡ `/bio2 IND UID ACCESS_TOKEN NAYA_BIO`\n"
            "🔑 `/token ACCESS_TOKEN`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 */start ya /help se poori guide dekho!*"
        )
        bot.send_message(call.message.chat.id, success_text, parse_mode='Markdown')
    else:
        missing = ", ".join(not_joined)
        bot.answer_callback_query(
            call.id,
            f"❌ Abhi bhi join nahi kiya:\n{missing}\nSab join karke dobara try karo!",
            show_alert=True
        )

# ==========================================
# 🎮 8. COMMAND: /start & /help
# NOTE: /start HAMESHA 1.png ke saath verify prompt dikhata hai
#       Agar pehle se verified hai toh bhi 1.png saath mein welcome show hoga
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id    = message.from_user.id
    first_name = message.from_user.first_name
    log_active_user(user_id)

    not_joined = check_join_status(user_id)

    # ❌ UNVERIFIED — 1.png + join buttons
    if not_joined:
        remove_verified_user(user_id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🌟 JOIN VIP GROUP 🌟",           url=f"https://t.me/{GROUP_USERNAME.replace('@','')}"))
        markup.row(InlineKeyboardButton("📢 Join Channel 1 (@ROLEX857J)", url=f"https://t.me/{CHANNEL_1.replace('@','')}"))
        markup.row(InlineKeyboardButton("📢 Join Channel 2 (@rolexlike)",  url=f"https://t.me/{CHANNEL_2.replace('@','')}"))
        markup.row(InlineKeyboardButton(f"🤖 Start {BOT_1_USERNAME}",      url=BOT_1_LINK))
        markup.row(InlineKeyboardButton(f"🤖 Start {BOT_2_USERNAME}",      url=BOT_2_LINK))
        markup.row(InlineKeyboardButton("🔄 VERIFY KAR — CHECK KARO ✅",  callback_data=f"verify_{user_id}"))
        verify_text = (
            f"👋 **Namaste, {first_name}!**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🔐 **VERIFICATION REQUIRED**\n\n"
            "Rolex VIP System ek *private tool* hai.\n"
            "Sirf verified members hi use kar sakte hain.\n\n"
            "📋 **Verify hone ke steps:**\n\n"
            "1️⃣ **VIP Group join karo**\n"
            "2️⃣ **Channel 1 & 2 join karo**\n"
            "3️⃣ **Dono Bots start karo** (ek baar /start bhejo)\n"
            "4️⃣ Wapas aakar ✅ **VERIFY KAR** button dabao\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ *Ek baar verify = hamesha ke liye access!*"
        )
        # 1.png HAMESHA bhejo — FileNotFoundError hone par bhi try karo
        sent = False
        try:
            with open('1.png', 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=verify_text, reply_markup=markup, parse_mode="Markdown")
                sent = True
        except FileNotFoundError:
            pass
        if not sent:
            bot.reply_to(message, verify_text, reply_markup=markup, parse_mode="Markdown")
        return

    # ✅ VERIFIED — 1.png ke saath welcome dikhao
    add_verified_user(user_id)
    welcome_text = (
        f"👑 **WELCOME BACK, {first_name}!** 👑\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ *Tum verified ho! Rolex VIP System Ready!* ⚡\n\n"
        "📋 **AVAILABLE COMMANDS:**\n\n"
        "🔥 **BAN CHECK**\n"
        "`/ban IND 987654321`\n\n"
        "🏴‍☠️ **BLACKLIST CHECK**\n"
        "`/blacklist IND 987654321`\n\n"
        "❤️ **LIKES CHECK**\n"
        "`/checklike IND 987654321`\n\n"
        "🎒 **WISHLIST + TXT FILE**\n"
        "`/wishlist IND 987654321`\n\n"
        "✍️ **BIO CHANGE (Direct JWT)**\n"
        "`/bio IND UID JWT_TOKEN NAYA_BIO`\n\n"
        "⚡ **BIO CHANGE (Auto Token)**\n"
        "`/bio2 IND UID ACCESS_TOKEN NAYA_BIO`\n\n"
        "🔑 **JWT TOKEN NIKALO**\n"
        "`/token ACCESS_TOKEN`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Servers: IND | SG | BR | US | ME | SAC | NA*\n"
        "🔰 *Powered by Rolex VIP Engine*"
    )
    # ✅ Verified user pe bhi 1.png bhejo
    sent = False
    try:
        with open('1.png', 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=welcome_text, parse_mode="Markdown")
            sent = True
    except FileNotFoundError:
        pass
    if not sent:
        bot.reply_to(message, welcome_text, parse_mode='Markdown')

# ==========================================
# 🎒 9. COMMAND: /wishlist IND {UID}
# ==========================================
@bot.message_handler(commands=['wishlist'])
def handle_wishlist(message):
    if not check_security(message): return

    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(
            message,
            "❌ **Wrong Format!**\n\n"
            "✅ *Sahi Format:*\n`/wishlist SERVER UID`\n\n"
            "📌 *Example:*\n`/wishlist IND 987654321`\n\n"
            "💡 *Kya milega:*\n"
            "→ Player ke wishlist items ke naam\n"
            "→ Saari items ki TXT file download\n"
            "⏳ *5-10 second lagenge!*",
            parse_mode="Markdown"
        )
        return

    server = args[1].upper()
    uid    = args[2]

    status_msg = bot.reply_to(
        message,
        f"🎒 *Wishlist fetch ho rahi hai...*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **UID:** `{uid}`\n"
        f"🌍 **Server:** `{server}`\n"
        f"⏳ *5-10 second lagenge...*",
        parse_mode="Markdown"
    )

    def _fetch_wishlist():
        try:
            # ✅ API call
            res = requests.get(
                f"{MY_API_BASE_URL}/wishlist",
                params={"uid": uid, "server_name": server},
                timeout=15
            )
            data = res.json()

            # ==========================================
            # API RESPONSE PARSER
            # Exact format:
            # {
            #   "server": "IND", "uid": "...",
            #   "wishlist_data": [
            #     { "field": 1, "nested": [
            #         { "field": 1, "value": 203000105 },  <-- item ID
            #         { "field": 2, "value": 1745094184 }  <-- timestamp
            #       ]
            #     }, ...
            #   ]
            # }
            # ==========================================

            # Error check
            if isinstance(data, dict) and ('error' in data or 'error_message' in data):
                err = data.get('error') or data.get('error_message', 'Unknown error')
                bot.edit_message_text(
                    f"❌ **API Error!**\n`{err}`\n\n"
                    "💡 *UID ya Server check karo aur dobara try karo.*",
                    chat_id=message.chat.id,
                    message_id=status_msg.message_id,
                    parse_mode="Markdown"
                )
                return

            # wishlist_data key se list nikalo
            wishlist_raw = []
            if isinstance(data, dict):
                wishlist_raw = data.get('wishlist_data', [])
                # Fallback: koi bhi list key ho
                if not wishlist_raw:
                    for val in data.values():
                        if isinstance(val, list) and len(val) > 0:
                            wishlist_raw = val
                            break
            elif isinstance(data, list):
                wishlist_raw = data

            if not wishlist_raw:
                bot.edit_message_text(
                    "⚠️ **Wishlist empty hai!**\n\n"
                    "🔎 *Possible reasons:*\n"
                    "• Is player ki wishlist empty hai\n"
                    "• UID galat hai\n"
                    "• Server galat hai (IND/SG/BR?)\n\n"
                    "💡 *UID check karo aur dobara try karo!*",
                    chat_id=message.chat.id,
                    message_id=status_msg.message_id,
                    parse_mode="Markdown"
                )
                return

            # ==========================================
            # ITEM ID EXTRACT + NAME LOOKUP
            # nested[field==1].value = item_id
            # nested[field==2].value = timestamp
            # ==========================================
            wishlist_entries = []
            for entry in wishlist_raw:
                item_id  = None
                add_time = ""

                if isinstance(entry, dict):
                    nested = entry.get('nested', [])
                    if nested:
                        # nested list se field==1 (item_id) aur field==2 (timestamp) nikalo
                        for n in nested:
                            if isinstance(n, dict):
                                f = n.get('field')
                                v = n.get('value')
                                if f == 1 and v:
                                    item_id = str(v)
                                elif f == 2 and v:
                                    add_time = str(v)
                    else:
                        # Fallback: direct dict mein ID key dhundho
                        for id_key in ['itemId', 'item_id', 'id', 'itemID', 'Id', 'ID', 'value']:
                            if id_key in entry:
                                item_id = str(entry[id_key])
                                break
                        for time_key in ['addTime', 'add_time', 'date', 'timestamp']:
                            if time_key in entry and entry[time_key]:
                                add_time = str(entry[time_key])
                                break

                elif isinstance(entry, (int, str)):
                    item_id = str(entry)

                if not item_id:
                    continue

                wishlist_entries.append({
                    "id":       item_id,
                    "name":     get_item_name(item_id),
                    "add_time": add_time
                })

            if not wishlist_entries:
                bot.edit_message_text(
                    "⚠️ **Item IDs parse nahi ho paaye!**\n\n"
                    "💡 *Rolex ko report karo is issue ke baare mein.*",
                    chat_id=message.chat.id,
                    message_id=status_msg.message_id,
                    parse_mode="Markdown"
                )
                return

            # ==========================================
            # TXT FILE BANANA
            # ==========================================
            fetched_at    = datetime.now().strftime("%d %b %Y, %I:%M %p")
            unknown_count = sum(1 for x in wishlist_entries if "Unknown Item" in x["name"])
            known_count   = len(wishlist_entries) - unknown_count

            txt_lines = []
            txt_lines.append("=" * 55)
            txt_lines.append("       ROLEX VIP — FREE FIRE WISHLIST")
            txt_lines.append("=" * 55)
            txt_lines.append(f"  UID     : {uid}")
            txt_lines.append(f"  Server  : {server}")
            txt_lines.append(f"  Total   : {len(wishlist_entries)} items")
            txt_lines.append(f"  Matched : {known_count} / {len(wishlist_entries)} items")
            txt_lines.append(f"  Fetched : {fetched_at}")
            txt_lines.append("=" * 55)
            txt_lines.append("")

            for i, item in enumerate(wishlist_entries, 1):
                txt_lines.append(f"  [{i:>3}]  {item['name']}")
                txt_lines.append(f"         ID   : {item['id']}")
                if item["add_time"]:
                    txt_lines.append(f"         Added: {item['add_time']}")
                txt_lines.append("")

            txt_lines.append("=" * 55)
            txt_lines.append("         Powered by Rolex VIP Engine")
            txt_lines.append("=" * 55)

            txt_content = "\n".join(txt_lines)
            txt_bytes   = io.BytesIO(txt_content.encode("utf-8"))

            # ==========================================
            # VIDEO CAPTION (short — 1024 char limit)
            # ==========================================
            video_caption = (
                f"🎒 **WISHLIST RESULT** 🎒\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **UID:** `{uid}`\n"
                f"🌍 **Server:** `{server}`\n"
                f"📦 **Total Items:** `{len(wishlist_entries)}`\n"
                f"✅ **Matched:** `{known_count}` | ❓ **Unknown:** `{unknown_count}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📄 *Poori wishlist neeche TXT file mein!*\n"
                f"✅ *Extracted by Rolex VIP Engine* ⚡"
            )

            # Delete processing message
            bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)

            # ✅ Result + done.mp4 EK SAATH (video ke caption mein result)
            try:
                with open('done.mp4', 'rb') as video:
                    bot.send_video(
                        message.chat.id,
                        video,
                        caption=video_caption,
                        parse_mode="Markdown"
                    )
            except FileNotFoundError:
                bot.send_message(message.chat.id, video_caption, parse_mode="Markdown")

            # ✅ TXT file bhejo
            bot.send_document(
                message.chat.id,
                txt_bytes,
                visible_file_name=f"{uid}_Rolex_Wishlist.txt",
                caption=(
                    f"📄 **WISHLIST TXT READY!** 📄\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 `{uid}` | 🌍 `{server}`\n"
                    f"📦 **{len(wishlist_entries)} items** | ✅ **{known_count} matched**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"⚡ *Secured by Rolex VIP Engine*"
                ),
                parse_mode="Markdown"
            )

        except requests.exceptions.Timeout:
            bot.edit_message_text(
                "⏳ **Request Timeout!**\n\nServer ne 15 sec mein reply nahi diya.\n💡 *Thodi der baad dobara try karo!*",
                chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown"
            )
        except Exception as e:
            bot.edit_message_text(
                f"❌ **Extraction Error!**\n`{e}`\n\n💡 *Kuch der baad dobara try karo!*",
                chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown"
            )

    bot_executor.submit(_fetch_wishlist)

# ==========================================
# 🎮 10. COMMAND: /checklike
# ==========================================
@bot.message_handler(commands=['checklike'])
def handle_checklike(message):
    if not check_security(message): return
    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(
            message,
            "❌ **Wrong Format!**\n\n"
            "✅ *Sahi Format:*\n`/checklike SERVER UID`\n\n"
            "📌 *Example:*\n`/checklike IND 987654321`\n\n"
            "🌍 *Servers:* IND, SG, BR, US, ME, SAC, NA",
            parse_mode="Markdown"
        )
        return

    status_msg = bot.reply_to(message, "❤️ *Player likes fetch kiye ja rahe hain...*\n_5-8 second lagenge_", parse_mode="Markdown")

    def _fetch_likes():
        try:
            res  = requests.get(INFO_API_URL, params={'region': args[1].upper(), 'uid': args[2]}).json()
            data = None
            if isinstance(res, list) and len(res) > 0:
                data = res[0]
            elif isinstance(res, dict) and "basicInfo" in res:
                data = res

            if data:
                likes  = data.get("basicInfo", {}).get("liked", 0)
                name   = data.get("basicInfo", {}).get("nickname", "Unknown")
                level  = data.get("basicInfo", {}).get("level", "?")
                region = data.get("basicInfo", {}).get("region", args[1].upper())
                text = (
                    "❤️ **LIKES CHECKER — RESULT** ❤️\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 **Player:** `{name}`\n"
                    f"🆔 **UID:** `{args[2]}`\n"
                    f"🌍 **Server:** `{region}`\n"
                    f"🎮 **Level:** `{level}`\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    f"❤️ **Total Likes:** `{likes:,}`\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    "✅ *Checked by Rolex VIP Engine* ⚡"
                )
                bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
                send_result_with_video(message.chat.id, text)
            else:
                bot.edit_message_text(
                    "❌ **Data nahi mila!**\n\n🔎 *Reasons:*\n• UID galat hai\n• Server galat hai\n• API down hai\n\n💡 *Dobara try karo!*",
                    chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown"
                )
        except Exception as e:
            bot.edit_message_text(f"❌ *Server Error:* `{e}`", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

    bot_executor.submit(_fetch_likes)

# ==========================================
# 🎮 11. COMMAND: /ban
# ==========================================
@bot.message_handler(commands=['ban'])
def handle_ban(message):
    if not check_security(message): return
    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(
            message,
            "❌ **Wrong Format!**\n\n"
            "✅ *Sahi Format:*\n`/ban SERVER UID`\n\n"
            "📌 *Example:*\n`/ban IND 987654321`\n\n"
            "🌍 *Servers:* IND, SG, BR, US, ME, SAC, NA",
            parse_mode="Markdown"
        )
        return

    status_msg = bot.reply_to(message, "🔍 *Ban status check kiya ja raha hai...*\n_3-5 second lagenge_", parse_mode="Markdown")

    def _fetch_ban():
        try:
            res = requests.get(f"{MY_API_BASE_URL}/ban", params={"uid": args[2], "server_name": args[1]}).json()
            if 'error' in res:
                bot.edit_message_text(
                    f"❌ **API Error:**\n`{res['error']}`\n\n💡 _UID aur Server check karo._",
                    chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown"
                )
                return
            is_banned   = res.get('is_banned', False)
            status_line = "🔴 **BANNED** _(Account suspend hai)_" if is_banned else "🟢 **ACTIVE** _(Account safe hai)_"
            advice      = "⚠️ _Is account se khelna band karo!_" if is_banned else "✅ _Account bilkul safe hai!_"
            text = (
                "🔥 **ANTI-BAN SCANNER — RESULT** 🔥\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 **Player:** `{res.get('nickname','Unknown')}`\n"
                f"🆔 **UID:** `{res.get('uid', args[2])}`\n"
                f"🌍 **Server:** `{args[1].upper()}`\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ **Status:** {status_line}\n\n"
                f"💬 {advice}\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "✅ *Checked by Rolex VIP Engine* ⚡"
            )
            bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
            send_result_with_video(message.chat.id, text)
        except Exception as e:
            bot.edit_message_text(f"❌ *Connection Error:* `{e}`", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

    bot_executor.submit(_fetch_ban)

# ==========================================
# 🎮 12. COMMAND: /blacklist
# ==========================================
@bot.message_handler(commands=['blacklist'])
def handle_blacklist(message):
    if not check_security(message): return
    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(
            message,
            "❌ **Wrong Format!**\n\n"
            "✅ *Sahi Format:*\n`/blacklist SERVER UID`\n\n"
            "📌 *Example:*\n`/blacklist IND 987654321`\n\n"
            "🌍 *Servers:* IND, SG, BR, US, ME, SAC, NA",
            parse_mode="Markdown"
        )
        return

    status_msg = bot.reply_to(message, "🔍 *Matchmaking blacklist check kiya ja raha hai...*\n_3-5 second lagenge_", parse_mode="Markdown")

    def _fetch_blacklist():
        try:
            res = requests.get(f"{MY_API_BASE_URL}/blacklist", params={"uid": args[2], "server_name": args[1]}).json()
            if 'error' in res:
                bot.edit_message_text(
                    f"❌ **API Error:**\n`{res['error']}`\n\n💡 _UID aur Server check karo._",
                    chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown"
                )
                return
            is_bl   = res.get('is_blacklisted', False)
            bl_line = "🚨 **YES — Hacker Lobby Active**" if is_bl else "✅ **NO — Normal Lobby**"
            advice  = "⚠️ _Is player ke saath mat khelo!_" if is_bl else "✅ _Is player ke saath khelna safe hai._"
            text = (
                "🏴‍☠️ **MATCHMAKING BLACKLIST — RESULT** 🏴‍☠️\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **UID:** `{res.get('uid', args[2])}`\n"
                f"🌍 **Server:** `{args[1].upper()}`\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🕵️ **Blacklisted:** {bl_line}\n\n"
                f"💬 {advice}\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "✅ *Checked by Rolex VIP Engine* ⚡"
            )
            bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
            send_result_with_video(message.chat.id, text)
        except Exception as e:
            bot.edit_message_text(f"❌ *Server Error:* `{e}`", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

    bot_executor.submit(_fetch_blacklist)

# ==========================================
# 🎮 13. COMMAND: /bio (Direct JWT)
# ==========================================
@bot.message_handler(commands=['bio'])
def handle_bio(message):
    if not check_security(message): return
    args = message.text.split(maxsplit=4)
    if len(args) < 5:
        bot.reply_to(
            message,
            "❌ **Wrong Format!**\n\n"
            "✅ *Sahi Format:*\n`/bio SERVER UID JWT_TOKEN NAYA_BIO`\n\n"
            "📌 *Example:*\n`/bio IND 987654321 eyJhbGci... My New Bio`\n\n"
            "💡 *JWT chahiye?* → `/token ACCESS_TOKEN` use karo",
            parse_mode="Markdown"
        )
        return

    server, uid, token, new_bio = args[1], args[2], args[3], args[4]
    status_msg = bot.reply_to(message, "✍️ *Bio change kiya ja raha hai...*\n_3-5 second lagenge_", parse_mode="Markdown")

    def _change_bio():
        try:
            res = requests.get(f"{MY_API_BASE_URL}/update_bio",
                               params={"uid": uid, "server_name": server, "bio": new_bio, "token": token}).json()
            if 'error' in res:
                bot.edit_message_text(
                    f"❌ **Bio Change Failed!**\n`{res['error']}`\n\n💡 *JWT Token expire ho gaya hoga!*",
                    chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown"
                )
                return
            text = (
                "✅ **BIO CHANGE — SUCCESS!** ✅\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **UID:** `{uid}`\n"
                f"🌍 **Server:** `{server.upper()}`\n"
                f"📝 **Naya Bio:** `{new_bio}`\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "🎉 *Bio successfully update ho gaya!*\n"
                "✅ *Powered by Rolex VIP Engine* ⚡"
            )
            bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
            send_result_with_video(message.chat.id, text)
        except Exception as e:
            bot.edit_message_text(f"❌ *Server Error:* `{e}`", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

    bot_executor.submit(_change_bio)

# ==========================================
# 🎮 14. COMMAND: /token
# ==========================================
@bot.message_handler(commands=['token'])
def handle_get_token(message):
    if not check_security(message): return
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(
            message,
            "❌ **Wrong Format!**\n\n"
            "✅ *Sahi Format:*\n`/token ACCESS_TOKEN`\n\n"
            "📌 *Example:*\n`/token abc123def456accesstoken`",
            parse_mode="Markdown"
        )
        return

    status_msg = bot.reply_to(message, "🔐 *JWT Token nikal raha hu...*\n_10-15 second lagenge_", parse_mode="Markdown")

    def _fetch_jwt_only():
        try:
            jwt_token = run_jwt_fetch_task(args[1])
            if jwt_token:
                text = (
                    "🔑 **JWT TOKEN — EXTRACTED!** 🔑\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    f"`{jwt_token}`\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    "💡 *Ab use karo:*\n`/bio IND UID <YE_TOKEN> NAYA_BIO`\n\n"
                    "✅ *Extracted by Rolex VIP Engine* ⚡"
                )
                bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
                send_result_with_video(message.chat.id, text)
            else:
                bot.edit_message_text(
                    "❌ **JWT Token nahi mila!**\n\n🔎 *Reasons:*\n• Access Token expire ho gaya\n• Token invalid hai\n• Target bot ne response nahi diya\n\n💡 *Fresh token se dobara try karo!*",
                    chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown"
                )
        except Exception as e:
            bot.edit_message_text(f"❌ *Server Error:* `{e}`", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

    bot_executor.submit(_fetch_jwt_only)

# ==========================================
# 🎮 15. COMMAND: /bio2 (Auto Token + Bio)
# ==========================================
@bot.message_handler(commands=['bio2'])
def handle_bio2(message):
    if not check_security(message): return
    args = message.text.split(maxsplit=4)
    if len(args) < 5:
        bot.reply_to(
            message,
            "❌ **Wrong Format!**\n\n"
            "✅ *Sahi Format:*\n`/bio2 SERVER UID ACCESS_TOKEN NAYA_BIO`\n\n"
            "📌 *Example:*\n`/bio2 IND 987654321 abc123token Pro Player Rolex`\n\n"
            "💡 *Auto karta hai:*\n1️⃣ JWT nikaalti hai\n2️⃣ Bio change karti hai",
            parse_mode="Markdown"
        )
        return

    server, uid, access_token, new_bio = args[1], args[2], args[3], args[4]
    status_msg = bot.reply_to(message, "⚙️ *Step 1/2: JWT nikal raha hu...*\n_10-12 second lagenge_", parse_mode="Markdown")

    def _change_bio2():
        try:
            jwt_token = run_jwt_fetch_task(access_token)
            if not jwt_token:
                bot.edit_message_text(
                    "❌ **JWT Token fetch failed!**\n\n🔎 *Reasons:*\n• Access Token expire ho gaya\n• Target bot ne response nahi diya\n\n💡 *Fresh access token se dobara try karo!*",
                    chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown"
                )
                return
            bot.edit_message_text(
                "✅ *Step 1/2: JWT mil gaya!*\n⚙️ *Step 2/2: Bio update kar raha hu...*",
                chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown"
            )
            res = requests.get(f"{MY_API_BASE_URL}/update_bio",
                               params={"uid": uid, "server_name": server, "bio": new_bio, "token": jwt_token}).json()
            if 'error' in res:
                bot.edit_message_text(
                    f"❌ **Bio Change Failed!**\n`{res['error']}`",
                    chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown"
                )
                return
            text = (
                "✅ **BIO CHANGE — SUCCESS!** ✅\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **UID:** `{uid}`\n"
                f"🌍 **Server:** `{server.upper()}`\n"
                f"📝 **Naya Bio:** `{new_bio}`\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "⚡ *Auto JWT Engine used*\n"
                "🎉 *Bio successfully update ho gaya!*\n"
                "✅ *Powered by Rolex VIP Engine* ⚡"
            )
            bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
            send_result_with_video(message.chat.id, text)
        except Exception as e:
            bot.edit_message_text(f"❌ *Server Error:* `{e}`", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

    bot_executor.submit(_change_bio2)

# ==========================================
# 🚀 SYSTEM BOOT
# ==========================================
hacker_look_banner = """
\033[1;32m
██████╗  ██████╗ ██╗     ███████╗██╗  ██╗
██╔══██╗██╔═══██╗██║     ██╔════╝╚██╗██╔╝
██████╔╝██║   ██║██║     █████╗   ╚███╔╝ 
██╔══██╗██║   ██║██║     ██╔══╝   ██╔██╗ 
██║  ██║╚██████╔╝███████╗███████╗██╔╝ ██╗
╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝
\033[0m
\033[1;36m[+] ROLEX VIP SYSTEM INITIALIZED\033[0m
\033[1;36m[+] SERVER: ONLINE\033[0m
\033[1;36m[+] MULTI-FORCE JOIN: ACTIVE\033[0m
\033[1;36m[+] WISHLIST ENGINE: LOCAL JSON DB (5 FILES)\033[0m
\033[1;36m[+] GROUP REPLY: ENABLED (ALL GROUPS)\033[0m
\033[1;36m[+] DONE.MP4: ACTIVE ON ALL RESULTS\033[0m
\033[1;36m[+] THREAD POOL: 15 WORKERS\033[0m
"""
print(hacker_look_banner)

keep_alive()
bot.infinity_polling(allowed_updates=telebot.util.update_types)
