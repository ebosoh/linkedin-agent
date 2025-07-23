



import os
import google.generativeai as genai
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
from googleapiclient.discovery import build

load_dotenv()

# Configure the Gemini API key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

def search_for_news(query, num_results=5, retries=3, delay=10):
    """
    Searches for a given query using the Google Custom Search API with retries.
    """
    print(f"Searching for news with query: {query}")
    for i in range(retries):
        try:
            service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
            res = service.cse().list(q=query, cx=GOOGLE_CSE_ID, num=num_results).execute()
            urls = [item['link'] for item in res.get('items', [])]
            print(f"Found {len(urls)} results.")
            return urls
        except Exception as e:
            print(f"An error occurred during Google Custom Search (Attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("All retries failed.")
                return []
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

def generate_linkedin_post(article_content, style_guide_text):
    """
    Generates a LinkedIn post using the Gemini API.
    """
    print("Generating LinkedIn post with Gemini...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    **Objective:** Write a 400-word LinkedIn post based on the provided news article.

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
    1.  Create an engaging and professional LinkedIn post of approximately 400 words.
    2.  The post should summarize the key points of the article.
    3.  Incorporate my personal writing style from the examples provided.
    4.  Include relevant hashtags at the end.
    5.  Start with a strong hook to grab attention.
    6.  End with a question or a call to action to encourage engagement.
    """
    
    response = model.generate_content(prompt)
    print("Post generation complete.")
    return response.text

if __name__ == '__main__':
    # Set stdout to utf-8 to handle emojis
    import sys
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    company_topic = "latest developments in large language models"
    search_query = f"{company_topic} site:techcrunch.com OR site:wired.com OR site:venturebeat.com"

    article_urls = search_for_news(search_query)

    if article_urls:
        article_content = scrape_article_content(article_urls[0])
        
        if article_content:
            try:
                with open("style_guide.txt", "r", encoding="utf-8") as f:
                    style_guide = f.read()
            except FileNotFoundError:
                print("Error: style_guide.txt not found. Please run linkedin_scraper.py first.")
                style_guide = ""

            linkedin_post = generate_linkedin_post(article_content, style_guide)
            
            print("\n--- GENERATED LINKEDIN POST ---\n")
            print(linkedin_post)
            
            with open("generated_post.txt", "w", encoding="utf-8") as f:
                f.write(linkedin_post)
            print("\nPost saved to generated_post.txt")
    else:
        print("No articles found for the given query.")

