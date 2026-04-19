from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from handlers.create import user_data

@Client.on_message(filters.command("done"))
async def done(client, message):
    buttons = [
        [InlineKeyboardButton("⏱ 10 sec", callback_data="t10")],
        [InlineKeyboardButton("⏱ 20 sec", callback_data="t20")],
        [InlineKeyboardButton("❌ No Shuffle", callback_data="shuffle_off")],
        [InlineKeyboardButton("▶️ Start Quiz", callback_data="start_quiz")]
    ]
    await message.reply("Settings:", reply_markup=InlineKeyboardMarkup(buttons))
