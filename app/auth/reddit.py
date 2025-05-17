import requests
from fastapi import Request
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDDIT_REDIRECT_URI")
AUTH_BASE_URL = "https://www.reddit.com/api/v1/authorize"
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_BASE_URL = "https://oauth.reddit.com"

def get_authorization_url(state: str):
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "state": state,
        "redirect_uri": REDIRECT_URI,
        "duration": "temporary",
        "scope": "identity read history mysubreddits"
    }
    return f"{AUTH_BASE_URL}?{urlencode(params)}"

def get_token(code: str):
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    headers = {"User-Agent": "TouchGrassApp/0.0.1"}
    response = requests.post(TOKEN_URL, auth=auth, data=data, headers=headers)
    return response.json()

def get_user_info(token: str):
    headers = {
        "Authorization": f"bearer {token}",
        "User-Agent": "TouchGrassApp/0.0.1"
    }
    response = requests.get(f"{API_BASE_URL}/api/v1/me", headers=headers)
    return response.json()
