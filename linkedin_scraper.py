import os
import time
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

def login(page):
    """
    Logs into LinkedIn using credentials from .env file.
    """
    page.goto("https://www.linkedin.com/login")
    page.fill("#username", os.getenv("LINKEDIN_USER"))
    page.fill("#password", os.getenv("LINKEDIN_PASS"))
    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle")
    print("Logged in successfully.")

def scrape_profile_posts(page, profile_url):
    """
    Navigates to the user's profile and scrapes their recent posts.
    """
    print(f"Navigating to profile: {profile_url}")
    page.goto(f"{profile_url}/recent-activity/all/")
    page.wait_for_load_state("networkidle")
    time.sleep(5) # Wait for posts to load

    # Scroll down to load more posts
    for _ in range(3): # Adjust the range to scroll more or less
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(3)

    soup = BeautifulSoup(page.content(), "html.parser")
    post_elements = soup.find_all("div", class_="update-components-text")
    
    posts = [post.get_text(strip=True) for post in post_elements]
    print(f"Scraped {len(posts)} posts.")
    return posts

if __name__ == '__main__':
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Set headless=True for production
        page = browser.new_page()
        
        login(page)
        
        # Replace with your actual LinkedIn profile URL
        linkedin_profile_url = os.getenv("LINKEDIN_PROFILE_URL") 
        if not linkedin_profile_url:
            raise ValueError("LINKEDIN_PROFILE_URL not set in .env file")

        scraped_posts = scrape_profile_posts(page, linkedin_profile_url)
        
        # Save the scraped posts to a file for the agent to use as a style guide
        with open("style_guide.txt", "w", encoding="utf-8") as f:
            for post in scraped_posts:
                f.write(post + "\n" + "="*20 + "\n")

        browser.close()
