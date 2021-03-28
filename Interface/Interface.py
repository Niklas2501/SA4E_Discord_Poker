import threading

from Bot.Bot import Bot
from Configuration.Configuration import Configuration


class Interface:

    def __init__(self, config: Configuration):
        self.config: Configuration = config
        self.ready_lock = threading.Lock()
        self.bot: Bot

    def handle_message(self, msg, author):
        return 'Interface handled message from {}: {} '.format(author, msg)

    def start(self):
        pass
