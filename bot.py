from telegram.ext import Application
from config import BOT_TOKEN

from handlers.start import start_handler
from handlers.create import create_handler
from handlers.buttons import button_handler
from handlers.ready import ready_handler
from handlers.answer import answer_handler

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(start_handler)
    app.add_handler(create_handler)
    app.add_handler(button_handler)
    app.add_handler(ready_handler)
    app.add_handler(answer_handler)

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
