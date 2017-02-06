import logging
import pymongo
import uuid
import time
import config
import math
import datetime
from telegram.ext import Updater, CommandHandler, MessageHandler, BaseFilter

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


class MessageFilter(BaseFilter):
    def filter(self, message):
        if message.text.startswith('/'):
            return False
        for entity in message.entities:
            if entity.type == "mention":
                name = message.text[entity.offset:entity.offset + entity.length]
                if name == config.name:
                    return True
        return False


class BotHandler:
    def __init__(self):
        self.db = pymongo.MongoClient(config.db).telegram
        self.updater = Updater(config.token)

    def add_mark(self, bot, update):
        collection = self.db.mark
        mark = Mark()
        mark.chat_id = update.message.chat_id
        mark.message_id = update.message.message_id
        mark.message = update.message.to_dict()
        if not collection.find_one({"chat_id": mark.chat_id, "message_id": mark.message_id}):
            collection.insert(mark.__dict__)
        text = "Message " + str(update.message.message_id) + " have been saved."
        bot.sendMessage(update.message.chat_id, reply_to_message_id=update.message.message_id, text=text)

    def get_message(self, chat_id, args):
        collection = self.db.mark
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

    def del_mark(self, bot, update, args):
        chat_id = update.message.chat_id
        reply = update.message.message_id
        deleted = []
        for arg in args:
            result = self.get_message(chat_id, [arg])
            if result and result.count() == 1:
                mark = Mark(result[0])
                self.db.mark.remove({"uuid": mark.uuid})
                deleted.append(arg)
        if deleted:
            text = "Deleted "
            text += " ".join(deleted)
        else:
            text = "No message found."
        bot.sendMessage(update.message.chat_id, reply_to_message_id=reply, text=text)

    def list_mark(self, bot, update, args):
        collection = self.db.mark
        chat_id = update.message.chat_id
        result = collection.find({"chat_id": chat_id}).sort("add_time", pymongo.DESCENDING)
        totally_num = result.count()
        totally_page = int(math.ceil(totally_num / 10))
        if totally_page == 0:
            totally_page = 1
        show_page = 1
        if len(args) > 0:
            try:
                show_page = int(args[0])
            except ValueError:
                show_page = 1
            if show_page > totally_page:
                show_page = totally_page
            if show_page < 1:
                show_page = 1
        text = "Page " + str(show_page) + " of " + str(totally_page) + "\n"
        for i in range((show_page - 1) * 10, show_page * 10):
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

    def show_mark(self, bot, update, args):
        chat_id = update.message.chat_id
        result = self.get_message(chat_id, args)
        if result and result.count() > 0:
            mark = Mark(result[0])
            reply = mark.message_id
            text = "Show message " + str(mark.message_id) + "."
        else:
            reply = update.message.message_id
            text = "No message found."
        bot.sendMessage(update.message.chat_id, reply_to_message_id=reply, text=text)

    def info_mark(self, bot, update, args):
        chat_id = update.message.chat_id
        result = self.get_message(chat_id, args)
        text = ""
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
        logger.error('Update "%s" caused error "%s"' % (update, error))

    @staticmethod
    def help(bot, update):
        reply = update.message.message_id
        text = """
        \n
        Use \\addm to mark a message. \n
        Use \\delm to del a mark. \n
        Use \\listm [page] to show marks\n
        Use \\showm [message_id]/[uuid] to show that message. \n
        Use \\infom [message_id]/[uuid] to show that message info.\n
        """
        bot.sendMessage(update.message.chat_id, reply_to_message_id=reply, text=text)

    def message_handler(self, bot, update):
        collection = self.db.mark
        mark = Mark()
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
        if not collection.find_one({"chat_id": mark.chat_id, "message_id": mark.message_id}):
            collection.insert(mark.__dict__)
        text = "Message " + str(reply) + " have been saved."
        bot.sendMessage(update.message.chat_id, reply_to_message_id=reply, text=text)

    def loop(self):
        dispatcher = self.updater.dispatcher
        dispatcher.bot.setWebhook(config.url)
        dispatcher.add_handler(CommandHandler("addm", self.add_mark))
        dispatcher.add_handler(MessageHandler(MessageFilter(), self.message_handler))
        dispatcher.add_handler(CommandHandler("showm", self.show_mark, pass_args=True))
        dispatcher.add_handler(CommandHandler("listm", self.list_mark, pass_args=True))
        dispatcher.add_handler(CommandHandler("infom", self.info_mark, pass_args=True))
        dispatcher.add_handler(CommandHandler("delm", self.del_mark, pass_args=True))
        dispatcher.add_handler(CommandHandler("help", self.help))
        dispatcher.add_error_handler(self.error)
        self.updater.start_webhook(listen=config.ip, port=config.port, url_path=config.secret,
                                   webhook_url=config.url)
        # self.updater.start_polling()
        self.updater.idle()


if __name__ == '__main__':
    BotHandler().loop()
