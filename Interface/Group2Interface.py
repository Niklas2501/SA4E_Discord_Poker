import asyncio
import json
import threading

import praw
from praw.models import Submission

from Bot.Bot import Bot
from Configuration.Configuration import Configuration
from Configuration.Enums import BotMode
from Interface import Interface


class Group2Interface(Interface):

    def __init__(self, config: Configuration):
        super().__init__(config)

        self.reddits = {}
        self.threads = {}

        self.private_message_receiver = []

    def start_bot(self):
        self.ready_lock.acquire()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        self.bot = Bot(self.config, self, BotMode.GROUP2_INTERFACE, self.config.table_instance_name)
        self.bot.run(self.config.secrets.table_bot_token)

    def start(self):
        threading.Thread(target=self.start_bot).start()

    def handle_message(self, msg, author):
        """
        Called by the bot instance whenever a message for this user is received

        :param msg: The content of the message as string
        :param author: The discord username of the user that send the message
        """

        print('Group2Interface received from discord:', msg.strip())

        # If it's a "new" user, we must initialise some things
        if author not in self.reddits:
            self.add_player(author)

        converted_msg, send_privately = self.convert_message(msg)

        # Get the reddit thread object for the author msg was send by
        # We can use a single object for all because the posting reddit user is associated with it
        author_thread_obj: Submission = self.threads.get(author)

        # Based on the type of message send via private message or post as comment of the post
        if send_privately is None:
            # Message that cannot be processed by the reddit server interface will be ignored.
            return
        if send_privately:
            thread_creator = author_thread_obj.author
            thread_creator.message("PokerSturm", converted_msg)
        else:
            author_thread_obj.reply(converted_msg)

    def add_player(self, player_id):

        # Check if player with this id already known, should not occur.
        if player_id in self.reddits or player_id in self.threads:
            raise ValueError('Player {} already present in dicts!'.format(player_id))

        credentials = self.config.secrets.get_credentials(player_id)

        if credentials is not None:
            username, password, client_id, client_secret = credentials
        else:
            raise ValueError('No reddit credentials available for player {}'.format(player_id))

        reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, username=username, password=password,
                             user_agent=self.config.reddit_user_agent, check_for_async=False)

        # Get the most recent submission in the configured subreddit which is used for communication
        thread = list(reddit.subreddit(self.config.subreddit_name).new(limit=1))[0]

        # Start separate thread that awaits private messages of the reddit user and forwards these via discord
        pmr = PrivateMessageReceiver(reddit, self.bot, player_id)
        pmr.start()
        self.private_message_receiver.append(pmr)

        self.reddits[player_id] = reddit
        self.threads[player_id] = thread

    @staticmethod
    def convert_message(msg: str):

        # Convert message in json-like format into python dict
        msg_dict = json.loads(msg.strip().replace('\'', '"'))

        if msg_dict['method'] == 'addPlayer':
            converted_message = "addPlayer " + msg_dict['name']
            send_privately = True
        elif msg_dict['method'] == 'start':
            converted_message = "startGame"
            send_privately = False
        elif msg_dict['method'] == 'status':
            converted_message = "getState"
            send_privately = True
        elif msg_dict['method'] == 'current':
            converted_message = "getCurrentPlayer"
            send_privately = True
        elif msg_dict['method'] == 'actions':
            converted_message = "getAvailableActions"
            send_privately = True
        elif msg_dict['method'] == 'removePlayer':
            converted_message = "removePlayer " + msg_dict['name']
            send_privately = True
        elif msg_dict['method'] == 'update':
            converted_message = "update"
            send_privately = True
        elif msg_dict['method'] == 'info':
            converted_message = "getPlayerInformation"
            send_privately = True
        elif msg_dict['method'] == 'call':
            converted_message = msg_dict['action']
            send_privately = False
        else:
            raise ValueError('Undefined message type received:', msg)

        return converted_message, send_privately

    @staticmethod
    def start_instance():
        config = Configuration()
        group2_interface = Group2Interface(config)
        group2_interface.start()


class PrivateMessageReceiver(threading.Thread):

    def __init__(self, reddit, bot, player_id):
        super().__init__()
        self.reddit: praw.Reddit = reddit
        self.bot: Bot = bot
        self.player_id = player_id

    def run(self):
        print('Private Message Receiver: Waiting for messages for {} ...'.format(self.player_id))

        for msg in self.reddit.inbox.stream(skip_existing=True):
            msg.mark_read()

            # print(self.player_id, 'received from reddit:', msg.body)

            if msg.subject != 'PokerSturm-Server':
                continue
            else:
                discord_msg = self.convert_message(msg.body)

                if discord_msg is None:
                    continue

                print('Group2Interface send to client {}: {}'.format(self.player_id, discord_msg.strip()))

                self.bot.send_message(discord_msg, self.player_id)

        print('PrivateMessageReceiver for {} stopped.'.format(self.player_id))

    @staticmethod
    def convert_message(msg: str):

        if msg == 'add received':
            converted_msg = '{"status" : "Success" , "message" : "Player added"}\n'
        elif msg == 'remove received':
            converted_msg = '{"status" : "Success" , "message" : "Player removed"}\n'
        elif msg == 'screen refreshed':
            # No return is actually expected
            return None
        elif msg.startswith("state info: "):
            state = msg.split(": ")[-1]
            converted_msg = '{"status" : "Success" , "message" : "' + state + '"}\n'
        elif msg.startswith("current player info: "):
            current_player = msg.split(": ")[-1]
            converted_msg = '{"status" : "Success" , "message" : "' + current_player + '"}\n'
        elif msg.startswith("available Actions: "):
            actions = msg.split(": ")[-1]

            # Special handling because rmi and json responses differ for this case
            if actions == 'allin':
                actions = 'none'
            else:
                # convert action list to expected format, without bet height
                parts = actions.split(',')
                parts_new = [part if len(part.split(' ')) == 1 else part.split(' ')[0] for part in parts]
                actions = ','.join(parts_new)
            converted_msg = '{"status" : "Success" , "message" : "' + actions + '"}\n'
        elif msg.startswith("your player information: "):
            info = msg.split(": ")[-1]
            converted_msg = '{"status" : "Success" , "message" : "' + info + '"}\n'

        else:
            raise ValueError('Undefined message type received:', msg)

        return converted_msg


if __name__ == '__main__':
    Group2Interface.start_instance()
