import asyncio, aiohttp, html, io, json, logging, os, random, re, string, sys, traceback, fractions, uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import aiofiles
from collections import Counter, defaultdict
import gc, requests
import pymongo
from pymongo.errors import PyMongoError
from sympy.parsing.latex import parse_latex
from bs4 import BeautifulSoup
from motor.motor_asyncio import AsyncIOMotorClient

from pyrogram import Client, filters
from pyrogram.enums import PollType, ChatType
from pyrogram.errors import (
    ChatAdminRequired, FloodWait, InviteHashExpired, InviteHashInvalid,
    UserAlreadyParticipant, UserNotParticipant
)
from pyrogram.types import InlineQueryResultArticle, InlineKeyboardMarkup, InlineKeyboardButton, InputTextMessageContent

from pyrogram.raw.functions.messages import GetPollVotes, GetPollResults
from pyrogram.raw.types import InputPeerChat
from pyrogram.types import (
    Message, User, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQueryResultArticle, InputTextMessageContent
)
from func import clean_html
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import binascii
import base64
import binascii
import time
from bson import ObjectId
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from config import (
    API_ID, API_HASH, BOT_TOKEN, BOT_TOKEN_2,
    MONGO_URI, MONGO_URI_2, MONGO_URIX, DB_NAME,
    OWNER_ID, LOG_GROUP, FORCE_SUB, BOT_GROUP, CHANNEL_ID,
    MASTER_KEY, IV_KEY, FREEMIUM_LIMIT, PREMIUM_LIMIT,
    PAY_API, YT_COOKIES, INSTA_COOKIES, UMODE, FREE_BOT
)

app = Client("quizbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, workers=50)

# ── Database connections ──────────────────────────────────────────────────────
client_db = pymongo.MongoClient(MONGO_URI)
db = client_db[DB_NAME]
users_collection     = db["quiz_users"]
questions_collection = db["questions"]
auth_chats_collection = db["auth_chats"]

mongo_client = pymongo.MongoClient(MONGO_URI_2)
mdb = mongo_client["assignment_bot"]
assignments_collection = mdb["assignments"]
submissions_collection = mdb["submissions"]

cl2_db = pymongo.MongoClient(MONGO_URI_2)
db2 = cl2_db[DB_NAME]
uc_2 = db2["quiz_users"]
qc_2 = db2["questions"]
ac_2 = db2["auth_chats"]

clientX = AsyncIOMotorClient(MONGO_URIX)
dbx = clientX.quiz_bot_db
quizzes_collection = dbx.quizzes
filter_collection  = dbx.user_filters  # kept for compatibility

BOT_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN_2}"

# ── Constants ─────────────────────────────────────────────────────────────────
chatn     = "quiz_zone_new"
PAGE_SIZE = 10

# ── State ─────────────────────────────────────────────────────────────────────
ongoing_edits   = {}
user_quiz_data  = {}
broadcast_active = False
TEMP_ACCESS     = {}

import binascii
MASTER_KEY_HEX = binascii.hexlify(MASTER_KEY.encode() if isinstance(MASTER_KEY, str) else MASTER_KEY).decode()
IV_HEX         = binascii.hexlify(IV_KEY.encode() if isinstance(IV_KEY, str) else IV_KEY).decode()
MASTER_KEY_B   = binascii.unhexlify(MASTER_KEY_HEX)
IV_B           = binascii.unhexlify(IV_HEX.ljust(32, "0"))[:16]

user_quiz_data = {}
broadcast_active = False 

TEMP_ACCESS = {}

MASTER_KEY_HEX = "2e4c5fe382452f9f636b059b4f5cfdfa"
IV_HEX = "4048894e29ea"

MASTER_KEY = binascii.unhexlify(MASTER_KEY_HEX)
IV = binascii.unhexlify(IV_HEX.ljust(32, '0'))[:16]

def encrypt_test_id(test_id: str) -> str:
    cipher = AES.new(MASTER_KEY, AES.MODE_CBC, IV)
    padded_data = pad(test_id.encode(), AES.block_size)
    encrypted = cipher.encrypt(padded_data)
    return base64.urlsafe_b64encode(encrypted).decode()

def decrypt_test_id(encrypted_id: str) -> str:
    MASTER_KEY = binascii.unhexlify(MASTER_KEY_HEX)
    IV = binascii.unhexlify(IV_HEX.ljust(32, '0'))[:16]

    padding_needed = 4 - (len(encrypted_id) % 4)
    if padding_needed and padding_needed != 4:
        encrypted_id += "=" * padding_needed

    cipher = AES.new(MASTER_KEY, AES.MODE_CBC, IV)
    encrypted_data = base64.urlsafe_b64decode(encrypted_id)
    decrypted = unpad(cipher.decrypt(encrypted_data), AES.block_size)
    return decrypted.decode()

