import asyncio
import json
import threading

from Bot.Bot import Bot
from Configuration.Configuration import Configuration
from Configuration.Enums import BotMode
from Interface import Interface


class TableInterface(Interface):
    """
    This class contains the client side interface. It uses a instance of Bot in client mode to communicate
    with the server / table interface
    """

    def __init__(self, config: Configuration):
        super().__init__(config)

    def start_bot(self):
        self.ready_lock.acquire()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        self.bot = Bot(self.config, self, BotMode.TABLE_MODE, self.config.table_instance_name)
        self.bot.run(self.config.secrets.table_bot_token)

    def start(self):
        threading.Thread(target=self.start_bot).start()

    def handle_message(self, msg, author):

        if not self.check_secure_request(msg, author):
            return

        self.bot.table_socket.send(msg.encode())
        print('Table interface SEND TO table:', msg.strip())
        server_reply = self.bot.table_socket.recv(self.config.tcp_buffer_size).decode('UTF-8')
        print('Table interface RECEIVED FROM table:', server_reply.strip())
        print()
        return server_reply

    @staticmethod
    def check_secure_request(msg, author):
        """
        Checks whether the player mentioned in the message matches the author the message, so that no other player can
        e.g. request someones card

        """

        msg_dict = json.loads(msg.strip().replace('\'', '"'))

        if msg_dict['method'] in ['info', 'removePlayer', 'call']:
            return author == msg_dict['name']
        else:
            return True

    @staticmethod
    def start_instance():
        config = Configuration()
        table_interface = TableInterface(config)
        table_interface.start()


if __name__ == '__main__':
    TableInterface.start_instance()
