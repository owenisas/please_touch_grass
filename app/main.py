from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from auth import reddit
import uuid
import requests
from PIL import Image, ImageDraw, ImageFont


def calculate_touch_grass_index(comments, subreddits, posts):
    comment_count = len(comments['data']['children'])
    subreddit_count = len(subreddits['data']['children'])
    post_count = len(posts['data']['children'])

    # Simple formula: fewer activities imply a higher "Touch Grass Index"
    index = max(0, 100 - (comment_count + post_count) + subreddit_count)
    return index


def generate_touch_grass_card(username, index):
    # Create an image
    img = Image.new('RGB', (800, 400), color=(73, 109, 137))
    draw = ImageDraw.Draw(img)

    # Load a font
    font = ImageFont.truetype("arial.ttf", 40)

    # Add text
    draw.text((50, 50), f"User: {username}", font=font, fill=(255, 255, 255))
    draw.text((50, 150), f"Touch Grass Index: {index}", font=font, fill=(255, 255, 255))

    # Save the image
    img_path = f"{username}_touch_grass_card.png"
    img.save(img_path)

    return img_path


def get_user_comments(access_token):
    headers = {
        "Authorization": f"bearer {access_token}",
        "User-Agent": "TouchGrassApp/0.0.1"
    }
    response = requests.get("https://oauth.reddit.com/user/me/comments", headers=headers)
    return response.json()


def get_user_subreddits(access_token):
    headers = {
        "Authorization": f"bearer {access_token}",
        "User-Agent": "TouchGrassApp/0.0.1"
    }
    response = requests.get("https://oauth.reddit.com/subreddits/mine/subscriber", headers=headers)
    return response.json()


def get_user_posts(access_token):
    headers = {
        "Authorization": f"bearer {access_token}",
        "User-Agent": "TouchGrassApp/0.0.1"
    }
    response = requests.get("https://oauth.reddit.com/user/me/submitted", headers=headers)
    return response.json()


app = FastAPI()
templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def read_root(request: Request):
    state = str(uuid.uuid4())
    auth_url = reddit.get_authorization_url(state)
    return templates.TemplateResponse("index.html", {"request": request, "auth_url": auth_url})


@app.get("/callback")
def callback(request: Request, code: str, state: str):
    token_data = reddit.get_token(code)
    print(token_data)
    access_token = token_data.get("access_token")
    user_info = reddit.get_user_info(access_token)
    username = user_info["name"]
    comments = get_user_comments(access_token)
    subreddits = get_user_subreddits(access_token)
    posts = get_user_posts(access_token)

    index = calculate_touch_grass_index(comments, subreddits, posts)
    generate_touch_grass_card(username, index)
    return templates.TemplateResponse("index.html", {"request": request, "user_info": user_info})


@app.get("/generate_card")
def generate_card(request: Request):
    access_token = request.headers.get("Authorization").split(" ")[1]
    username = reddit.get_user_info(access_token)  # Replace with actual logic to get the username

    comments = get_user_comments(access_token)
    subreddits = get_user_subreddits(access_token)
    posts = get_user_posts(access_token)

    index = calculate_touch_grass_index(comments, subreddits, posts)
    img_path = generate_touch_grass_card(username, index)

    return FileResponse(img_path, media_type="image/png", filename=img_path)
