import logging, json, random
from telegram import *
from telegram.ext import *
from sqlalchemy import *
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()
engine = create_engine('sqlite:///quiz.db')
Session = sessionmaker(bind=engine)

# ───── DB ─────
class Quiz(Base):
    __tablename__ = 'quiz'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    questions = relationship("Question", back_populates="quiz")

class Question(Base):
    __tablename__ = 'question'
    id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey('quiz.id'))
    text = Column(String)
    options = Column(String)
    correct = Column(Integer)
    quiz = relationship("Quiz", back_populates="questions")

Base.metadata.create_all(engine)

# ───── STATES ─────
NAME, QUESTION, OPTIONS, CORRECT = range(4)

user_temp = {}

# ───── START ─────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/create | /list | /attempt quizname")

# ───── CREATE ─────
async def create(update, context):
    user_temp[update.effective_user.id] = {"questions":[]}
    await update.message.reply_text("Send quiz name")
    return NAME

async def name(update, context):
    user_temp[update.effective_user.id]["name"] = update.message.text
    await update.message.reply_text("Send question")
    return QUESTION

async def question(update, context):
    user_temp[update.effective_user.id]["q"] = update.message.text
    await update.message.reply_text("Send 4 options comma separated")
    return OPTIONS

async def options(update, context):
    opts = update.message.text.split(",")
    if len(opts) != 4:
        return await update.message.reply_text("Need 4 options")

    user_temp[update.effective_user.id]["opts"] = opts

    kb = [[InlineKeyboardButton(opt, callback_data=str(i))] for i,opt in enumerate(opts)]
    await update.message.reply_text("Select correct", reply_markup=InlineKeyboardMarkup(kb))
    return CORRECT

async def correct(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    idx = int(q.data)

    data = user_temp[uid]

    data["questions"].append({
        "q": data["q"],
        "opts": data["opts"],
        "ans": idx
    })

    kb = [
        [InlineKeyboardButton("➕ Add More", callback_data="more")],
        [InlineKeyboardButton("💾 Save", callback_data="save")]
    ]

    await q.edit_message_text("Saved question", reply_markup=InlineKeyboardMarkup(kb))
    return QUESTION

# ───── SAVE / MORE ─────
async def control(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    data = user_temp.get(uid)

    if q.data == "more":
        await q.message.reply_text("Send next question")
        return QUESTION

    if q.data == "save":
        session = Session()
        quiz = Quiz(name=data["name"])
        session.add(quiz)
        session.commit()

        for x in data["questions"]:
            session.add(Question(
                quiz_id=quiz.id,
                text=x["q"],
                options=json.dumps(x["opts"]),
                correct=x["ans"]
            ))

        session.commit()
        session.close()

        user_temp.pop(uid)
        await q.message.reply_text("Quiz saved ✅")
        return ConversationHandler.END

# ───── LIST ─────
async def list_q(update, context):
    session = Session()
    quizzes = session.query(Quiz).all()
    text = "\n".join([q.name for q in quizzes]) or "No quiz"
    await update.message.reply_text(text)
    session.close()

# ───── ATTEMPT ─────
async def attempt(update, context):
    name = " ".join(context.args)

    session = Session()
    quiz = session.query(Quiz).filter_by(name=name).first()

    if not quiz:
        return await update.message.reply_text("Not found")

    context.user_data["qs"] = quiz.questions
    context.user_data["i"] = 0
    context.user_data["score"] = 0

    await send_q(update, context)
    session.close()

async def send_q(update, context):
    i = context.user_data["i"]
    qs = context.user_data["qs"]

    if i >= len(qs):
        return await update.message.reply_text(f"Score: {context.user_data['score']}")

    q = qs[i]
    opts = json.loads(q.options)

    kb = [[InlineKeyboardButton(o, callback_data=f"{i}_{x}")] for x,o in enumerate(opts)]
    await update.message.reply_text(q.text, reply_markup=InlineKeyboardMarkup(kb))

async def answer(update, context):
    q = update.callback_query
    await q.answer()

    i, chosen = map(int, q.data.split("_"))
    qs = context.user_data["qs"]

    if chosen == qs[i].correct:
        context.user_data["score"] += 1

    context.user_data["i"] += 1
    await send_q(update, context)

# ───── MAIN ─────
def main():
    TOKEN = os.getenv("BOT_TOKEN")

    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("create", create)],
        states={
            NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
            QUESTION:[MessageHandler(filters.TEXT & ~filters.COMMAND, question)],
            OPTIONS:[MessageHandler(filters.TEXT & ~filters.COMMAND, options)],
            CORRECT:[CallbackQueryHandler(correct)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(control, pattern="more|save"))
    app.add_handler(CommandHandler("list", list_q))
    app.add_handler(CommandHandler("attempt", attempt))
    app.add_handler(CallbackQueryHandler(answer))

    app.run_polling()

if __name__ == "__main__":
    main()
