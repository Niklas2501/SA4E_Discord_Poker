import json
import socket
from time import sleep

import discord
from discord import Webhook, RequestsWebhookAdapter

from Configuration.Configuration import Configuration
from Configuration.Encryption import Encryption
from Configuration.Enums import BotMode


class Bot(discord.Client):

    def __init__(self, config: Configuration, interface, bot_mode: BotMode, player_id: str, **options):
        super().__init__(**options)
        self.config = config
        self.interface = interface
        self.player_id = player_id

        # credentials = self.config.secrets.get_credentials(self.player_id)
        # if credentials is not None:
        #     self.player_id = credentials[0]

        # Both bots are modeled in a single class and the corresponding behaviour is determined according to this
        self.bot_mode = bot_mode

        self.encryption = Encryption(self.config)
        self.encryption.load_keys()

        # A webhook is used to send messages to the channel
        # This is way easier and more performant than dealing with the asynchronous message sending of discord.Client
        if self.bot_mode == BotMode.TABLE_MODE:
            self.webhook = Webhook.from_url(self.config.secrets.table_webhook_url, adapter=RequestsWebhookAdapter())

            # Should be in the interface class, but was not changed after giving access to other group
            self.table_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.table_socket.connect((self.config.tcp_ip, self.config.tcp_port))
        elif self.bot_mode == BotMode.PLAYER_MODE:
            self.webhook = Webhook.from_url(self.config.secrets.player_webhook_url, adapter=RequestsWebhookAdapter())
        elif self.bot_mode == BotMode.GROUP2_INTERFACE:
            self.webhook = Webhook.from_url(self.config.secrets.table_webhook_url, adapter=RequestsWebhookAdapter())

    async def on_ready(self):
        print('{} bot is now ready.'.format('Table' if self.bot_mode == BotMode.TABLE_MODE else 'Player'))

        # Release the lock so the client can start interacting with the bot
        if self.interface.ready_lock.locked():
            self.interface.ready_lock.release()

    async def on_message(self, message: discord.Message):

        # Restrict to channel
        if message.channel.id != self.config.secrets.text_channel_id:
            return

        # Ignore own messages
        if message.author.name == self.player_id:
            return

        content, valid_signature = self.decrypt(message.content, message.author.name)

        # Decrypt returns None if this client is not the intended recipient of the message
        if valid_signature is None:
            return

        if not valid_signature:
            print('Invalid signature for message from', message.author.name)
            return

        reply_content = self.interface.handle_message(content, message.author.name)

        if reply_content is not None:
            self.send_message(reply_content, message.author.name)

    def decrypt(self, message, author):
        d = json.loads(message)

        # Ignore messages not addressed to this player
        if d['recipient'] != self.player_id:
            return None, None

        content, valid_signature = self.encryption.decrypt(d, self.player_id, author)

        return content, valid_signature

    def send_message(self, message_content, recipient):
        sleep(self.config.message_sleep_time)

        d = {}
        d['recipient'] = recipient

        signer = self.player_id

        if self.bot_mode == BotMode.PLAYER_MODE:
            print(self.player_id + ' send: ' + str(message_content).strip())

        # Can be used to simulate a faked signature:
        # For will look like Player1 tried to fake a message for this player (self.player_id)
        # if self.bot_mode == BotMode.PLAYER_MODE:
        #     signer = 'Player1'

        d['content'], d['signature'] = self.encryption.encrypt(message_content, recipient, signer)
        content = json.dumps(d)

        self.webhook.send(content=content,
                          username=self.player_id,
                          avatar_url=self.user.avatar_url)

    def run(self, *args, **kwargs):
        # Acquire the lock before sub thread starting process so the client will have to wait before interacting
        # with the bot until it is connected, see on_ready function
        print('Starting and connecting bot now ...')
        super(Bot, self).run(*args, **kwargs)
