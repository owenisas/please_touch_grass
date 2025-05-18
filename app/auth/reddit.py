import os
from typing import Optional
import requests
from urllib.parse import urlencode
import dotenv

dotenv.load_dotenv()

class RedditAuth:
    def __init__(self):
        self.client_id = os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        self.redirect_uri = os.getenv("REDDIT_REDIRECT_URI")
        self.scopes = [
            "identity",  # For user info
            "read",  # For reading posts and comments
            "history",  # For accessing user's submitted posts
            "mysubreddits"  # For accessing subscribed subreddits
        ]

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "state": state,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes)
        }
        return f"https://www.reddit.com/api/v1/authorize?{urlencode(params)}"

    def get_token(self, code: str) -> Optional[dict]:
        auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        headers = {"User-Agent": "TouchGrassApp/0.0.1"}
        response = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=auth,
            data=data,
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        print(f"Token request failed: {response.status_code} - {response.text}")
        return None

    def refresh_token(self, refresh_token: str) -> Optional[dict]:
        auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        headers = {"User-Agent": "TouchGrassApp/0.0.1"}
        response = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=auth,
            data=data,
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        print(f"Token refresh failed: {response.status_code} - {response.text}")
        return None

    def get_user_info(self, access_token: str) -> Optional[dict]:
        headers = {
            "Authorization": f"bearer {access_token}",
            "User-Agent": "TouchGrassApp/0.0.1"
        }
        response = requests.get("https://oauth.reddit.com/api/v1/me", headers=headers)
        if response.status_code == 200:
            return response.json()
        print(f"User info request failed: {response.status_code} - {response.text}")
        return None
