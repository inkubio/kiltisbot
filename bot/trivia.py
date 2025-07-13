import requests
import html
import random
from telegram import Update, Poll
from telegram.ext import ContextTypes

async def trivia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Retrieves a random trivia quiz from an open database.
    Creates the quiz and sends it to the chat.
    """
    try:
        response = requests.get("https://opentdb.com/api.php?amount=1&type=multiple")
        response.raise_for_status()
        data = response.json()
        question_data = data['results'][0]
    except Exception as e:
        await update.message.reply_text(f"⚠️ Couldn't fecth question: {e}")
        return

    question = html.unescape(question_data['question'])
    correct_answer = html.unescape(question_data['correct_answer'])
    incorrect_answers = [html.unescape(ans) for ans in question_data['incorrect_answers']]
    options = incorrect_answers + [correct_answer]
    random.shuffle(options)
    correct_index = options.index(correct_answer)

    # Sending the telegram quiz
    await update.message.reply_poll(
        question=f"❓ {question}",
        options=options,
        type=Poll.QUIZ,
        correct_option_id=correct_index,
        is_anonymous=False
    )
