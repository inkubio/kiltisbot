from uuid import uuid4

import re

from telegram import InlineQueryResultArticle, InlineQueryResultPhoto, ParseMode, \
    InputTextMessageContent
from telegram.ext import Updater, InlineQueryHandler, CommandHandler
import logging
import urllib

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    bot.sendMessage(update.message.chat_id, text='Hi!')


def help(bot, update):
    bot.sendMessage(update.message.chat_id, text='Help!')


def stalk(bot, update):

    msg = update.message.text.lower()
    print("moi")
    if msg == '/stalk' or msg == '/stalk@kahmybot':
        img = urllib.urlopen('http://www.inkubio.fi/kiltiscam/kiltahuone.jpg').read()
        bot.sendMessage(update.message.chat_id, text='lol')
        bot.sendPhoto(update.message.chat_id, photo=img)


def inlinequery(bot, update):
    query = update.inline_query.query
    results = list()

    results.append(InlineQueryResultPhoto(id=uuid4(),
                                            photo_url="http://www.inkubio.fi/kiltiscam/kiltahuone.jpg",
                                            thumb_url="http://www.inkubio.fi/kiltiscam/kiltahuone.jpg"))

    results.append(InlineQueryResultPhoto(id=uuid4(),
                                            photo_url="http://ruutu.hut.fi/pics/30-Jonotilanne.jpg",
                                            thumb_url="http://ruutu.hut.fi/pics/30-Jonotilanne.jpg"))


    bot.answerInlineQuery(update.inline_query.id, results=results)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():
    # Create the Updater and pass it your bot's token.
    kahmytoken="163712304:AAHznhUn9ajhmBHjrOJDVhWNMBQxM89ROoU"
    kiltistoken="69427851:AAFl1pyuTLjYz3OOIIiBEmM_QTnoOgtpZbU"

    # https://kiltisbot.appspot.com/set_webhook?url=https://kiltisbot.appspot.com/webhook

    updater = Updater(kahmytoken)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(InlineQueryHandler(inlinequery))

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