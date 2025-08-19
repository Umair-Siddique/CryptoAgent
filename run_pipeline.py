#!/usr/bin/env python3
"""
Main script to run the complete crypto data pipeline.
This script will:
1. Fetch altcoin tokens from Token Metrics API using category and exchange filters
2. Store token metadata in Supabase
3. Fetch social posts for each token and store them in Supabase
"""

import asyncio
import sys
from config import Config
from data_processor import CryptoDataProcessor
from apis.social_sentiment import fetch_social_sentiment, filter_posts, store_in_supabase

async def main():
    """Run the complete data pipeline"""
    try:
        # Validate configuration
        Config.validate()
        print("Configuration validated successfully")
        
        # Initialize processor
        processor = CryptoDataProcessor()
        
        # Run the pipeline with altcoin filtering
        await processor.process_all_tokens(
            limit=Config.TOP_TOKENS_LIMIT,
            category=Config.TOKEN_CATEGORY,
            exchange=Config.TOKEN_EXCHANGE
        )
        
        # Fetch social posts for each token
        await fetch_social_posts_for_tokens(processor)
        
        print("\nPipeline completed successfully!")
        
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Pipeline failed: {e}")
        sys.exit(1)

async def fetch_social_posts_for_tokens(processor):
    """Fetch social posts for all tokens stored in the database"""
    try:
        # Get the most recent tokens from Supabase
        result = processor.supabase.table('tokens').select('token_symbol').order('created_at', desc=True).limit(Config.TOP_TOKENS_LIMIT).execute()
        
        if not result.data:
            print("No tokens found in database to fetch social posts for")
            return
        
        print(f"\n{'='*50}")
        print("Fetching social posts for tokens...")
        print(f"{'='*50}")
        
        for token_record in result.data:
            token_symbol = token_record.get('token_symbol', '').lower()
            if not token_symbol:
                continue
                
            print(f"\nProcessing social posts for {token_symbol.upper()}...")
            
            # Fetch social sentiment data
            social_data = fetch_social_sentiment(token_symbol)
            
            if social_data is None:
                print(f"❌ Failed to fetch social data for {token_symbol.upper()}")
                continue
            
            print(f"�� Raw data received: {len(social_data.get('data', []))} posts")
            
            # Filter posts based on criteria
            filtered_posts = filter_posts(social_data)
            print(f"🔍 Filtered posts: {len(filtered_posts)} posts meet criteria")
            
            # Store filtered posts in Supabase
            if filtered_posts:
                success = store_in_supabase(filtered_posts)
                if success:
                    print(f"✅ Successfully stored {len(filtered_posts)} social posts for {token_symbol.upper()}")
                else:
                    print(f"❌ Failed to store social posts for {token_symbol.upper()}")
            else:
                print(f"ℹ️ No social posts meet the filtering criteria for {token_symbol.upper()}")
        
        print(f"\n{'='*50}")
        print("Social posts processing completed!")
        print(f"{'='*50}")
        
    except Exception as e:
        print(f"Error fetching social posts: {e}")

if __name__ == "__main__":
    asyncio.run(main())