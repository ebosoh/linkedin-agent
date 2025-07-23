



import os
import google.generativeai as genai
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import re
from googleapiclient.discovery import build

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
    Cleans the generated post text by removing markdown-like formatting.
    """
    # Remove bold markers (**)
    text = text.replace('**', '')
    # Remove list item markers (* ) at the beginning of lines
    text = re.sub(r'^\s*\*\s+', '', text, flags=re.MULTILINE)
    # Remove heading markers (#, ##, etc.) at the beginning of lines
    text = re.sub(r'^\s*#+\s+', '', text, flags=re.MULTILINE)
    return text.strip()

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
    7.  Use emojis to enhance the post's visual appeal, but keep it professional.
    8.  Ensure the post is suitable for a professional audience on LinkedIn.  
    9.  Avoid using markdown-like formatting (e.g., **bold**, *italic*).  
    10. Ensure the post is concise and to the point, avoiding unnecessary fluff.
    11. Use a friendly and approachable tone, as if speaking directly to a colleague.
    12. Ensure the post is informative and adds value to my network.
    13. Avoid using overly technical jargon unless necessary for clarity.
    14. Ensure the post is original and does not plagiarize any content from the article.
    15. The post should be engaging and encourage discussion among my connections.
    16. Use a conversational tone, as if speaking directly to my LinkedIn connections.
    17. Ensure the post is well-structured with a clear beginning, middle, and end.
    18. Avoid using excessive exclamation marks or overly dramatic language.
    19. Ensure the post is free of grammatical errors and typos.
    20. The post should be suitable for a professional audience and reflect my expertise in the field.
    21. Ensure the post is relevant to my professional interests and expertise.
    22. The post should be engaging and encourage discussion among my connections.  
    23. Ensure the post is optimized for reading on LinkedIn, with short paragraphs and clear formatting.    """
    
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
        else:
            print("No new, unposted articles were found.")
    else:
        print("No articles found for the given query.")

