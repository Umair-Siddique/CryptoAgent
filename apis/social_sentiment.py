import requests
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
import json

# Add Supabase client
try:
    from supabase import create_client, Client
except ImportError:
    print("Supabase client not found. Installing...")
    os.system("pip install supabase")
    from supabase import create_client, Client

load_dotenv()

# Environment variables
LUNAR_CRUSH_API = os.getenv('LUNAR_CRUSH_API')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = os.getenv('USER_ID')  # Add your user ID from Supabase auth

def get_today_timestamp():
    """Get today's date as Unix timestamp"""
    today = datetime.now(timezone.utc)
    return int(today.timestamp())

async def fetch_social_sentiment(token, start_date=None, end_date=None):
    """Fetch social sentiment data for a given token"""
    
    # Use today's date if not provided
    if start_date is None:
        start_date = get_today_timestamp()
    if end_date is None:
        end_date = get_today_timestamp()
    
    url = f"https://lunarcrush.com/api4/public/topic/{token}/posts/v1?start={start_date}&end={end_date}"
    
    headers = {
        'Authorization': f'Bearer {LUNAR_CRUSH_API}'
    }
    
    print(f"Fetching from URL: {url}")
    print(f"Using API key: {'Set' if LUNAR_CRUSH_API else 'Not set'}")
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            print(f"Received {len(data.get('data', []))} posts from API")
            return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def safe_int(value, default=0):
    """Safely convert value to integer"""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def safe_float(value, default=0.0):
    """Safely convert value to float"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def filter_posts(posts_data):
    """Filter posts according to criteria based on actual API response structure"""
    if not posts_data:
        print("No posts data received")
        return []
    
    if 'data' not in posts_data:
        print(f"Unexpected data structure: {list(posts_data.keys()) if isinstance(posts_data, dict) else type(posts_data)}")
        return []
    
    filtered_posts = []
    
    print(f"Processing {len(posts_data['data'])} posts...")
    
    for post in posts_data['data']:
        # Extract required fields and convert to proper data types
        followers = safe_int(post.get('creator_followers', 0))
        interactions_24h = safe_int(post.get('interactions_24h', 0))
        interactions_total = safe_int(post.get('interactions_total', 0))
        sentiment = safe_float(post.get('post_sentiment', 0))
        
        # Apply filters based on your criteria:
        # followers ≥ 50k
        # interactions_24h ≥ 30k OR interactions_total ≥ 60k
        # sentiment >= 2.8 or <= 2.2
        if (followers >= 50000 and  # followers ≥ 50k
            (interactions_24h >= 30000 or interactions_total >= 60000) and  # interactions_24h ≥ 30k OR interactions_total ≥ 60k
            (sentiment >= 2.8 or sentiment <= 2.2)):  # sentiment >= 2.8 or <= 2.2
            
            filtered_post = {
                'user_id': USER_ID,
                'token': posts_data.get('config', {}).get('topic', ''),  # Get token from config
                'post_title': post.get('post_title', ''),
                'post_link': post.get('post_link', ''),
                'post_sentiment': sentiment,
                'creator_followers': followers,
                'interactions_24h': interactions_24h,
                'interactions_total': interactions_total
            }
            filtered_posts.append(filtered_post)
    
    return filtered_posts

def store_in_supabase(posts, token_symbol=None):
    """Store filtered posts in Supabase with duplicate handling"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Supabase credentials not found in environment variables")
        return False
    
    if not USER_ID:
        print("USER_ID not found in environment variables")
        return False
    
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        if not posts:
            print("No posts to store")
            return False
        
        # Check for existing posts to avoid duplicates
        existing_links = set()
        for post in posts:
            post_link = post.get('post_link', '')
            if post_link:
                # Check if this post already exists
                result = supabase.table('posts').select('post_link').eq('post_link', post_link).execute()
                if result.data:
                    existing_links.add(post_link)
        
        # Filter out posts that already exist
        new_posts = [post for post in posts if post.get('post_link', '') not in existing_links]
        
        if not new_posts:
            print(f"All {len(posts)} posts already exist in database")
            return True
        
        if existing_links:
            print(f"Skipping {len(existing_links)} existing posts, inserting {len(new_posts)} new posts")
        
        # Insert only new posts
        result = supabase.table('posts').insert(new_posts).execute()
        print(f"Successfully stored {len(new_posts)} new posts in Supabase")
        return True
            
    except Exception as e:
        print(f"Error storing data in Supabase: {e}")
        return False

def main():
    """Main function to run the social sentiment analysis"""
    
    # Get token from command line argument
    if len(sys.argv) < 2:
        print("Usage: python social_sentiment.py <token>")
        print("Example: python social_sentiment.py bitcoin")
        sys.exit(1)
    
    token = sys.argv[1].lower()
    print(f"Fetching social sentiment data for {token}...")
    
    # Fetch data
    data = fetch_social_sentiment(token)
    
    if data is None:
        print("Failed to fetch data from LunarCrush API")
        sys.exit(1)
    
    print(f"Raw data received: {len(data.get('data', []))} posts")
    
    # Filter posts
    filtered_posts = filter_posts(data)
    print(f"Filtered posts: {len(filtered_posts)} posts meet criteria")
    
    # Store in Supabase
    if filtered_posts:
        success = store_in_supabase(filtered_posts)
        if success:
            print("Data successfully processed and stored!")
        else:
            print("Failed to store data in Supabase")
    else:
        print("No posts meet the filtering criteria")

if __name__ == "__main__":
    main()