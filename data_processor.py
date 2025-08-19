import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any
from dotenv import load_dotenv

# Import our API modules
from apis.token_metrics import TokenMetricsAPI
from apis.social_sentiment import fetch_social_sentiment, filter_posts, store_in_supabase

# Add Supabase client
try:
    from supabase import create_client, Client
except ImportError:
    print("Supabase client not found. Installing...")
    os.system("pip install supabase")
    from supabase import create_client, Client

load_dotenv()

# Environment variables
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = os.getenv('USER_ID')

class CryptoDataProcessor:
    def __init__(self):
        self.token_metrics_api = TokenMetricsAPI()
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    async def get_tokens(self, limit: int = 3, page: int = 1, category: str = None, exchange: str = None) -> List[Dict]:
        """Get tokens from Token Metrics API using /v2/tokens endpoint with filtering"""
        try:
            tokens = await self.token_metrics_api.get_tokens(limit, page, category, exchange)
            if tokens:
                print(f"Successfully fetched {len(tokens)} tokens")
                return tokens
            else:
                print("Failed to fetch tokens")
                return []
        except Exception as e:
            print(f"Error fetching tokens: {e}")
            return []
    
    def store_token_data(self, token_data: Dict) -> bool:
        """Store token metadata in Supabase with new field mapping"""
        try:
            # Map API response fields to database fields
            db_data = {
                'user_id': USER_ID,
                'token_id': token_data.get('TOKEN_ID'),
                'token_name': token_data.get('TOKEN_NAME'),
                'token_symbol': token_data.get('TOKEN_SYMBOL'),
                'current_price': token_data.get('CURRENT_PRICE'),
                'market_cap': token_data.get('MARKET_CAP'),
                'total_volume': token_data.get('TOTAL_VOLUME'),
                'circulating_supply': token_data.get('CIRCULATING_SUPPLY'),
                'total_supply': token_data.get('TOTAL_SUPPLY'),
                'max_supply': token_data.get('MAX_SUPPLY'),
                'fully_diluted_valuation': token_data.get('FULLY_DILUTED_VALUATION'),
                'high_24h': token_data.get('HIGH_24H'),
                'low_24h': token_data.get('LOW_24H'),
                'price_change_percentage_24h_in_currency': token_data.get('PRICE_CHANGE_PERCENTAGE_24H_IN_CURRENCY'),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table('tokens').insert(db_data).execute()
            print(f"Successfully stored token data for {db_data.get('token_symbol', 'N/A')}")
            return True
        except Exception as e:
            print(f"Error storing token data: {e}")
            return False
    
    async def process_social_posts_for_token(self, token_symbol: str) -> bool:
        """Process social posts for a specific token"""
        try:
            print(f"📱 Fetching social posts for {token_symbol.upper()}...")
            
            # Fetch social sentiment data
            social_data = fetch_social_sentiment(token_symbol.lower())
            
            if social_data is None:
                print(f"❌ Failed to fetch social data for {token_symbol.upper()}")
                return False
            
            print(f"�� Raw data received: {len(social_data.get('data', []))} posts")
            
            # Filter posts based on criteria
            filtered_posts = filter_posts(social_data)
            print(f"🔍 Filtered posts: {len(filtered_posts)} posts meet criteria")
            
            # Store filtered posts in Supabase
            if filtered_posts:
                success = store_in_supabase(filtered_posts)
                if success:
                    print(f"✅ Successfully stored {len(filtered_posts)} social posts for {token_symbol.upper()}")
                    return True
                else:
                    print(f"❌ Failed to store social posts for {token_symbol.upper()}")
                    return False
            else:
                print(f"ℹ️ No social posts meet the filtering criteria for {token_symbol.upper()}")
                return True  # Consider this a success since no posts met criteria
                
        except Exception as e:
            print(f"Error processing social posts for {token_symbol}: {e}")
            return False
    
    async def process_all_tokens(self, limit: int = 3, category: str = "altcoin,defi", exchange: str = "binance,coinbase,gate"):
        """Main function to process altcoin tokens and their social posts"""
        print(f"Starting to process {limit} altcoin tokens from /v2/tokens endpoint...")
        print(f"Category filter: {category}")
        print(f"Exchange filter: {exchange}")
        
        # Get tokens from the new endpoint with altcoin filtering
        tokens = await self.get_tokens(limit, 1, category, exchange)
        
        if not tokens:
            print("No tokens to process")
            return
        
        # Process each token - store token data and social posts
        for token in tokens:
            symbol = token.get('TOKEN_SYMBOL', '').upper()
            name = token.get('TOKEN_NAME', 'N/A')
            print(f"\n{'='*50}")
            print(f"Processing token: {symbol} ({name})")
            print(f"{'='*50}")
            
            # Store token metadata
            token_success = self.store_token_data(token)
            if token_success:
                print(f"✅ Successfully stored token data for {symbol}")
                
                # Process social posts for this token
                social_success = await self.process_social_posts_for_token(symbol)
                if social_success:
                    print(f"✅ Successfully processed social posts for {symbol}")
                else:
                    print(f"❌ Failed to process social posts for {symbol}")
            else:
                print(f"❌ Failed to store token data for {symbol}")
            
            print(f"Completed processing for {symbol}")
        
        print(f"\n{'='*50}")
        print("All altcoin tokens and social posts processed successfully!")
        print(f"{'='*50}")

async def main():
    """Main function to run the data processor"""
    try:
        processor = CryptoDataProcessor()
        # Process 3 altcoin tokens from major exchanges with social posts
        await processor.process_all_tokens(
            limit=3,
            category="altcoin,defi",  # Focus on altcoins and DeFi tokens
            exchange="binance,coinbase,gate"  # Major exchanges
        )
    except Exception as e:
        print(f"Error in main: {e}")

if __name__ == "__main__":
    asyncio.run(main())