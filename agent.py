import os
import google.generativeai as genai
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import re
from googleapiclient.discovery import build
import sys
import random

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
    Searches for a given query using the Google Custom Search API, filtering for recent results.
    """
    print(f"Searching for news with query: {query}")
    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        # Restrict search to the last 7 days to find recent/trending topics
        res = service.cse().list(q=query, cx=GOOGLE_CSE_ID, num=num_results, dateRestrict='w[1]').execute()
        urls = [item['link'] for item in res.get('items', [])]
        print(f"Found {len(urls)} results from the last 7 days.")
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
    # Remove "Ever" from the beginning of the post
    if text.lstrip().startswith("Ever"):
        text = text.lstrip()[4:].lstrip()
    # Remove any URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove calls to action with links
    text = re.sub(r'Click the link below.*', '', text, flags=re.IGNORECASE)
    return text.strip()

def generate_linkedin_post(article_content, style_guide_text, topic, company, region=None):
    """
    Generates a LinkedIn post using the Gemini API.
    """
    print(f"Generating LinkedIn post on the topic of: {topic} from {company}")
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    region_prompt = ""
    if region == "Africa":
        region_prompt = "The post should also highlight that this is a significant development happening in Africa, showcasing innovation from the continent."

    prompt = f"""
    **Objective:** Write a professional, exciting, and insightful LinkedIn post based on the provided **trending** news article about **{company}** on the topic of **{topic}**. The post must be designed to spark curiosity and engagement.

    **Topic for this post:** {topic}
    **Company in Focus:** {company}
    {region_prompt}

    **Style Guide:**
    Analyze the following posts to understand my personal writing style. Mimic this style in the new post. Pay attention to tone, sentence structure, use of emojis, and hashtags.
    ---
    {style_guide_text}
    ---

    **News Article Content:**
    Here is the content of the news article to summarize and use as the basis for the post. This is from a recent, trending source about {company}.
    ---
    {article_content}
    ---

    **Instructions:**
    1.  **Focus on What's New and Surprising:** The post MUST focus on the absolute latest, most surprising, or counter-intuitive findings from the article, specifically about {company}. Avoid generic explanations. The goal is to make the audience feel like they are learning about a cutting-edge development from a leading company.
    2.  **Create a Very Attractive Hook:** Start with a powerful, provocative, or surprising hook that immediately grabs the reader's attention. This could be a bold statement, a controversial question, or a shocking statistic from the article related to {company}. Do NOT use generic greetings.
    3.  **Avoid Common Knowledge:** Do NOT post about basic concepts (e.g., "What is AI?"). Assume the audience is professional and has foundational knowledge. Focus only on the new, exciting information in the article.
    4.  **Human-Like & Passionate Tone:** Write in a natural, conversational, and authentic voice. It should sound like a passionate expert sharing something exciting, not a robot.
    5.  **Skim-Optimized Readability:** Structure the post for extremely easy reading on mobile. Use **very short paragraphs**, often just a single sentence or two.
    6.  **Formatting:** Use bold text (e.g., `**My Sub-title**`) to create sub-titles for different sections of the post to break up the text and guide the reader.
    7.  **Content:** Summarize the key, surprising points of the article, provide a unique perspective that shows deep insight, and encourage engagement with a thoughtful, open-ended question.
    8.  **Length:** The post must be a maximum of 400 words. This is a strict limit.
    9.  **Emojis & Hashtags:** Incorporate relevant emojis to add personality and include relevant hashtags at the end.
    10. **No Links or CTAs:** Do NOT include any URLs or calls-to-action like 'Click the link below' in the post body.
    11. **Final Polish:** Ensure the post is free of grammatical errors and typos.
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
            page.goto("https://www.linkedin.com/login", wait_until='domcontentloaded')
            
            # Wait for the username field to be ready and fill it
            username_selector = "#username"
            page.wait_for_selector(username_selector, state='visible', timeout=30000)
            page.fill(username_selector, os.getenv("LINKEDIN_USER"))
            time.sleep(random.uniform(1, 3))  # Add a random delay

            # Wait for the password field to be ready and fill it
            password_selector = "#password"
            page.wait_for_selector(password_selector, state='visible', timeout=30000)
            page.fill(password_selector, os.getenv("LINKEDIN_PASS"))
            time.sleep(random.uniform(1, 2))  # Add a random delay
            
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
            # Wait for the button to be enabled before clicking
            page.wait_for_selector(f"{post_button_selector}:not([disabled])", timeout=30000)
            page.click(post_button_selector)
            print("Post published to personal profile.")
            time.sleep(5) # Wait for post to complete

        except Exception as e:
            print(f"An error occurred: {e}")
            try:
                page.screenshot(path="linkedin_post_error.png")
                print("Saved screenshot to linkedin_post_error.png for debugging.")
            except Exception as screenshot_error:
                print(f"Failed to take screenshot: {screenshot_error}")
        finally:
            browser.close()

