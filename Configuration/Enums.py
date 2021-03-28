from enum import Enum


class BotMode(Enum):
    PLAYER_MODE = 0
    TABLE_MODE = 1
    GROUP2_INTERFACE = 2

# Selection how the client interacts with server in the sense of the messages transmitted, not how they are transmitted.
class ClientMode(Enum):
    DISCORD = 0
    REDDIT = 0