#!/usr/bin/env python3
"""
Run Semantic Search Embedding Pipeline
This script runs the embedding pipeline to create embeddings for TODAY'S social posts and AI reports only.
"""

import asyncio
import os
from dotenv import load_dotenv

# Import the embedding pipeline
from apis.embedding_pipeline import EmbeddingPipeline

load_dotenv()

async def main():
    """Main function to run the embedding pipeline"""
    try:
        # Validate environment variables
        from config import Config
        Config.validate()
        
        print("🔐 Environment variables validated successfully!")
        
        # Initialize the embedding pipeline
        pipeline = EmbeddingPipeline()
        
        # Get actual tokens from your data instead of hardcoded ones
        print(" Checking available tokens in your data...")
        
        # Get tokens from posts table
        posts_response = pipeline.supabase.table('posts').select('token_name').execute()
        post_tokens = set()
        if posts_response.data:
            for post in posts_response.data:
                if post.get('token_name'):
                    post_tokens.add(post['token_name'])
        
        # Get tokens from ai_reports table
        reports_response = pipeline.supabase.table('ai_reports').select('token_name').execute()
        report_tokens = set()
        if reports_response.data:
            for report in reports_response.data:
                if report.get('token_name'):
                    report_tokens.add(report['token_name'])
        
        # Combine all tokens
        all_tokens = list(post_tokens.union(report_tokens))
        
        if not all_tokens:
            print("❌ No tokens found in your data!")
            print("Please run your data collection scripts first to populate posts and ai_reports tables.")
            return
        
        print(f"✅ Found tokens: {', '.join(all_tokens)}")
        
        # Use all available tokens
        token_names = all_tokens
        
        print(f" Processing TODAY'S embeddings for tokens: {', '.join(token_names)}")
        
        # Run the pipeline
        success = await pipeline.run_embedding_pipeline(token_names)
        
        if success:
            print("\n✅ Embedding pipeline completed successfully!")
            print("📅 Only processed data created today.")
            print("🔍 You can now use the embeddings for semantic search.")
        else:
            print("\n⚠️ Embedding pipeline completed with some errors.")
            print("Check the logs above for details.")
            
    except Exception as e:
        print(f"❌ Failed to run embedding pipeline: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
