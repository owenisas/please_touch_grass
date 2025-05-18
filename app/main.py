from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from auth import reddit
import requests
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict
import secrets
from urllib.parse import urlencode
import os
import time
from datetime import datetime, timedelta

# Store state tokens temporarily (in production, use a proper session store)
state_store = {}

# Store user sessions (in production, use a proper database)
user_sessions: Dict[str, dict] = {}
reddit = reddit.RedditAuth()

def generate_session_id():
    return secrets.token_urlsafe(32)

def create_user_session(username: str, access_token: str, refresh_token: str):
    session_id = generate_session_id()
    user_sessions[session_id] = {
        "username": username,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=1)  # Access token expires in 1 hour
    }
    return session_id

def get_user_session(session_id: str) -> Optional[dict]:
    if session_id not in user_sessions:
        return None

    session = user_sessions[session_id]

    # Check if session is expired
    if datetime.now() > session["expires_at"]:
        # Try to refresh the token
        try:
            new_token_data = reddit.refresh_token(session["refresh_token"])
            if new_token_data and "access_token" in new_token_data:
                session["access_token"] = new_token_data["access_token"]
                session["expires_at"] = datetime.now() + timedelta(hours=1)
                return session
        except Exception as e:
            print(f"Error refreshing token: {str(e)}")

        # If refresh failed, remove the session
        del user_sessions[session_id]
        return None

    return session

def get_current_user(session_id: str = None) -> Optional[dict]:
    if not session_id:
        return None
    return get_user_session(session_id)

def generate_state_token():
    return secrets.token_urlsafe(32)


def calculate_touch_grass_index(comments, subreddits, posts):
    # Get counts from the data
    comment_count = len(comments['data']['children'])
    subreddit_count = len(subreddits['data']['children'])
    post_count = len(posts['data']['children'])

    print(f"Comment count: {comment_count}")
    print(f"Subreddit count: {subreddit_count}")
    print(f"Post count: {post_count}")

    # Simple formula: fewer activities imply a higher "Touch Grass Index"
    index = max(0, 100 - (comment_count + post_count) + subreddit_count)
    return index


def get_user_comments(access_token: str, username: str):
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "TouchGrassApp/0.0.1 by /u/owenisas"
        }
        response = requests.get(
            f"https://oauth.reddit.com/user/{username}/comments",
            headers=headers,
            params={
                "limit": 100,
                "sort": "new",
                "t": "all"
            }
        )
        print(f"Comments API Response Status: {response.status_code}")
        print(f"Comments API Response Headers: {response.headers}")
        response.raise_for_status()
        data = response.json()
        print(f"Comments API Response Data: {data}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching comments: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response headers: {e.response.headers}")
            print(f"Response content: {e.response.text}")
        return {"data": {"children": []}}


def get_user_subreddits(access_token: str):
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "TouchGrassApp/0.0.1 by /u/owenisas"
        }
        response = requests.get(
            "https://oauth.reddit.com/subreddits/mine/subscriber",
            headers=headers,
            params={
                "limit": 100,
                "show": "all"
            }
        )
        print(f"Subreddits API Response Status: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching subreddits: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response headers: {e.response.headers}")
            print(f"Response content: {e.response.text}")
        return {"data": {"children": []}}


def get_user_posts(access_token: str, username: str):
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "TouchGrassApp/0.0.1 by /u/owenisas"
        }
        response = requests.get(
            f"https://oauth.reddit.com/user/{username}/submitted",
            headers=headers,
            params={
                "limit": 100,
                "sort": "new",
                "t": "all"
            }
        )
        print(f"Posts API Response Status: {response.status_code}")
        print(f"Posts API Response Headers: {response.headers}")
        response.raise_for_status()
        data = response.json()
        print(f"Posts API Response Data: {data}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching posts: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response headers: {e.response.headers}")
            print(f"Response content: {e.response.text}")
        return {"data": {"children": []}}


app = FastAPI(
    title="Rejection Dashboard API",
    description="API for scanning Gmail for job rejections and displaying stats.",
    version="0.1.0"
)

