import json
from pathlib import Path


class Configuration:
    """
    This class stores all configurable parameters. A instance of this class is passed to every
    subcomponent that needs access to some kind of configuration, setting or parameter
    """

    def __init__(self):
        self.tcp_ip = '127.0.0.1'
        self.tcp_port = 1850
        self.tcp_buffer_size = 1024

        self.message_sleep_time = 2
        self.request_delay = 60
        self.encryption_enabled = True

        self.keys = Path("../Configuration/keys/")
        self.secrets_file = Path("../Configuration/secrets.json")

        self.secrets = Secrets()
        self.secrets.import_from_file(self.secrets_file)

        self.table_instance_name = 'Table'
        self.reddit_user_agent = 'S4AE.Bot'

        # Subreddit of group 1 (for testing)
        # self.subreddit_name = 'S4AE'

        # Subreddit of group 2
        self.subreddit_name = 'PokerSturm'


class Secrets:
    """
    This class stores some configuration settings which can't be published e.g. the discord bot private key.
    Hence these values are read form a local file, which e.g. isn't pushed to the Github repo.
    """

    def __init__(self):
        self.text_channel_id = None
        self.voice_channel_id = None
        self.server_id = None
        self.table_bot_token = None
        self.player_bot_token = None
        self.table_webhook_url = None
        self.player_webhook_url = None

    def import_from_file(self, path_to_file: Path):
        with open(path_to_file, 'r') as f:
            secrets = json.load(f)

        self.text_channel_id = secrets['text_channel_id']
        self.voice_channel_id = secrets['voice_channel_id']
        self.server_id = secrets['server_id']
        self.table_bot_token = secrets['table_bot_token']
        self.player_bot_token = secrets['player_bot_token']
        self.table_webhook_url = 'https://discord.com/api/webhooks/' + secrets['table_webhook_url_postfix']
        self.player_webhook_url = 'https://discord.com/api/webhooks/' + secrets['player_webhook_url_postfix']

        self.p1_user_name = secrets['p1_user_name']
        self.p1_password = secrets['p1_password']
        self.p1_app_id = secrets['p1_app_id']
        self.p1_app_secret = secrets['p1_app_secret']

        self.p2_user_name = secrets['p2_user_name']
        self.p2_password = secrets['p2_password']
        self.p2_app_id = secrets['p2_app_id']
        self.p2_app_secret = secrets['p2_app_secret']

    def get_credentials(self, client_side_id):
        if client_side_id == 'Table':
            return None
            # return self.table_user_name, self.table_password, self.table_app_id, self.table_app_secret
        elif client_side_id == 'Player1':
            return self.p1_user_name, self.p1_password, self.p1_app_id, self.p1_app_secret
        elif client_side_id == 'Player2':
            return self.p2_user_name, self.p2_password, self.p2_app_id, self.p2_app_secret
