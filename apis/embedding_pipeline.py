#!/usr/bin/env python3
"""
Semantic Search Embedding Pipeline
This module handles creating and storing embeddings for social posts and AI reports
created TODAY using OpenAI's text-embedding-3-large model (3072 dimensions).
"""

import os
import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, date
from dotenv import load_dotenv
import urllib.parse

try:
    from supabase import create_client, Client
except ImportError:
    print("Supabase client not found. Installing...")
    os.system("pip install supabase")
    from supabase import create_client, Client

try:
    from openai import OpenAI
except ImportError:
    print("OpenAI client not found. Installing...")
    os.system("pip install openai")
    from openai import OpenAI

load_dotenv()

class EmbeddingPipeline:
    def __init__(self):
        # Initialize OpenAI client with new syntax
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("Missing OPENAI_API_KEY environment variable")
        
        # Initialize Supabase client
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        self.user_id = os.getenv('USER_ID')
        
        if not self.supabase_url or not self.supabase_key or not self.user_id:
            raise ValueError("Missing Supabase credentials")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Embedding model configuration
        self.model = "text-embedding-3-small"
        self.dimensions = 1536
        
        # Fix: Use UTC date for consistent comparison
        self.today_utc = datetime.now(timezone.utc).date()
        print(f"📅 Processing embeddings for data created on: {self.today_utc} (UTC)")
    
    async def create_embedding(self, text: str) -> Optional[List[float]]:
        """Create embedding for given text using OpenAI API"""
        try:
            if not text or len(text.strip()) == 0:
                return None
            
            # Truncate text if too long (OpenAI has limits)
            max_tokens = 8000  # Conservative limit for embedding model
            truncated_text = text[:max_tokens * 4]  # Rough estimate: 4 chars per token
            
            # Use new OpenAI API syntax
            response = self.openai_client.embeddings.create(
                input=truncated_text,
                model=self.model,
                dimensions=self.dimensions
            )
            
            embedding = response.data[0].embedding
            print(f"✅ Created embedding with {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            print(f"❌ Error creating embedding: {e}")
            return None
    
    def prepare_social_post_text(self, post: Dict[str, Any]) -> str:
        """Prepare text content from social post for embedding"""
        text_parts = []
        
        # Add post title if available
        if post.get('post_title'):
            text_parts.append(f"Title: {post['post_title']}")
        
        # Add sentiment information
        if post.get('post_sentiment') is not None:
            sentiment = post['post_sentiment']
            if sentiment >= 2.8:
                sentiment_label = "Very Positive"
            elif sentiment >= 2.0:
                sentiment_label = "Positive"
            elif sentiment <= 2.2:
                sentiment_label = "Negative"
            else:
                sentiment_label = "Very Negative"
            text_parts.append(f"Sentiment: {sentiment_label} ({sentiment})")
        
        # Add engagement metrics
        if post.get('creator_followers'):
            text_parts.append(f"Creator Followers: {post['creator_followers']:,}")
        
        if post.get('interactions_24h'):
            text_parts.append(f"24h Interactions: {post['interactions_24h']:,}")
        
        if post.get('interactions_total'):
            text_parts.append(f"Total Interactions: {post['interactions_total']:,}")
        
        # Add token context
        if post.get('token'):
            text_parts.append(f"Token: {post['token']}")
        
        return " | ".join(text_parts)
    
    def prepare_ai_report_text(self, report: Dict[str, Any]) -> str:
        """Prepare text content from AI report for embedding"""
        text_parts = []
        
        # Add token information
        if report.get('token_symbol'):
            text_parts.append(f"Token: {report['token_symbol']}")
        
        if report.get('token_name'):
            text_parts.append(f"Token Name: {report['token_name']}")
        
        # Add analysis sections
        if report.get('investment_analysis_pointer'):
            text_parts.append(f"Investment Analysis Pointer: {report['investment_analysis_pointer']}")
        
        if report.get('investment_analysis'):
            text_parts.append(f"Investment Analysis: {report['investment_analysis']}")
        
        if report.get('deep_dive'):
            text_parts.append(f"Deep Dive: {report['deep_dive']}")
        
        if report.get('code_review'):
            text_parts.append(f"Code Review: {report['code_review']}")
        
        return " | ".join(text_parts)
    
    async def process_todays_social_posts_embeddings(self, token_name: str) -> bool:
        """Process embeddings for social posts created TODAY for a specific token"""
        try:
            # 🆕 FIX: URL decode the token name if it's encoded
            decoded_token_name = urllib.parse.unquote(token_name)
            if decoded_token_name != token_name:
                print(f" Decoded token name: {token_name} → {decoded_token_name}")
                token_name = decoded_token_name
            
            print(f" Processing TODAY'S social post embeddings for {token_name}...")
            
            # Fetch social posts created today from Supabase
            response = self.supabase.table('posts').select('*').eq('token_name', token_name).execute()
            
            if not response.data:
                print(f"ℹ️ No social posts found for {token_name}")
                return True
            
            print(f"🔍 Found {len(response.data)} total posts for {token_name}")
            
            # Debug: Show all post dates
            print(f"📅 Debug - All post dates for {token_name}:")
            for post in response.data[:5]:  # Show first 5 posts
                print(f"  Post {post['id']}: ingested_at={post.get('ingested_at')}")
            
            # Filter posts created today (using UTC comparison)
            todays_posts = []
            for post in response.data:
                if post.get('ingested_at'):
                    try:
                        # Parse the ingested_at timestamp (it's already in UTC from Supabase)
                        created_date = datetime.fromisoformat(post['ingested_at'].replace('Z', '+00:00')).date()
                        
                        # Debug: Show the date comparison
                        print(f"  Post {post['id']}: ingested_at={post['ingested_at']}, parsed_date={created_date}, today_utc={self.today_utc}")
                        
                        if created_date == self.today_utc:
                            todays_posts.append(post)
                            print(f"✅ Post {post['id']} is from today!")
                    except (ValueError, TypeError) as e:
                        print(f"⚠️ Date parsing error for post {post['id']}: {e}")
                        continue
            
            if not todays_posts:
                print(f"ℹ️ No social posts created today (UTC) for {token_name}")
                print(f"  Today's date (UTC): {self.today_utc}")
                print(f"  Tip: Check if your data was created in a different timezone or date")
                return True
            
            print(f"📅 Found {len(todays_posts)} social posts created today (UTC)")
            
            success_count = 0
            for post in todays_posts:
                # Prepare text content
                content_text = self.prepare_social_post_text(post)
                
                # Create embedding
                embedding = await self.create_embedding(content_text)
                if not embedding:
                    print(f"❌ Failed to create embedding for post {post['id']}")
                    continue
                
                # Prepare metadata
                metadata = {
                    'post_id': post['id'],  # Store post ID in metadata
                    'post_title': post.get('post_title'),
                    'post_sentiment': post.get('post_sentiment'),
                    'creator_followers': post.get('creator_followers'),
                    'interactions_24h': post.get('interactions_24h'),
                    'interactions_total': post.get('interactions_total'),
                    'post_link': post.get('post_link'),
                    'created_date': post.get('ingested_at')
                }
                
                # Store embedding in Supabase with DECODED token name
                embedding_data = {
                    'user_id': self.user_id,
                    'content_type': 'social_post',
                    'token_name': token_name,  # 🆕 Now using decoded name
                    'content_text': content_text,
                    'embedding_vector': embedding,
                    'metadata': metadata
                }
                
                result = self.supabase.table('embeddings').insert(embedding_data).execute()
                
                if result.data:
                    success_count += 1
                    print(f"✅ Stored embedding for post {post['id']}")
                else:
                    print(f"❌ Failed to store embedding for post {post['id']}")
            
            print(f"✅ Successfully processed {success_count}/{len(todays_posts)} social post embeddings for {token_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error processing social post embeddings for {token_name}: {e}")
            return False
    
    async def process_todays_ai_reports_embeddings(self, token_name: str) -> bool:
        """Process embeddings for AI reports created TODAY for a specific token"""
        try:
            # 🆕 FIX: URL decode the token name if it's encoded
            decoded_token_name = urllib.parse.unquote(token_name)
            if decoded_token_name != token_name:
                print(f" Decoded token name: {token_name} → {decoded_token_name}")
                token_name = decoded_token_name
            
            print(f" Processing TODAY'S AI report embeddings for {token_name}...")
            
            # Fetch AI reports created today from Supabase
            response = self.supabase.table('ai_reports').select('*').eq('token_name', token_name).execute()
            
            if not response.data:
                print(f"ℹ️ No AI reports found for {token_name}")
                return True
            
            print(f"🔍 Found {len(response.data)} total AI reports for {token_name}")
            
            # Filter reports created today (using UTC comparison)
            todays_reports = []
            for report in response.data:
                if report.get('created_at'):
                    try:
                        # Parse the created_at timestamp (it's already in UTC from Supabase)
                        created_date = datetime.fromisoformat(report['created_at'].replace('Z', '+00:00')).date()
                        
                        # Debug: Show the date comparison
                        print(f" Report {report['id']}: created_at={report['created_at']}, parsed_date={created_date}, today_utc={self.today_utc}")
                        
                        if created_date == self.today_utc:
                            todays_reports.append(report)
                            print(f"✅ Report {report['id']} is from today!")
                    except (ValueError, TypeError) as e:
                        print(f"⚠️ Date parsing error for report {report['id']}: {e}")
                        continue
            
            if not todays_reports:
                print(f"ℹ️ No AI reports created today (UTC) for {token_name}")
                print(f" Tip: Check if your data was created in a different timezone or date")
                return True
            
            print(f"📅 Found {len(todays_reports)} AI reports created today (UTC)")
            
            success_count = 0
            for report in todays_reports:
                # Prepare text content
                content_text = self.prepare_ai_report_text(report)
                
                # Create embedding
                embedding = await self.create_embedding(content_text)
                if not embedding:
                    print(f"❌ Failed to create embedding for AI report {report['id']}")
                    continue
                
                # Prepare metadata
                metadata = {
                    'report_id': report['id'],  # Store report ID in metadata instead
                    'token_symbol': report.get('token_symbol'),
                    'token_name': report.get('token_name'),
                    'investment_analysis_pointer': report.get('investment_analysis_pointer'),
                    'investment_analysis': report.get('investment_analysis'),
                    'deep_dive': report.get('deep_dive'),
                    'code_review': report.get('code_review'),
                    'created_date': report.get('created_at')
                }
                
                # 🆕 FIXED: Store embedding without content_id field
                embedding_data = {
                    'user_id': self.user_id,
                    'content_type': 'ai_report',
                    'token_name': token_name,
                    'content_text': content_text,
                    'embedding_vector': embedding,
                    'metadata': metadata
                    # ✅ No content_id field needed
                }
                
                result = self.supabase.table('embeddings').insert(embedding_data).execute()
                
                if result.data:
                    success_count += 1
                    print(f"✅ Stored embedding for AI report {report['id']}")
                else:
                    print(f"❌ Failed to store embedding for AI report {report['id']}")
            
            print(f"✅ Successfully processed {success_count}/{len(todays_reports)} AI report embeddings for {token_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error processing AI report embeddings for {token_name}: {e}")
            return False
    
    async def process_token_embeddings(self, token_name: str) -> bool:
        """Process embeddings for both social posts and AI reports created TODAY for a token"""
        try:
            print(f"\n{'='*50}")
            print(f"Processing TODAY'S Embeddings for: {token_name}")
            print(f"{'='*50}")
            
            # Process social posts and AI reports in parallel
            social_task = self.process_todays_social_posts_embeddings(token_name)
            ai_report_task = self.process_todays_ai_reports_embeddings(token_name)
            
            social_success, ai_report_success = await asyncio.gather(
                social_task, ai_report_task, return_exceptions=True
            )
            
            # Handle results
            if isinstance(social_success, Exception):
                print(f"❌ Social posts embeddings failed for {token_name}: {social_success}")
                social_success = False
            
            if isinstance(ai_report_success, Exception):
                print(f"❌ AI report embeddings failed for {token_name}: {ai_report_success}")
                ai_report_success = False
            
            overall_success = social_success and ai_report_success
            
            if overall_success:
                print(f"✅ Successfully processed all TODAY'S embeddings for {token_name}")
            else:
                print(f"❌ Failed to process some TODAY'S embeddings for {token_name}")
            
            return overall_success
            
        except Exception as e:
            print(f"❌ Error processing embeddings for {token_name}: {e}")
            return False
    
    async def run_embedding_pipeline(self, token_names: List[str]) -> bool:
        """Run the complete embedding pipeline for multiple tokens (TODAY'S data only)"""
        try:
            print("🚀 Starting Semantic Search Embedding Pipeline")
            print(f" Processing TODAY'S data for tokens: {', '.join(token_names)}")
            print(f" Model: {self.model} ({self.dimensions} dimensions)")
            print(f"🌍 Using UTC date: {self.today_utc}")
            print(f"{'='*50}")
            
            # Process all tokens
            results = []
            for token_name in token_names:
                result = await self.process_token_embeddings(token_name)
                results.append(result)
            
            # Summary
            successful = sum(results)
            total = len(results)
            
            print(f"\n{'='*50}")
            print("EMBEDDING PIPELINE COMPLETED")
            print(f"{'='*50}")
            print(f"✅ Successfully processed: {successful}/{total} tokens")
            print(f"📅 Only processed data created on: {self.today_utc} (UTC)")
            
            if successful == total:
                print("🎉 All token embeddings processed successfully!")
            else:
                print("⚠️ Some token embeddings failed to process")
            
            return successful == total
            
        except Exception as e:
            print(f"❌ Embedding pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Main function for testing the embedding pipeline"""
    try:
        # Test with sample tokens
        pipeline = EmbeddingPipeline()
        token_names = ['BTC', 'ETH', 'ADA']
        await pipeline.run_embedding_pipeline(token_names)
    except Exception as e:
        print(f"❌ Failed to start embedding pipeline: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
