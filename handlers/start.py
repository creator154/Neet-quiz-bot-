from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@Client.on_message(filters.command("start"))
async def start(client, message):
    buttons = [
        [InlineKeyboardButton("➕ Create Quiz", callback_data="create")],
    ]
    await message.reply("Welcome to Quiz Bot", reply_markup=InlineKeyboardMarkup(buttons))
