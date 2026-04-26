from pyrogram import Client, filters
from pyrogram.types import (
InlineKeyboardMarkup,
InlineKeyboardButton,
ReplyKeyboardMarkup
)

quiz_data = {}

# /create command
@Client.on_message(filters.command("create") & filters.private)
async def create_quiz(client, message):
    uid = message.from_user.id
    quiz_data[uid] = {"step":"title","questions":[]}

    await message.reply(
"""🧠 Let's create a new quiz.

First, send me the title of your quiz.
(e.g. NEET Biology Test)"""
    )


# title
@Client.on_message(filters.private & filters.text & ~filters.command(["create","start"]))
async def quiz_steps(client,message):
    uid=message.from_user.id

    if uid not in quiz_data:
        return

    step=quiz_data[uid]["step"]


    if step=="title":
        quiz_data[uid]["title"]=message.text
        quiz_data[uid]["step"]="description"

        await message.reply(
"""Good.

Now send me a description of your quiz.
Type /skip to skip."""
        )
        return


    if step=="description":
        quiz_data[uid]["description"]=message.text
        quiz_data[uid]["step"]="question"

        await message.reply(
"""Good. Now send me a poll with your first question.

Warning: this bot can't create anonymous polls.""",

reply_markup=ReplyKeyboardMarkup(
[['Create a question']],
resize_keyboard=True
)
        )
        return


# skip description
@Client.on_message(filters.command("skip"))
async def skip_desc(client,message):
    uid=message.from_user.id
    if uid in quiz_data:
        quiz_data[uid]["step"]="question"

        await message.reply(
"""Good. Now send me a poll with your first question.

Warning: this bot can't create anonymous polls.""",

reply_markup=ReplyKeyboardMarkup(
[['Create a question']],
resize_keyboard=True
)
        )


# clicking Create a question
@Client.on_message(filters.regex("Create a question"))
async def create_question(client,message):

    await message.reply(
"""📌 Tap attachment icon ➜ Poll ➜ Quiz

Create your poll question and send it here."""
    )


# receive telegram quiz poll
@Client.on_message(filters.poll)
async def receive_poll(client,message):

    uid=message.from_user.id
    if uid not in quiz_data:
        return

    quiz_data[uid]["questions"].append(message.poll.question)

    await message.reply(
f"✅ Question Added ({len(quiz_data[uid]['questions'])})",

reply_markup=InlineKeyboardMarkup(
[
[
InlineKeyboardButton("➕ Add Question",callback_data="addq"),
InlineKeyboardButton("🔀 Shuffle",callback_data="shuffle")
],
[
InlineKeyboardButton("🏁 Done",callback_data="done")
]
]
)
    )


@Client.on_callback_query(filters.regex("addq"))
async def addq(client,query):

    await query.message.reply(
"Send next Quiz Poll now."
    )



@Client.on_callback_query(filters.regex("shuffle"))
async def shuffle(client,query):
    await query.answer("Questions shuffled ✓",show_alert=True)



@Client.on_callback_query(filters.regex("done"))
async def done(client,query):

    uid=query.from_user.id
    total=len(quiz_data[uid]["questions"])

    await query.message.reply(
f"""✅ Quiz saved successfully

Questions: {total}

Use /start to publish."""
    )
