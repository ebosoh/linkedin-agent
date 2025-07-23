import os
import time
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

def login_and_post(post_content):
    """
    Logs into LinkedIn and posts the given content.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Set to True for production
        page = browser.new_page()
        
        try:
            print("Logging into LinkedIn...")
            page.goto("https://www.linkedin.com/login")
            page.fill("#username", os.getenv("LINKEDIN_USER"))
            page.fill("#password", os.getenv("LINKEDIN_PASS"))
            page.click("button[type='submit']")
            page.wait_for_url("**/feed/**", timeout=90000)
            print("Login successful.")

            # --- Post to Personal Profile ---
            print("Navigating to create a post...")
            # Use a more robust text-based selector
            page.click('button:has-text("Start a post")')
            
            print("Typing post content...")
            editor_selector = "div.ql-editor"
            page.wait_for_selector(editor_selector, timeout=30000)
            page.fill(editor_selector, post_content)
            
            post_button_selector = "button.share-actions__primary-action"
            page.wait_for_selector(post_button_selector, timeout=30000)
            page.click(post_button_selector)
            print("Post published to personal profile.")
            time.sleep(5)

            # --- Post to Company Page (Optional) ---
            company_page_url = os.getenv("LINKEDIN_COMPANY_PAGE_URL")
            if company_page_url:
                print(f"Navigating to company page: {company_page_url}")
                page.goto(company_page_url)
                page.wait_for_load_state("networkidle")

                print("Creating post on company page...")
                page.click("button.share-box-feed-entry__trigger")
                page.wait_for_selector(editor_selector, timeout=30000)
                page.fill(editor_selector, post_content)
                
                page.click(post_button_selector)
                print("Post published to company page.")
                time.sleep(5)

        except Exception as e:
            print(f"An error occurred: {e}")
            page.screenshot(path="linkedin_post_error.png")
            print("Saved screenshot to linkedin_post_error.png for debugging.")
        finally:
            browser.close()

if __name__ == '__main__':
    try:
        with open("generated_post.txt", "r", encoding="utf-8") as f:
            post_to_publish = f.read()
        
        if post_to_publish:
            login_and_post(post_to_publish)
        else:
            print("generated_post.txt is empty. No post to publish.")

    except FileNotFoundError:
        print("Error: generated_post.txt not found. Please run agent.py first to generate a post.")
