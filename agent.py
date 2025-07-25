import os
import google.generativeai as genai
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import re
from googleapiclient.discovery import build
import sys

load_dotenv()

# Configure the Gemini API key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

def get_unique_article_url(urls):
    """
    Finds the first URL in a list that has not been previously posted.
    """
    try:
        with open("posted_articles.log", "r") as f:
            posted_urls = {line.strip() for line in f}
    except FileNotFoundError:
        posted_urls = set()

    for url in urls:
        if url not in posted_urls:
            print(f"Found unique article to post: {url}")
            return url
    
    print("No new articles found in the search results.")
    return None

def log_posted_article(url):
    """
    Logs a URL to the posted_articles.log file.
    """
    with open("posted_articles.log", "a") as f:
        f.write(url + "\n")

def search_for_news(query, num_results=10): # Fetch more results to increase chance of finding a unique one
    """
    Searches for a given query using the Google Custom Search API.
    """
    print(f"Searching for news with query: {query}")
    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        res = service.cse().list(q=query, cx=GOOGLE_CSE_ID, num=num_results).execute()
        urls = [item['link'] for item in res.get('items', [])]
        print(f"Found {len(urls)} results.")
        return urls
    except Exception as e:
        print(f"An error occurred during Google Custom Search: {e}")
        return []

def scrape_article_content(url):
    """
    Scrapes the main content of a given article URL.
    """
    print(f"Scraping article: {url}")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=90000, wait_until='domcontentloaded')
            time.sleep(3)
            
            soup = BeautifulSoup(page.content(), "html.parser")
            
            for element in soup(["script", "style", "header", "footer", "nav", "aside"]):
                element.extract()
            
            content = soup.get_text(separator=' ', strip=True)
            content = ' '.join(content.split()[:1500])
            print("Successfully scraped and cleaned article content.")
            return content
    except Exception as e:
        print(f"An error occurred while scraping {url}: {e}")
        return None

def clean_post_text(text):
    """
    Cleans the generated post text by removing unwanted markdown and specific phrases.
    """
    # Remove list item markers (* ) at the beginning of lines
    text = re.sub(r'^\s*\*\s+', '', text, flags=re.MULTILINE)
    # Remove heading markers (#, ##, etc.) at the beginning of lines
    text = re.sub(r'^\s*#+\s+', '', text, flags=re.MULTILINE)
    # Remove horizontal rules and other artifacts
    text = text.replace('***', '')
    text = re.sub(r'^\s*[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Remove variations of "Let's discuss!"
    text = re.sub(r"Let's discuss!.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Let’s discuss!.*", "", text, flags=re.IGNORECASE)
    # Remove generic greetings
    greetings = ["Hey everyone! 👋", "Hey everyone!", "Hi everyone,"]
    for greeting in greetings:
        text = text.replace(greeting, "")
     Remove "Ever" from the beginning of the post
    if text.lstrip().startswith("Ever"):
        text = text.lstrip()[4:].lstrip()
    return text.strip()

def generate_linkedin_post(article_content, style_guide_text):
    """
    Generates a LinkedIn post using the Gemini API.
    """
    print("Generating LinkedIn post with Gemini...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    **Objective:** Write a professional and engaging LinkedIn post based on the provided news article.

    **Style Guide:**
    Analyze the following posts to understand my personal writing style. Mimic this style in the new post. Pay attention to tone, sentence structure, use of emojis, and hashtags.
    ---
    {style_guide_text}
    ---

    **News Article Content:**
    Here is the content of the news article to summarize and use as the basis for the post.
    ---
    {article_content}
    ---

    **Instructions:**
    1.  **Human-Like Tone:** Write in a natural, conversational, and authentic voice. Avoid overly formal or robotic language.
    2.  **Unique Opening:** Start with a unique and compelling hook that grabs the reader's attention immediately. Do NOT use generic greetings like "Hey everyone!" or start with the word "Ever".
    3.  **Skim-Optimized Readability:** Structure the post for extremely easy reading on mobile. Use **very short paragraphs**, often just a single sentence or two.
    4.  **Formatting:** Use bold text (e.g., `**My Sub-title**`) to create sub-titles for different sections of the post to break up the text and guide the reader.
    5.  **Content:** Summarize the key points of the article, provide a unique perspective or insight, and encourage engagement with a thoughtful question.
    6.  **Length:** The post should be approximately 400 words.
    7.  **Emojis & Hashtags:** Incorporate relevant emojis to add personality and include relevant hashtags at the end.
    8.  **Final Polish:** Ensure the post is free of grammatical errors and typos.
    10. Remove any unwanted characters like*** from the article content.

    """
    
    response = model.generate_content(prompt)
    print("Post generation complete.")
    return response.text

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
            
            # Uncheck the "Remember me" checkbox if it's visible
            try:
                remember_me_selector = "#remember-me-prompt-toggle"
                page.wait_for_selector(remember_me_selector, timeout=5000) # Wait up to 5s
                if page.is_checked(remember_me_selector):
                    page.uncheck(remember_me_selector)
                    print("Unchecked 'Remember me' checkbox.")
            except Exception:
                print("'Remember me' checkbox not found, continuing with login.")
                pass

            page.click("button[type='submit']")
            page.wait_for_url("**/feed/**", timeout=90000)
            print("Login successful.")

            # --- Post to Personal Profile ---
            print("Navigating to create a post...")
            page.click('button:has-text("Start a post")')
            
            print("Typing post content...")
            editor_selector = "div.ql-editor"
            page.wait_for_selector(editor_selector, timeout=30000)
            page.fill(editor_selector, post_content)
            
            post_button_selector = "button.share-actions__primary-action"
            page.wait_for_selector(post_button_selector, timeout=30000)
            page.click(post_button_selector)
            print("Post published to personal profile.")
            time.sleep(5) # Wait for post to complete

        except Exception as e:
            print(f"An error occurred: {e}")
            page.screenshot(path="linkedin_post_error.png")
            print("Saved screenshot to linkedin_post_error.png for debugging.")
        finally:
            browser.close()

if __name__ == '__main__':
    # Set stdout to utf-8 to handle emojis
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    company_topic = "latest developments in large language models"
    # Search the entire web, not just specific sites
    search_query = f"{company_topic}"

    article_urls = search_for_news(search_query)

    if article_urls:
        unique_article_url = get_unique_article_url(article_urls)
        
        if unique_article_url:
            article_content = scrape_article_content(unique_article_url)
            
            if article_content:
                try:
                    with open("style_guide.txt", "r", encoding="utf-8") as f:
                        style_guide = f.read()
                except FileNotFoundError:
                    print("Error: style_guide.txt not found. Please run linkedin_scraper.py first.")
                    style_guide = ""

                linkedin_post = generate_linkedin_post(article_content, style_guide)
                cleaned_post = clean_post_text(linkedin_post)
                
                print("\n--- GENERATED LINKEDIN POST ---\n")
                print(cleaned_post)
                
                with open("generated_post.txt", "w", encoding="utf-8") as f:
                    f.write(cleaned_post)
                print("\nPost saved to generated_post.txt")

                # Log the article URL to prevent re-posting
                log_posted_article(unique_article_url)
                print(f"Logged {unique_article_url} to posted_articles.log")

                # Post to LinkedIn
                print("\n--- POSTING TO LINKEDIN ---")
                login_and_post(cleaned_post)
        else:
            print("No new, unposted articles were found.")
    else:
        print("No articles found for the given query.")
