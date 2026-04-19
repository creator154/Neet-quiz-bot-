from pyrogram import Client
from config import *

app = Client(
    "quizbot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

import handlers.start
import handlers.create
import handlers.question
import handlers.settings
import handlers.launch

app.run()
