"""
Hacker News AI Scraper

Setup Instructions:
1. Ensure you have Python 3 installed.
2. Install the required external libraries by running:
   pip install requests beautifulsoup4
3. Run the script:
   python scrape.py
   
This script scrapes up to 50 pages of Hacker News front page AND the
/newest feed for fresh posts. It extracts AI-related posts using a broad
keyword list, sorts them by points, displays them in the terminal neatly,
and saves the structured results to 'ai_news.json'.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin

def fetch_url(url):
    """
    Fetches the HTML content of a given URL.
    Includes proper headers to simulate a real browser request.
    """
    
    # Adding a standard User-Agent header to avoid being blocked
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise an exception for bad status codes
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return None

def parse_hn_page(html_content, base_url):
    """
    Parses the Hacker News HTML content and extracts posts data.
    Also looks for the 'More' button to find the next page URL.
    Safely handles missing elements.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    posts = []
    
    # HN posts are structured in rows. The title and link are in a <tr> with class 'athing'.
    # The subtext (points, author, time) is in the immediate next sibling <tr>.
    athing_rows = soup.find_all('tr', class_='athing')
    
    for row in athing_rows:
        try:
            # 1. Extract headline and link
            titleline = row.find('span', class_='titleline')
            if not titleline:
                continue
            
            link_tag = titleline.find('a')
            if not link_tag:
                continue
                
            headline = link_tag.text.strip()
            link = link_tag.get('href')
            
            # Handle relative HN links (e.g., Ask HN or item?id=...)
            if link.startswith('item?id='):
                link = f"https://news.ycombinator.com/{link}"
            
            # 2. Extract points and author from the next sibling row
            subtext_row = row.find_next_sibling('tr')
            if not subtext_row:
                continue
                
            subtext = subtext_row.find('td', class_='subtext')
            if not subtext:
                continue
                
            # Extract points safely
            score_span = subtext.find('span', class_='score')
            points = 0
            if score_span:
                points_text = score_span.text.replace(' points', '').replace(' point', '').strip()
                points = int(points_text) if points_text.isdigit() else 0
                
            # Extract author safely
            author_tag = subtext.find('a', class_='hnuser')
            author = author_tag.text.strip() if author_tag else 'unknown'
            
            # Add extracted post to list
            posts.append({
                'headline': headline,
                'link': link,
                'points': points,
                'author': author
            })
            
        except Exception as e:
            # Safely handle any parsing anomalies for a single row without breaking the whole process
            print(f"Warning: Failed to parse a row - {e}")
            continue
            
    # Find next page URL using the 'More' link
    next_url = None
    more_link = soup.find('a', class_='morelink')
    if more_link and more_link.get('href'):
        next_url = urljoin(base_url, more_link.get('href'))
            
    return posts, next_url