FEATURES_TEXT = """> **📢 Features Showcase of Quizbot!** 🚀  

🔹 **Create questions from text** just by providing a ✅ mark to the right options.  
🔹 **Marathon Quiz Mode:** Create unlimited questions for a never-ending challenge.  
🔹 **Convert Polls to Quizzes:** Simply forward polls (e.g., from @quizbot), and unnecessary elements like `[1/100]` will be auto-removed!  
🔹 **Smart Filtering:** Remove unwanted words (e.g., usernames, links) from forwarded polls.  
🔹 **Skip, Pause & Resume** ongoing quizzes anytime.  
🔹 **Bulk Question Support** via ChatGPT output.  
🔹 **Negative Marking** for accurate scoring.  
🔹 **Edit Existing Quizzes** with ease like shuffle title editing timer adding removing questions and many more.  
🔹 **Quiz Analytics:** View engagement, tracking how many users completed the quiz.  
🔹 **Inline Query Support:** Share quizzes instantly via quiz ID.  
🔹 **Free & Paid Quizzes:** Restrict access to selected users/groups—perfect for paid quiz series!  
🔹 **Assignment Management:** Track student responses via bot submissions.  
🔹 **View Creator Info** using the quiz ID.  
🔹 **Generate Beautiful HTML Reports** with score counters, plus light/dark theme support.  
🔹 **Manage Paid Quizzes:** Add/remove users & groups individually or in bulk.  
🔹 **Video Tutorials:** Find detailed guides in the Help section.  
🔹 **Auto-Send Group Results:** No need to copy-paste manually—send all results in one click! 
🔹 **Create Sectional Quiz:** You can create different sections with different timing 🥳.
🔹 **Slow/Fast**: Slow or fast ongoing quiz.
🔹 **OCR Update** - Now extract text from PDFs or Photos
🔹 **Comparison** of Result with accuracy, percentile and percentage
🔹 Create Questions from TXT.
🔹 Advance Mechanism with 99.99% uptime.
🔹 Automated link and username removal from Poll's description and questions.
🔹 Auto txt quiz creation from Wikipedia Britannia bbc news and 20+ articles sites.

> **Latest update 🆕**

🔹 Auto clone from official quizbot.
🔹 Create from polls/already finishrd quizzes in channels and all try /extract.
🔹 Create from Drishti IAS web Quiz try /quiztxt.

> **🚀 Upcoming Features:** 

🔸 Advance Engagement saving + later on perspective.
🔸 More optimizations for a smoother experience.
🔸 Suprising Updates...

> **📊 Live Tracker & Analysis:** 

✅ **Topper Comparisons**  
✅ **Detailed Quiz Performance Analytics**  
"""

def generate_random_id():
    return "GGN" + "".join(random.choices(string.ascii_uppercase + string.digits, k=7))

async def is_paid_user(user_id):
    """Check if user has premium access via the API."""
    try:
        from func import is_premium_user
        return await is_premium_user(user_id)
    except Exception:
        return False

async def remove_baby(text):
    if not text:
        return text

    text = re.sub(r'[\[\(]\s*Q\.?\s*\d+\s*/\s*\d+\s*[\]\)]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\bQ\.?\s*\d+\s*/\s*\d+\)?', '', text, flags=re.IGNORECASE)

    text = re.sub(r'[\[\(]?\s*Q\.?\s*\d+\s*[\]\)]?', '', text, flags=re.IGNORECASE)
    pattern = r"(https?://[^\s]+|t\.me/[^\s]+|@\w+)"
    text = re.sub(pattern, "", text)

    return text.strip()
    

@app.on_message(filters.command("delall") & filters.user(6693636856))  # Owner ID is 1234
async def delete_all_quizzes(client, message: Message):
    result = questions_collection.delete_many({})
    await message.reply(f"✅ Deleted {result.deleted_count} quiz records from the database.")

async def subscribe(app, message):
    if LOG_GROUP:
        try:
          user = await app.get_chat_member(LOG_GROUP, message.from_user.id)
          if str(user.status) == "ChatMemberStatus.BANNED":
              await message.reply_text("You are Banned. Contact -- Team SPY")
              return 1
        except UserNotParticipant:
            caption = f"Join our channel to use the bot"
            await message.reply_photo(photo="https://graph.org/file/d44f024a08ded19452152.jpg",caption=caption, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Now...", url=f"https://t.me/quiz_zone_new")]]))
            return 1
        except Exception:
            await message.reply_text("Something Went Wrong. Contact us Team SPY...")
            return 1

async def send_document_http(chat_id: int, file_id: str, caption: str):
    payload = {
        "chat_id": chat_id,
        "document": file_id,
        "caption": caption
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BOT_API_URL}/sendDocument",
            json=payload
        ) as resp:
            return await resp.json()
            

# ─── /clone COMMAND (PRIVATE ONLY) ──────────────────────────────────────────
@app.on_message(filters.command("clone") & filters.private)
async def clone_quiz(_, message):
    command_parts = message.text.split(maxsplit=1)
    if len(message.command) != 2:
        await message.reply_text("❌ Usage:\n`/clone QUIZID`")
        return

    input_text = command_parts[1].strip()
    quiz_id = input_text.split('=')[-1] if '=' in input_text else input_text
    chat_id = message.chat.id

    status = await message.reply_text("🔍 Searching quiz database...")

    quiz = await quizzes_collection.find_one({"quiz_id": quiz_id})

    if not quiz:
        await status.edit("❌ Quiz not found.")
        return

    caption = (
        f"📘 Quiz Cloned\n"
        f"🆔 {quiz_id}\n"
        f"📊 Questions: {quiz.get('question_count', 'N/A')}"
)