def generate_search_queries(topics, companies, african_countries):
    """
    Generates a shuffled list of search queries, including topic-only, company-specific, and African news.
    """
    queries = []
    # Add broader, non-company-specific queries for each topic
    for topic in topics:
        # Occasionally add an African country to the topic search
        if random.random() < 0.3: # 30% chance to add an African country
            country = random.choice(african_countries)
            queries.append(f"trending news on '{topic}' in {country}")
        else:
            queries.append(f"trending news on '{topic}'")

    # Add company-specific queries
    for company in companies:
        # To keep it focused, let's randomly pick a few topics for each company
        selected_topics = random.sample(topics, k=min(len(topics), 3)) # Pick up to 3 topics
        for topic in selected_topics:
            # Occasionally add an African country to the company search
            if random.random() < 0.3: # 30% chance to add an African country
                country = random.choice(african_countries)
                queries.append(f"trending news from {company} on '{topic}' in {country}")
            else:
                queries.append(f"trending news from {company} on '{topic}'")

    random.shuffle(queries)
    print(f"Generated {len(queries)} unique search queries.")
    return queries

def find_and_process_article(search_queries):
    """
    Iterates through search queries to find a unique, unposted article and processes it.
    """
    for query in search_queries:
        # Extract topic and company from the query for the generator
        topic_match = re.search(r"on '([^']+)'", query)
        topic = topic_match.group(1) if topic_match else "a relevant topic"
        
        company_match = re.search(r"from (\w+)", query)
        company = company_match.group(1) if company_match else "a leading company"
        
        region = "Africa" if "in" in query else None

        article_urls = search_for_news(query)
        if not article_urls:
            time.sleep(random.uniform(1, 3)) # Wait a bit before the next query
            continue

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

                linkedin_post = generate_linkedin_post(article_content, style_guide, topic, company, region=region)
                cleaned_post = clean_post_text(linkedin_post)
                
                print("\n--- GENERATED LINKEDIN POST ---\n")
                print(cleaned_post)
                
                with open("generated_post.txt", "w", encoding="utf-8") as f:
                    f.write(cleaned_post)
                print("\nPost saved to generated_post.txt")

                log_posted_article(unique_article_url)
                print(f"Logged {unique_article_url} to posted_articles.log")

                print("\n--- POSTING TO LINKEDIN ---")
                login_and_post(cleaned_post)
                return True # Indicate success
            else:
                # If scraping fails, log it and try the next URL/query
                print(f"Could not scrape content from {unique_article_url}, trying next.")
                log_posted_article(unique_article_url) # Log to avoid trying it again
    
    return False # Indicate that no article was posted

if __name__ == '__main__':
    # Set stdout to utf-8 to handle emojis
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    research_topics = [
        "AI agents", "Agentic systems", "Workflow Automation", "Autonomous Agents",
        "Large Language Models", "Artificial Intelligence", "Machine Learning", 
        "Deep Learning", "Natural Language Processing (NLP)", "Multi-agent systems",
        "Human-in-the-loop automation", "Robotic Process Automation (RPA)", "AI-driven automation"
    ]

    leading_companies = [
        # North American Tech & AI Leaders
        "Google", "Microsoft", "Amazon", "Meta", "Apple", "IBM", "Oracle", "Salesforce", "Tesla", "Waymo",
        # Hardware & Semiconductor Titans
        "NVIDIA", "Intel", "AMD", "TSMC", "ASML",
        # Chinese AI Giants
        "Baidu", "Alibaba", "Tencent", "Huawei", "ByteDance", "SenseTime", "Megvii",
        # Enterprise & Data Platforms
        "Palantir", "Snowflake", "Databricks", "Adobe",
        # Other Global Innovators
        "SAP", "Samsung", "UiPath"
    ]

    african_countries = [
        "Nigeria", "South Africa", "Kenya", "Ghana", "Egypt", "Rwanda", "Ethiopia", "Morocco", "Senegal", "Uganda"
    ]

    # Generate a dynamic and shuffled list of search queries
    queries = generate_search_queries(research_topics, leading_companies, african_countries)
    
    # Try to find and post an article from the generated queries
    success = find_and_process_article(queries)

    if not success:
        print("Could not find and post a new article after trying all queries.")
