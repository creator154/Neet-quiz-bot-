import os
from telegram.ext import Application

from handlers.start import start_handler
from handlers.create import create_handler
from handlers.quiz import quiz_handler

TOKEN = os.getenv("BOT_TOKEN")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(start_handler)
    app.add_handler(create_handler)
    app.add_handler(quiz_handler)

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