# --- CORS Configuration ---
# TODO: Restrict origins in production
origins = [
    "http://localhost:8080", # Default Vite dev server
    "http://localhost:3000", # Common React dev server
    "https://please.touch.grass.owenisas.com",
    "http://127.0.0.1:8080"  # Added for local development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Create templates directory if it doesn't exist
os.makedirs("./templates", exist_ok=True)

# Create a basic error template
with open("./templates/error.html", "w") as f:
    f.write("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Error</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .error { color: #dc2626; }
            .message { margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1 class="error">Authentication Error</h1>
        <p class="message">{{ error_message }}</p>
        <a href="/">Return to Home</a>
    </body>
    </html>
    """)

templates = Jinja2Templates(directory="./templates")


@app.get("/")
def read_root(request: Request, error: Optional[str] = None):
    if error:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_message": f"Authentication failed: {error}"
            }
        )

    state = generate_state_token()
    auth_url = reddit.get_authorization_url(state)
    state_store[state] = True  # Store state for validation
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "auth_url": auth_url,
            "state": state
        }
    )


@app.get("/auth/reddit/url")
def get_reddit_auth_url():
    state = generate_state_token()
    auth_url = reddit.get_authorization_url(state)
    state_store[state] = True  # Store state for validation
    return JSONResponse({"url": auth_url, "state": state}, status_code=200)


@app.get("/auth/reddit/callback")
async def callback(request: Request, code: str, state: str):
    # Validate state to prevent CSRF
    if state not in state_store:
        print(f"Invalid state parameter. Received: {state}, Stored states: {list(state_store.keys())}")
        return RedirectResponse(
            url=f"http://localhost:8080/?error=invalid_state",
            status_code=302
        )

    # Remove used state
    state_store.pop(state, None)

    try:
        # Exchange code for tokens
        token_data = reddit.get_token(code)
        if not token_data or "access_token" not in token_data:
            print(f"Token exchange failed. Response: {token_data}")
            return RedirectResponse(
                url=f"http://localhost:8080/?error=token_exchange_failed",
                status_code=302
            )

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")

        # Get user info
        user_info = reddit.get_user_info(access_token)
        if not user_info or "name" not in user_info:
            print(f"Failed to get user info. Response: {user_info}")
            return RedirectResponse(
                url=f"http://localhost:8080/?error=user_info_failed",
                status_code=302
            )

        username = user_info["name"]

        # Create user session
        session_id = create_user_session(username, access_token, refresh_token)

        # Get user data for the touch grass index
        try:
            print("Fetching user data...")
            print(f"Using access token: {access_token[:10]}...")

            comments = get_user_comments(access_token, username)
            print(f"Comments response: {comments}")

            subreddits = get_user_subreddits(access_token)
            #print(f"Subreddits response: {subreddits}")

            posts = get_user_posts(access_token, username)
            print(f"Posts response: {posts}")

            index = calculate_touch_grass_index(comments, subreddits, posts)
            print(f"Calculated index: {index}")

        except Exception as e:
            print(f"Error getting user data: {str(e)}")
            return RedirectResponse(
                url=f"http://localhost:8080/?error=data_fetch_failed&details={str(e)}",
                status_code=302
            )

        # Redirect back to frontend with the data and session
        frontend_url = "http://localhost:8080/reddit-callback"
        query_params = {
            "success": "true",
            "username": username,
            "index": index,
            "session_id": session_id
        }

        return RedirectResponse(
            url=f"{frontend_url}?{urlencode(query_params)}",
            status_code=302
        )

    except Exception as e:
        print(f"Error in callback: {str(e)}")
        return RedirectResponse(
            url=f"http://localhost:8080/?error=auth_failed&details={str(e)}",
            status_code=302
        )


@app.get("/generate_card")
def generate_card(request: Request):
    access_token = request.headers.get("Authorization").split(" ")[1]
    username = reddit.get_user_info(access_token)  # Replace with actual logic to get the username

    comments = get_user_comments(access_token)
    subreddits = get_user_subreddits(access_token)
    posts = get_user_posts(access_token)

    index = calculate_touch_grass_index(comments, subreddits, posts)


@app.get("/api/user/me")
async def get_current_user_info(session_id: str):
    session = get_user_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return {
        "username": session["username"],
        "access_token": session["access_token"]
    }

@app.get("/api/user/logout")
async def logout(session_id: str):
    if session_id in user_sessions:
        del user_sessions[session_id]
    return {"message": "Logged out successfully"}

@app.get("/api/reddit/user")
async def get_reddit_user_info(session_id: str):
    session = get_user_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    try:
        # Get user info from Reddit
        headers = {
            "Authorization": f"Bearer {session['access_token']}",
            "User-Agent": "TouchGrassApp/0.0.1 by /u/owenisas"
        }
        response = requests.get(
            "https://oauth.reddit.com/api/v1/me",
            headers=headers
        )
        response.raise_for_status()
        user_data = response.json()

        return {
            "name": user_data.get("name", ""),
            "total_karma": user_data.get("total_karma", 0),
            "created_utc": user_data.get("created_utc", 0),
            "comment_karma": user_data.get("comment_karma", 0),
            "link_karma": user_data.get("link_karma", 0),
            "has_verified_email": user_data.get("has_verified_email", False)
        }
    except Exception as e:
        print(f"Error fetching Reddit user info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch user data")

@app.get("/api/reddit/activity")
async def get_reddit_activity(session_id: str):
    session = get_user_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    try:
        # Get user info first to get the username
        headers = {
            "Authorization": f"Bearer {session['access_token']}",
            "User-Agent": "TouchGrassApp/0.0.1 by /u/owenisas"
        }
        user_response = requests.get(
            "https://oauth.reddit.com/api/v1/me",
            headers=headers
        )
        user_response.raise_for_status()
        user_data = user_response.json()
        username = user_data.get("name")

        if not username:
            raise HTTPException(status_code=500, detail="Could not get username")

        # Get user's posts
        posts_response = requests.get(
            f"https://oauth.reddit.com/user/{username}/submitted",
            headers=headers,
            params={"limit": 100, "sort": "new", "t": "all"}
        )
        posts_response.raise_for_status()
        posts_data = posts_response.json()

        # Get user's comments
        comments_response = requests.get(
            f"https://oauth.reddit.com/user/{username}/comments",
            headers=headers,
            params={"limit": 100, "sort": "new", "t": "all"}
        )
        comments_response.raise_for_status()
        comments_data = comments_response.json()

        # Get user's subreddits
        subreddits_response = requests.get(
            "https://oauth.reddit.com/subreddits/mine/subscriber",
            headers=headers,
            params={"limit": 100, "show": "all"}
        )
        subreddits_response.raise_for_status()
        subreddits_data = subreddits_response.json()

        # Process the data
        posts = posts_data.get("data", {}).get("children", [])
        comments = comments_data.get("data", {}).get("children", [])
        subreddits = subreddits_data.get("data", {}).get("children", [])

        # Calculate active hours
        active_hours = {}
        for hour in range(24):
            active_hours[str(hour)] = 0

        # Process posts and comments to get active hours
        for item in posts + comments:
            created_utc = item.get("data", {}).get("created_utc", 0)
            if created_utc:
                hour = datetime.fromtimestamp(created_utc).hour
                active_hours[str(hour)] = active_hours.get(str(hour), 0) + 1

        # Calculate average score
        total_score = 0
        item_count = 0
        for item in posts + comments:
            score = item.get("data", {}).get("score", 0)
            if score is not None:
                total_score += score
                item_count += 1

        average_score = total_score / item_count if item_count > 0 else 0

        return {
            "posts": len(posts),
            "comments": len(comments),
            "averageScore": average_score,
            "subreddits": [sub.get("data", {}).get("display_name", "") for sub in subreddits],
            "activeHours": active_hours
        }
    except Exception as e:
        print(f"Error fetching Reddit activity: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch activity data")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
