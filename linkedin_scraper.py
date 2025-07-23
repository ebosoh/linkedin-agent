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
    try:
        page.goto("https://www.linkedin.com/login")
        page.fill("#username", os.getenv("LINKEDIN_USER"))
        page.fill("#password", os.getenv("LINKEDIN_PASS"))
        page.click("button[type='submit']")
        
        # Wait for navigation to the feed, which indicates a successful login
        page.wait_for_url("**/feed/**", timeout=60000)
        print("Logged in successfully.")

        # Check for and close the messaging pop-up
        try:
            messaging_popup = page.locator(".msg-overlay-bubble-header")
            if messaging_popup.is_visible(timeout=5000):
                print("Closing messaging pop-up.")
                messaging_popup.get_by_label("Dismiss").click()
        except Exception as e:
            print("No messaging pop-up found or could not close it.")

    except TimeoutError:
        print("Timeout after login attempt. Saving screenshot to debug_screenshot.png")
        page.screenshot(path="debug_screenshot.png")
        raise



def scrape_profile_posts(page, profile_url):
    """
    Navigates to the user's profile and scrapes their recent posts.
    """
    print(f"Navigating to profile: {profile_url}")
    page.goto(f"{profile_url}/recent-activity/all/")
    page.wait_for_load_state("domcontentloaded", timeout=60000)
    time.sleep(5) # Wait for posts to render

    # Scroll down to load more posts
    for _ in range(5): # Scroll a bit more to ensure we get enough posts
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(3)

    soup = BeautifulSoup(page.content(), "html.parser")
    # This is a more precise selector based on the debug_page.html analysis
    post_elements = soup.select('div.update-components-text > span.break-words > span[dir="ltr"]')
    
    posts = [post.get_text(strip=True) for post in post_elements]
    
    if not posts:
        print("Could not find any posts with the new selector. Please double-check the HTML structure.")
        # Save the HTML again if it fails, to ensure we have the latest version
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(page.content())

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
