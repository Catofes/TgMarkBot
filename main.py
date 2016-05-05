import logging
import pymongo
import uuid
import time
import config
import math
import datetime
import telegram.messageentity
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


class Mark:
    def __init__(self, mark=None):
        self.message = None
        self.add_time = time.time()
        self.chat_id = 0
        self.message_id = 0
        self.uuid = uuid.uuid4().__str__()
        if mark:
            self.chat_id = mark['chat_id']
            self.uuid = mark['uuid']
            self.add_time = mark['add_time']
            self.message = mark['message']
            self.message_id = mark['message_id']


class BotHandler:
    def __init__(self):
        self.db = pymongo.MongoClient().telegram
        self.updater = Updater(config.token)

    @staticmethod
    def add_mark(bot, update):
        collection = pymongo.MongoClient().telegram.mark
        mark = Mark()
        mark.chat_id = update.message.chat_id
        mark.message_id = update.message.message_id
        mark.message = update.message.to_dict()
        collection.insert(mark.__dict__)
        text = "Message " + str(update.message.message_id) + " have been saved."
        bot.sendMessage(update.message.chat_id, reply_to_message_id=update.message.message_id, text=text)

    @staticmethod
    def get_message(chat_id, args):
        collection = pymongo.MongoClient().telegram.mark
        result = None
        if len(args) == 0:
            result = collection.find({"chat_id": chat_id}).sort("add_time", pymongo.DESCENDING)
        else:
            try:
                result = collection.find({"chat_id": chat_id, 'message_id': int(args[0])})
            except ValueError:
                pass
            if not result or result.count() == 0:
                result = collection.find({"uuid": args[0]})
        return result

    @staticmethod
    def del_mark(bot, update, args):
        chat_id = update.message.chat_id
        reply = update.message.message_id
        deleted = []
        for arg in args:
            result = BotHandler.get_message(chat_id, [arg])
            if result and result.count() == 1:
                mark = Mark(result[0])
                pymongo.MongoClient().telegram.mark.remove({"uuid": mark.uuid})
                deleted.append(arg)
        if deleted:
            text = "Deleted "
            text += " ".join(deleted)
        else:
            text = "No message found."
        bot.sendMessage(update.message.chat_id, reply_to_message_id=reply, text=text)

    @staticmethod
    def list_mark(bot, update, args):
        collection = pymongo.MongoClient().telegram.mark
        chat_id = update.message.chat_id
        result = collection.find({"chat_id": chat_id}).sort("add_time", pymongo.DESCENDING)
        totally_num = result.count()
        totally_page = int(math.ceil(totally_num / 10))
        show_page = 0
        if len(args) > 0:
            show_page = int(args[0])
            if show_page > totally_page:
                show_page = totally_page
        text = "Page " + str(show_page + 1) + " of " + str(totally_page) + "\n"
        for i in range(show_page * 10, (show_page + 1) * 10):
            try:
                mark = Mark(result[i])
                text += "Id: "
                text += str(mark.message_id)
                text += "    From: "
                text += mark.message['from']['username']
                text += "    Said: "
                if len(mark.message['text']) > 0:
                    text += mark.message['text'][0:300]
                else:
                    text += "Not Text."
                text += "\n"
            except IndexError:
                continue
        bot.sendMessage(update.message.chat_id, reply_to_message_id=update.message.message_id, text=text)

    @staticmethod
    def show_mark(bot, update, args):
        chat_id = update.message.chat_id
        result = BotHandler.get_message(chat_id, args)
        if result and result.count() > 0:
            mark = Mark(result[0])
            reply = mark.message_id
            text = "Show message " + str(mark.message_id) + "."
        else:
            reply = update.message.message_id
            text = "No message found."
        bot.sendMessage(update.message.chat_id, reply_to_message_id=reply, text=text)

    @staticmethod
    def info_mark(bot, update, args):
        chat_id = update.message.chat_id
        result = BotHandler.get_message(chat_id, args)
        text = None
        if result and result.count() > 0:
            mark = Mark(result[0])
            reply = mark.message_id
            text += "chat_id: " + str(mark.chat_id) + "\n"
            text += "message_id: " + str(mark.message_id) + "\n"
            text += "from: " + str(mark.message['from']['username']) + "\n"
            text += "date: " + datetime.datetime.fromtimestamp(mark.message['date']).strftime(
                '%Y-%m-%d %H:%M:%S') + "\n"
            text += "mark_date: " + datetime.datetime.fromtimestamp(mark.add_time).strftime(
                '%Y-%m-%d %H:%M:%S') + "\n"
            text += "uuid: " + str(mark.uuid) + "\n"
        else:
            reply = update.message.message_id
            text = "No message found."
        bot.sendMessage(update.message.chat_id, reply_to_message_id=reply, text=text)

    @staticmethod
    def error(bot, update, error):
        logger.warn('Update "%s" caused error "%s"' % (update, error))

    @staticmethod
    def help(bot, update):
        chat_id = update.message.chat_id
        reply = update.message.message_id
        text = """
        Use \\add to mark a message. \n
        Use \\del to del a mark. \n
        Use \\list [page] to show marks\n
        Use \\show [message_id]/[uuid] to show that message. \n
        Use \\info [message_id]/[uuid] to show that message info.\n
        """
        bot.sendMessage(update.message.chat_id, reply_to_message_id=reply, text=text)

    @staticmethod
    def message_filter(update):
        message = update.message
        if message.text.startswith('/'):
            return False
        for entity in message.entities:
            if entity.type == "mention":
                name = message.text[entity.offset:entity.offset + entity.length]
                if name == config.name:
                    return True
        return False

    @staticmethod
    def message_handler(bot, update):
        collection = pymongo.MongoClient().telegram.mark
        mark = Mark()
        reply = 0
        if update.message.reply_to_message:
            reply = update.message.reply_to_message.message_id
            mark.chat_id = update.message.reply_to_message.chat_id
            mark.message_id = update.message.reply_to_message.message_id
            mark.message = update.message.reply_to_message.to_dict()
        else:
            reply = update.message.message_id
            mark.chat_id = update.message.chat_id
            mark.message_id = update.message.message_id
            mark.message = update.message.to_dict()
        collection.insert(mark.__dict__)
        text = "Message " + str(update.message.message_id) + " have been saved."
        bot.sendMessage(update.message.chat_id, reply_to_message_id=reply, text=text)

    def loop(self):
        dispatcher = self.updater.dispatcher
        dispatcher.addHandler(CommandHandler("add", self.add_mark))
        dispatcher.addHandler(MessageHandler([self.message_filter], self.message_handler))
        dispatcher.addHandler(CommandHandler("show", self.show_mark, pass_args=True))
        dispatcher.addHandler(CommandHandler("list", self.list_mark, pass_args=True))
        dispatcher.addHandler(CommandHandler("info", self.info_mark, pass_args=True))
        dispatcher.addHandler(CommandHandler("del", self.del_mark, pass_args=True))
        dispatcher.addHandler(CommandHandler("help", self.help))
        dispatcher.addErrorHandler(self.error)
        self.updater.start_webhook(listen=config.ip, port=config.port, url_path=config.secret,
                                   webhook_url=config.url)
        self.updater.idle()


if __name__ == '__main__':
    BotHandler().loop()
