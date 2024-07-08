import requests
import os
import dotenv

class Slack:
    def __init__(self):
        dotenv.load_dotenv()
        self.webhook_url = os.getenv("slack_url")

    def send_message(self, message):
        self.webhook_url = self.webhook_url
        print(self.webhook_url)
        requests.post(self.webhook_url, json={"text": message}, headers={"Content-Type": "application/json"})
        return True