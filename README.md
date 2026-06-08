# LinkedIn Bot

LinkedIn Bot is a Python Playwright automation project for scheduled LinkedIn activity.

## Main Concept

The bot runs browser automation during configured work hours. It can generate posts, create post images, publish to LinkedIn, like posts, comment on feed items, and process connection invitations with randomized delays.

## Core Capabilities

- Saves and reuses a LinkedIn browser session
- Generates LinkedIn posts with Together AI
- Generates a supporting image for posts
- Publishes posts through the LinkedIn web UI
- Likes random feed posts
- Comments with short preset replies
- Accepts and sends connection requests
- Uses daily action counters and randomized timing

## Tech Stack

- Python
- Playwright
- Together AI API
- Requests
- Pillow
- `python-dotenv`

## Environment Variables

```env
TOGETHER_API_KEY=your_together_api_key
HEADLESS=true
```

## Run

```bash
pip install -r requirements.txt
python main.py
```

## Caution

This project automates a third-party social platform. Use conservative limits, respect platform rules, and avoid running it from accounts you cannot risk.