def filter_ai_posts(posts):
    """
    Filters posts to return only those containing AI-related keywords.
    Uses word boundaries for short acronyms like 'AI' and 'ML' to avoid
    false positives (e.g., matching 'ai' inside 'pain' or 'ml' inside 'html').
    """
    # Keywords that need word-boundary regex matching to avoid false positives
    boundary_keywords = ['ai', 'ml', 'llm', 'agi', 'rlhf']

    # Keywords safe for simple substring matching
    plain_keywords = [
        # Companies & Products
        'openai', 'anthropic', 'deepmind', 'google gemini', 'mistral',
        'hugging face', 'stability ai', 'midjourney', 'dall-e', 'dall·e',
        'sora', 'perplexity', 'groq', 'cohere', 'inflection',
        # Models & Architectures
        'gpt', 'gpt-4', 'gpt-5', 'claude', 'gemini', 'llama', 'falcon',
        'mixtral', 'phi-', 'qwen', 'grok', 'palm', 'bert', 'transformer',
        'diffusion model', 'foundation model', 'language model',
        # Core AI / ML Concepts
        'artificial intelligence', 'machine learning', 'deep learning',
        'neural network', 'neural', 'reinforcement learning',
        'natural language processing', 'nlp', 'computer vision',
        'generative ai', 'gen ai', 'large language', 'multimodal',
        'fine-tuning', 'fine tuning', 'pre-training', 'pretraining',
        'prompt engineering', 'prompt injection', 'context window',
        'embedding', 'vector database', 'retrieval augmented', 'rag',
        'attention mechanism', 'inference', 'training data',
        # AI Safety & Ethics
        'ai safety', 'ai alignment', 'alignment', 'ai ethics',
        'ai regulation', 'ai policy', 'responsible ai', 'ai risk',
        'hallucination', 'ai bias', 'superintelligence',
        # AI Applications
        'ai agent', 'ai coding', 'ai assistant', 'ai tool', 'ai model',
        'copilot', 'cursor', 'devin', 'chatbot', 'chatgpt',
        'text-to-image', 'text to image', 'text-to-video', 'text to video',
        'image generation', 'ai generated', 'ai-generated',
        'autonomous', 'agentic',
        # Infrastructure
        'gpu cluster', 'tpu', 'ai chip', 'ai hardware', 'inference chip',
        'nvidia', 'cuda', 'pytorch', 'tensorflow', 'jax',
        # Industry trends
        'ai startup', 'ai funding', 'ai investment', 'ai lab',
    ]

    filtered_posts = []
    for post in posts:
        headline_lower = post['headline'].lower()
        is_ai_related = False

        # Check boundary keywords with regex to avoid false matches
        for keyword in boundary_keywords:
            if re.search(rf'\b{re.escape(keyword)}\b', headline_lower):
                is_ai_related = True
                break

        # Check plain keywords with simple substring match
        if not is_ai_related:
            for keyword in plain_keywords:
                if keyword in headline_lower:
                    is_ai_related = True
                    break

        if is_ai_related:
            filtered_posts.append(post)

    return filtered_posts

def main():
    all_ai_posts = []
    seen_links = set()  # Track seen links to avoid duplicates across feeds
    max_pages = 50

    # Define the feeds to scrape:
    # 'news' = front page (popular, high-points posts)
    # 'newest' = freshest submissions (may have lower points but more volume)
    feeds = [
        ("https://news.ycombinator.com/news",   "Front Page"),
        ("https://news.ycombinator.com/newest", "Newest"),
    ]

    print(f"Starting Hacker News scraper...")
    print(f"Feeds: Front Page + Newest | Max pages per feed: {max_pages}")

    # 1. Scrape multiple feeds and multiple pages using the 'More' link
    for base_url, feed_label in feeds:
        print(f"\n--- Scraping '{feed_label}' feed ---")
        current_url = base_url
        page_count = 0
        
        while current_url and page_count < max_pages:
            page_count += 1
            print(f"  Scraping {feed_label} page {page_count}...")
            html = fetch_url(current_url)

            if html:
                posts, next_url = parse_hn_page(html, current_url)
                ai_posts = filter_ai_posts(posts)

                # Deduplicate: only add posts we haven't seen before
                for post in ai_posts:
                    if post['link'] not in seen_links:
                        seen_links.add(post['link'])
                        all_ai_posts.append(post)

                current_url = next_url # advance to the next page
            else:
                current_url = None # stop if fetch failed

            # Polite delay between requests to keep the server happy and prevent IP bans
            time.sleep(2)
        
    # 2. Sort results by points (descending)
    all_ai_posts.sort(key=lambda x: x['points'], reverse=True)
    
    # 3. Print neatly in the terminal
    print("\n" + "="*50)
    print("      Top AI-Related Hacker News Posts")
    print("="*50)
    
    if not all_ai_posts:
        print("No AI-related posts found on the first few pages.")
    else:
        for idx, post in enumerate(all_ai_posts, 1):
            print(f"[{idx}] {post['headline']}")
            print(f"    Points: {post['points']} | Author: {post['author']}")
            print(f"    Link: {post['link']}")
            print("-" * 50)
            
    print(f"\nTotal AI posts found: {len(all_ai_posts)}")
    
    # 4. Save to structured JSON file
    json_filename = "ai_news.json"
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            # Pretty-print with indent=4
            json.dump(all_ai_posts, f, indent=4, ensure_ascii=False)
        print(f"Results successfully saved to '{json_filename}'")
    except Exception as e:
        print(f"Failed to save results to JSON: {e}")

if __name__ == "__main__":
    main()
