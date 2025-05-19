import asyncio
import random
import os
import logging
from datetime import datetime, time, timedelta
from playwright.async_api import async_playwright
import base64
from PIL import Image
from io import BytesIO
import requests
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('linkedin_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    "daily_posts": 2,
    "daily_comments": 15,
    "daily_connections": 15,
    "like_interval_min": 15,
    "like_per_session_min": 3,
    "like_per_session_max": 8,
    "work_hours_start": time(8, 0),
    "work_hours_end": time(20, 0),
    "min_delay": 2,
    "max_delay": 10
}

class LinkedInBot:
    def __init__(self):
        self.actions_today = {
            "posts": 0,
            "comments": 0,
            "connections": 0,
            "likes": 0
        }
        self.last_reset_date = datetime.now().date()
        self.session_file = "linkedin_session.json"
        self.headless = os.getenv('HEADLESS', 'true').lower() == 'true'
        
    def reset_counters_if_new_day(self):
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.actions_today = {
                "posts": 0,
                "comments": 0,
                "connections": 0,
                "likes": 0
            }
            self.last_reset_date = today
            logger.info("Counters reset for new day")
    
    def get_random_delay(self):
        return random.randint(CONFIG["min_delay"], CONFIG["max_delay"])
    
    async def human_like_delay(self):
        await asyncio.sleep(self.get_random_delay())
    
    async def start_browser(self):
        self.playwright = await async_playwright().start()
        
        launch_options = {
            "headless": self.headless,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        }
        
        self.browser = await self.playwright.chromium.launch(**launch_options)
        
        context_options = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "viewport": {"width": 1280, "height": 720},
            "locale": "en-US"
        }
        
        if os.path.exists(self.session_file):
            context_options["storage_state"] = self.session_file
        
        self.context = await self.browser.new_context(**context_options)
        self.feed_page = await self.context.new_page()
        self.network_page = await self.context.new_page()
        self.post_page = await self.context.new_page()
    
    async def close_browser(self):
        await self.context.storage_state(path=self.session_file)
        await self.browser.close()
        await self.playwright.stop()
    
    async def is_work_hours(self):
        now = datetime.now().time()
        return CONFIG["work_hours_start"] <= now <= CONFIG["work_hours_end"]
    
    async def generate_post(self):
        try:
            from together import Together
            client = Together(api_key=os.getenv('TOGETHER_API_KEY'))
            
            response = client.chat.completions.create(
                model="deepseek-ai/DeepSeek-V3",
                messages=[{
                    "role": "user",
                    "content": (
                        f"Generate a LinkedIn post for {datetime.now().date()} about Python automation development. "
                        "Make it engaging and informative, tailored to: "
                        "🌐 Python Automation Developer | Telegram Bot Specialist | Playwright & Selenium Expert | "
                        "Cybersecurity Enthusiast | Focused on Scalable, Real-World Automation Solutions"
                    )
                }]
            )
            
            post = response.choices[0].message.content.strip()
            about_info = "🌐 Python Automation Developer | Telegram Bot Specialist | Playwright & Selenium Expert | Cybersecurity Enthusiast | Focused on Scalable, Real-World Automation Solutions"
            
            # Generate image
            img_response = client.images.generate(
                prompt=f"LinkedIn post image for: {about_info}. Post content: {post}",
                negative_prompt="lowres, bad anatomy, error, blurry, bad art, deformed, ugly",
                model="black-forest-labs/FLUX.1-dev",
                steps=10,
                n=1
            )
            
            if img_response.data:
                image_url = img_response.data[0].url
                img_data = requests.get(image_url).content
                with open("linkedin_image.jpg", "wb") as f:
                    f.write(img_data)
                logger.info("Generated post image")
            
            # Clean markdown formatting
            post = re.sub(r'\*\*(.*?)\*\*', r'\1', post)
            post = re.sub(r'__(.*?)__', r'\1', post)
            post = re.sub(r'\*(.*?)\*', r'\1', post)
            post = re.sub(r'_(.*?)_', r'\1', post)
            
            return post.strip()
            
        except Exception as e:
            logger.error(f"Error generating post: {str(e)}")
            raise
    
    async def post_on_linkedin(self):
        try:
            post_text = await self.generate_post()
            image_path = "linkedin_image.jpg" if os.path.exists("linkedin_image.jpg") else None
            
            await self.post_page.goto("https://www.linkedin.com/feed/")
            await self.post_page.locator("button:has-text('Start a post')").click()
            await self.post_page.wait_for_selector("div[role='dialog']")
            
            if image_path:
                await self.post_page.click('.artdeco-modal__content button[aria-label="Add a photo"]')
                await self.post_page.wait_for_selector('#media-editor-file-selector__file-input')
                await self.post_page.set_input_files('#media-editor-file-selector__file-input', image_path)
                await self.post_page.wait_for_selector('button[aria-label="Next"]:not([disabled])')
                await self.post_page.click('button[aria-label="Next"]:not([disabled])')
                await self.human_like_delay()
            
            await self.post_page.wait_for_selector('.ql-editor', state='visible')
            await self.post_page.fill('.ql-editor', post_text)
            await self.post_page.wait_for_selector('button.share-actions__primary-action:has-text("Post")')
            await self.post_page.click('button.share-actions__primary-action:has-text("Post")')
            await self.post_page.wait_for_selector('.artdeco-modal__content', state='detached')
            
            self.actions_today["posts"] += 1
            logger.info(f"Posted successfully (Total today: {self.actions_today['posts']})")
            
        except Exception as e:
            logger.error(f"Error posting to LinkedIn: {str(e)}")
            raise
    
    async def run_activities(self):
        try:
            await self.start_browser()
            
            while True:
                self.reset_counters_if_new_day()
                
                if not await self.is_work_hours():
                    logger.info("Outside work hours, sleeping...")
                    await asyncio.sleep(3600)
                    continue
                
                # Run scheduled tasks
                tasks = []
                
                if self.actions_today["posts"] < CONFIG["daily_posts"]:
                    tasks.append(self.manage_posts())
                
                if self.actions_today["comments"] < CONFIG["daily_comments"]:
                    tasks.append(self.manage_comments())
                
                if self.actions_today["connections"] < CONFIG["daily_connections"]:
                    tasks.append(self.manage_connections())
                
                tasks.append(self.like_posts())
                
                await asyncio.gather(*tasks)
                await asyncio.sleep(60)
                
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}")
        finally:
            await self.close_browser()
    
    async def manage_posts(self):
        """Handle scheduled posting"""
        try:
            now = datetime.now()
            target_times = [
                now.replace(hour=random.randint(9, 11), minute=random.randint(0, 59)),
                now.replace(hour=random.randint(14, 16), minute=random.randint(0, 59))
            ]
            
            for target in target_times:
                if now < target:
                    wait = (target - now).total_seconds()
                    logger.info(f"Waiting {wait//60} minutes until next post")
                    await asyncio.sleep(wait)
                
                if self.actions_today["posts"] < CONFIG["daily_posts"]:
                    await self.post_on_linkedin()
                    await asyncio.sleep(3600)  # Wait before next check
        
        except Exception as e:
            logger.error(f"Error in post management: {str(e)}")
    
    async def manage_comments(self):
        """Handle scheduled commenting"""
        try:
            while self.actions_today["comments"] < CONFIG["daily_comments"]:
                await self.comment_on_post()
                wait = random.randint(10*60, 30*60)
                logger.info(f"Next comment in {wait//60} minutes")
                await asyncio.sleep(wait)
        
        except Exception as e:
            logger.error(f"Error in comment management: {str(e)}")
    
    async def manage_connections(self):
        """Handle scheduled connecting"""
        try:
            while self.actions_today["connections"] < CONFIG["daily_connections"]:
                await self.process_connections()
                wait = random.randint(15*60, 45*60)
                logger.info(f"Next connection in {wait//60} minutes")
                await asyncio.sleep(wait)
        
        except Exception as e:
            logger.error(f"Error in connection management: {str(e)}")
    
    async def like_posts(self):
        """Continuous liking of posts"""
        try:
            while True:
                if self.actions_today["likes"] >= 100:
                    await asyncio.sleep(3600)
                    continue
                
                await self.like_random_posts()
                wait = random.randint(CONFIG["like_interval_min"]*30, CONFIG["like_interval_min"]*90)
                logger.info(f"Next like session in {wait//60} minutes")
                await asyncio.sleep(wait)
        
        except Exception as e:
            logger.error(f"Error in like management: {str(e)}")
    
    async def like_random_posts(self):
        """Like random posts in feed"""
        try:
            await self.feed_page.goto("https://www.linkedin.com/feed/")
            await self.feed_page.wait_for_selector('div.feed-shared-update-v2')
            
            posts = await self.feed_page.locator('div.feed-shared-update-v2').all()
            if not posts:
                logger.warning("No posts found to like")
                return
            
            likes = random.randint(CONFIG["like_per_session_min"], CONFIG["like_per_session_max"])
            for _ in range(min(likes, len(posts))):
                post = random.choice(posts)
                await post.scroll_into_view_if_needed()
                await self.human_like_delay()
                
                like_button = post.locator('button[aria-label="React Like"]').first
                if await like_button.count() > 0:
                    await like_button.click()
                    self.actions_today["likes"] += 1
                    logger.info(f"Liked post (Total today: {self.actions_today['likes']})")
                    await self.human_like_delay()
        
        except Exception as e:
            logger.error(f"Error liking posts: {str(e)}")
    
    async def comment_on_post(self):
        """Comment on a random post"""
        try:
            await self.feed_page.goto("https://www.linkedin.com/feed/")
            await self.feed_page.wait_for_selector('div.feed-shared-update-v2')
            
            posts = await self.feed_page.locator('div.feed-shared-update-v2').all()
            if not posts:
                logger.warning("No posts found to comment on")
                return
            
            post = random.choice(posts)
            await post.scroll_into_view_if_needed()
            await self.human_like_delay()
            
            # Like the post (70% chance)
            if random.random() < 0.7:
                like_button = post.locator('button[aria-label="React Like"]').first
                if await like_button.count() > 0:
                    await like_button.click()
                    await self.human_like_delay()
            
            # Comment
            comment_button = post.locator('button[aria-label*="Comment"]')
            if await comment_button.count() > 0:
                await comment_button.click()
                await self.human_like_delay()
                
                comments = [
                    "Great perspective!",
                    "Thanks for sharing this!",
                    "Interesting insights!",
                    "This is really helpful, thank you!",
                    "I agree with this approach."
                ]
                
                if random.random() < 0.6:  # Quick comment
                    quick_comments = post.locator('.comments-quick-comments__list-item button')
                    if await quick_comments.count() > 0:
                        await random.choice(await quick_comments.all()).click()
                else:  # Custom comment
                    editor = post.locator('.comments-comment-box__editor')
                    await editor.fill(random.choice(comments))
                
                await post.locator('button.comments-comment-box__submit-button').click()
                self.actions_today["comments"] += 1
                logger.info(f"Commented on post (Total today: {self.actions_today['comments']})")
                await self.human_like_delay()
        
        except Exception as e:
            logger.error(f"Error commenting on post: {str(e)}")
            raise
    
    async def process_connections(self):
        """Process connection requests and invitations"""
        try:
            # Accept pending connections (30% chance)
            if random.random() < 0.3:
                await self.network_page.goto("https://www.linkedin.com/mynetwork/invitation-manager/")
                accept_buttons = self.network_page.locator('button[aria-label^="Accept"]')
                count = await accept_buttons.count()
                
                if count > 0:
                    to_accept = min(count, random.randint(1, 3))
                    for i in range(to_accept):
                        await accept_buttons.nth(i).click()
                        await self.human_like_delay()
                        self.actions_today["connections"] += 1
            
            # Send new connections (70% chance)
            if random.random() < 0.7:
                await self.network_page.goto("https://www.linkedin.com/mynetwork/")
                connect_buttons = self.network_page.locator('button:has-text("Connect")')
                count = await connect_buttons.count()
                
                if count > 0:
                    to_send = min(count, random.randint(1, 3))
                    for i in range(to_send):
                        await connect_buttons.nth(i).click()
                        await self.human_like_delay()
                        
                        if random.random() < 0.3:  # Add note (30% chance)
                            try:
                                add_note = self.network_page.locator('button:has-text("Add a note")')
                                if await add_note.count() > 0:
                                    await add_note.click()
                                    await self.human_like_delay()
                                    
                                    notes = [
                                        "Hi, I'd love to connect and learn more about your work!",
                                        "Hello! Let's connect and share insights in our field.",
                                        "Hi there! Would be great to connect and network."
                                    ]
                                    
                                    note_box = self.network_page.locator('.send-invite__custom-message')
                                    await note_box.fill(random.choice(notes))
                                    await self.human_like_delay()
                            except:
                                pass
                        
                        send_button = self.network_page.locator('button:has-text("Send")')
                        if await send_button.count() > 0:
                            await send_button.click()
                        else:
                            skip_button = self.network_page.locator('button:has-text("Send without a note")')
                            if await skip_button.count() > 0:
                                await skip_button.click()
                        
                        await self.human_like_delay()
                        self.actions_today["connections"] += 1
        
        except Exception as e:
            logger.error(f"Error processing connections: {str(e)}")
            raise

if __name__ == "__main__":
    bot = LinkedInBot()
    asyncio.run(bot.run_activities())