from uuid import uuid4
import re
from telegram import InlineQueryResultArticle, InlineQueryResultPhoto, ParseMode, \
    InputTextMessageContent
from telegram.ext import Updater, InlineQueryHandler, CommandHandler
import logging
import urllib.request
import os

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_img_from_kiltiscam():
    """
    Grabs current kiltiscam image from server
    """
    cur_path = os.path.dirname(__file__)
    img_path = os.path.relpath("../kiltiscam/kiltahuone.jpg")
    f = open(img_path, "rb")
    return f


def _get_img_from_url(url):
    """
    Deprecated old function that grabs the image from
    inkubio.fi/kiltiscam/kiltahuone.jpg
    """
    img = urllib.request.urlopen(url).read()
    with open('out.jpg','wb') as f:
        f.write(img)
        i = open('out.jpg', 'rb')
        return i


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.

def stalk(bot, update):
    """
    Command to post current kiltiscam image
    """
    msg = update.message.text.lower()
    if msg == '/stalk' or msg == '/stalk@kiltisbot':
        img = _get_img_from_kiltiscam()
        bot.sendPhoto(update.message.chat_id, photo=img)
        img.close()

# Experimental functionality, currently disabled
"""
def inlinequery(bot, update):
    query = update.inline_query.query
    results = []

    results.append(InlineQueryResultPhoto(id=uuid4(),
                                            photo_url="http://www.inkubio.fi/kiltiscam/kiltahuone.jpg",
                                            thumb_url="http://www.inkubio.fi/kiltiscam/kiltahuone.jpg"))

    results.append(InlineQueryResultPhoto(id=uuid4(),
                                            photo_url="http://ruutu.hut.fi/pics/30-Jonotilanne.jpg",
                                            thumb_url="http://ruutu.hut.fi/pics/30-Jonotilanne.jpg"))

    bot.answerInlineQuery(update.inline_query.id, results=results)
"""

def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():
    # Create the Updater and pass it your bot's token.

    # https://kiltisbot.appspot.com/set_webhook?url=https://kiltisbot.appspot.com/webhook

    updater = Updater(config.kiltistoken)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("stalk", stalk))

    # on noncommand i.e message - echo the message on Telegram
    # dp.add_handler(InlineQueryHandler(inlinequery))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
