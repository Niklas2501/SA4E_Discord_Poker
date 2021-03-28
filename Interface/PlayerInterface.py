import asyncio
import json
import threading
from random import randint
from time import sleep

from Bot.Bot import Bot
from Configuration.Configuration import Configuration
from Configuration.Enums import BotMode
from Interface import Interface


class Requests:
    PLAYER_ADDED = 0
    GAME_STARTED = 1
    ROUND_STARTED = 2
    STATE = 3
    CURRENT_PLAYER = 4
    ACTION_REQUESTED = 5


class PlayerInterface(Interface):
    """
    This class contains the client side interface. It uses a instance of Bot in client mode to communicate
    with the server / table interface
    """

    def __init__(self, config: Configuration, player_id: str, is_lead_player):
        super().__init__(config)
        self.player_id = player_id
        self.last_request_send = None
        self.is_lead_player = is_lead_player
        self.single_request_finished = threading.Lock()

    def start_bot(self):
        self.ready_lock.acquire()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        self.bot = Bot(self.config, self, BotMode.PLAYER_MODE, self.player_id)
        self.bot.run(self.config.secrets.player_bot_token)

    def handle_message(self, msg, author):
        CALL_STATES = ["Pre-Flop-State", "Flop-State", "Turn-State", "River-State"]
        END_STATES = ["Winner-State", "End-State"]

        json_data = json.loads(msg)
        print(self.player_id + ' received: ' + str(json_data).strip())

        # For playing manually this if would have to be changed
        if self.last_request_send == Requests.STATE:

            if json_data["message"] in CALL_STATES:
                self.last_request_send = Requests.CURRENT_PLAYER
                self.bot.send_message("{ 'method' : 'current' , 'name' : '" + self.player_id + "' , 'action' : '' }\n",
                                      self.config.table_instance_name)

            elif json_data["message"] in END_STATES:
                if self.is_lead_player:
                    self.bot.send_message(
                        "{ 'method' : 'start' , 'name' : '+" + self.player_id + "' , 'action' : '' }\n",
                        self.config.table_instance_name)
                self.move_not_finished = False

            elif json_data["message"] == "Start-State":
                self.move_not_finished = False
                self.last_request_send = None

        elif self.last_request_send == Requests.CURRENT_PLAYER:

            if json_data["message"] == self.player_id:
                self.last_request_send = Requests.ACTION_REQUESTED
                self.bot.send_message("{ 'method' : 'actions' , 'name' : '" + self.player_id + "' , 'action' : '' }\n",
                                      self.config.table_instance_name)
            else:
                self.move_not_finished = False
                self.last_request_send = None

        elif self.last_request_send == Requests.ACTION_REQUESTED:
            actions = str(json_data["message"]).split(",")

            if actions[0] != "none":
                # print(actions)

                # If multiple actions are available ones is chosen randomly
                decision = randint(0, 100)
                if decision <= 10:
                    self.bot.send_message(
                        "{ 'method' : 'call' , 'name' : '" + self.player_id + "' , 'action' : '" + actions[0] + "' }\n",
                        self.config.table_instance_name)
                else:
                    if len(actions) == 2 or decision < 55:
                        self.bot.send_message(
                            "{ 'method' : 'call' , 'name' : '" + self.player_id + "' , 'action' : '" + actions[
                                1] + "' }\n", self.config.table_instance_name)
                    else:
                        self.bot.send_message(
                            "{ 'method' : 'call' , 'name' : '" + self.player_id + "' , 'action' : '" + actions[
                                2] + "' }\n", self.config.table_instance_name)
            elif actions[0] == "none":
                self.bot.send_message(
                    "{ 'method' : 'call' , 'name' : '" + self.player_id + "' , 'action' : 'allin' }\n",
                    self.config.table_instance_name)
            else:
                # In case the message received does not match the expected format, i. e. does not provide possible actions
                self.move_not_finished = False
                self.last_request_send = None

            self.last_request_send = None
            self.move_not_finished = False

        return None

    def start(self):
        threading.Thread(target=self.start_bot).start()

        self.ready_lock.acquire()

        self.bot.send_message("{ 'method' : 'addPlayer' , 'name' : '" + self.player_id + "' , 'action' : '' }\n",
                              self.config.table_instance_name)
        self.last_request_send = Requests.PLAYER_ADDED

        if self.is_lead_player:
            input("Input something when all players were added\n")

            self.bot.send_message("{ 'method' : 'start' , 'name' : '" + self.player_id + "' , 'action' : '' }\n",
                                  self.config.table_instance_name)
            self.last_request_send = Requests.GAME_STARTED
        else:
            print("Waiting {} seconds for other players to join and lead player to start the game".format(
                self.config.request_delay))
            sleep(self.config.request_delay)

        while True:

            # Note: For manual playing this whole while loop should be removed and replaced with a simple input
            # query and sending this via the bot
            self.last_request_send = Requests.STATE
            self.move_not_finished = True
            self.bot.send_message("{ 'method' : 'status' , 'name' : '" + self.player_id + "' , 'action' : '' }\n",
                                  self.config.table_instance_name)

            # Cant use a lock for this purpose because the bot thread can only lock access when the 1st message
            # of the sequence is received, in which case the main thread
            # may have already (unintentionally) sent another status request.
            while self.move_not_finished:
                sleep(2) # was 5, reduced because this should not influence the rate limiting

    @staticmethod
    def start_instance(player_id, is_lead_player):
        config = Configuration()
        player_interface = PlayerInterface(config, player_id, is_lead_player)
        player_interface.start()
