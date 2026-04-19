from pyrogram import Client, filters
from handlers.create import user_data
from utils.states import States

@Client.on_message(filters.text)
async def handle(client, message):
    uid = message.from_user.id

    if uid not in user_data:
        return

    state = user_data[uid]["state"]

    if state == States.TITLE:
        user_data[uid]["title"] = message.text
        user_data[uid]["state"] = States.DESCRIPTION
        await message.reply("Send Description:")

    elif state == States.DESCRIPTION:
        user_data[uid]["desc"] = message.text
        user_data[uid]["questions"] = []
        user_data[uid]["state"] = States.QUESTION
        await message.reply("Send Question:")

    elif state == States.QUESTION:
        user_data[uid]["current"] = {"q": message.text}
        user_data[uid]["state"] = States.OPTIONS
        await message.reply("Send options (comma separated):")

    elif state == States.OPTIONS:
        opts = [x.strip() for x in message.text.split(",")]
        user_data[uid]["current"]["options"] = opts
        user_data[uid]["state"] = States.ANSWER
        await message.reply("Send correct option index (0-based):")

    elif state == States.ANSWER:
        user_data[uid]["current"]["answer"] = int(message.text)
        user_data[uid]["questions"].append(user_data[uid]["current"])

        user_data[uid]["state"] = States.QUESTION
        await message.reply("✅ Added!\nSend next question or /done")
