#!/usr/bin/env python3
"""
Semantic Search Retriever
This module retrieves the most investable coin based on AI reports and social posts,
then fetches comprehensive token data from all tables for today's date.
"""

import asyncio
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, date, timedelta
from dotenv import load_dotenv

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

class TokenRetriever:
    def __init__(self):
        # Initialize OpenAI client
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
        
        # Get today's date for filtering
        self.today_utc = datetime.now(timezone.utc).date()
        print(f"📅 Retrieving data for: {self.today_utc} (UTC)")
    
    async def create_embedding(self, text: str) -> Optional[List[float]]:
        """Create embedding for query text"""
        try:
            if not text or len(text.strip()) == 0:
                return None
            
            response = self.openai_client.embeddings.create(
                input=text,
                model="text-embedding-3-small",
                dimensions=1536
            )
            
            embedding = response.data[0].embedding
            return embedding
            
        except Exception as e:
            print(f"❌ Error creating embedding: {e}")
            return None

    def calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            if len(vec1) != len(vec2):
                return 0.0
            
            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # Calculate magnitudes
            magnitude1 = sum(a * a for a in vec1) ** 0.5
            magnitude2 = sum(b * b for b in vec2) ** 0.5
            
            # Avoid division by zero
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = dot_product / (magnitude1 * magnitude2)
            return max(0.0, min(1.0, similarity))  # Clamp between 0 and 1
            
        except Exception as e:
            print(f"❌ Error calculating cosine similarity: {e}")
            return 0.0
    
    async def semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic search to find most relevant content"""
        try:
            print(f"🔍 Performing semantic search for: '{query}'")
            
            # Create embedding for the query
            query_embedding = await self.create_embedding(query)
            if not query_embedding:
                print("❌ Failed to create query embedding")
                return []
            
            print(f"✅ Created query embedding with {len(query_embedding)} dimensions")
            
            # Try using the function first
            try:
                response = self.supabase.rpc(
                    'match_embeddings',
                    {
                        'query_embedding': query_embedding,
                        'match_threshold': 0.6,
                        'match_count': top_k
                    }
                ).execute()
                
                if response.data:
                    print(f"✅ Found {len(response.data)} similar embeddings using function")
                    return response.data
                else:
                    print("ℹ️ No results found with function, trying lower threshold...")
                    response = self.supabase.rpc(
                        'match_embeddings',
                        {
                            'query_embedding': query_embedding,
                            'match_threshold': 0.3,
                            'match_count': top_k
                        }
                    ).execute()
                    
                    if response.data:
                        print(f"✅ Found {len(response.data)} similar embeddings with lower threshold")
                        return response.data
                        
            except Exception as func_error:
                print(f"⚠️ Function failed: {func_error}")
                print("🔄 Falling back to direct SQL...")
            
            # Fallback to direct SQL with manual similarity calculation
            print("🔄 Using direct SQL with manual similarity calculation...")
            # FIX: Only get today's embeddings
            response = self.supabase.table('embeddings').select('*').gte('created_at', f"{self.today_utc}T00:00:00Z").lt('created_at', f"{self.today_utc + timedelta(days=1)}T00:00:00Z").execute()
            
            if not response.data:
                print(f"ℹ️ No embeddings found for today ({self.today_utc})")
                return []
            
            print(f"📅 Found {len(response.data)} embeddings from today")
            
            # Calculate similarity manually
            results = []
            for item in response.data:
                if item.get('embedding_vector'):
                    # Calculate cosine similarity manually
                    similarity = self.calculate_cosine_similarity(query_embedding, item['embedding_vector'])
                    if similarity > 0.3:  # Threshold
                        item['similarity'] = similarity
                        results.append(item)
            
            # Sort by similarity and take top_k
            results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
            final_results = results[:top_k]
            
            print(f"✅ Found {len(final_results)} similar embeddings using direct SQL")
            
            # Add debug info for each result
            for i, result in enumerate(final_results):
                similarity = result.get('similarity', 0)
                content_type = result.get('content_type', 'unknown')
                token = result.get('token_symbol', 'unknown')
                print(f"  {i+1}. {content_type} ({token}) - Similarity: {similarity:.3f}")
            
            return final_results
            
        except Exception as e:
            print(f"❌ Error in semantic search: {e}")
            print("🔄 Falling back to content-based search...")
            return await self.fallback_search(query, top_k)

    async def fallback_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Fallback search method when vector search fails"""
        try:
            # FIX: Only get today's embeddings
            response = self.supabase.table('embeddings').select('*').gte('created_at', f"{self.today_utc}T00:00:00Z").lt('created_at', f"{self.today_utc + timedelta(days=1)}T00:00:00Z").limit(100).execute()
            
            if not response.data:
                print(f"ℹ️ No embeddings found for today ({self.today_utc})")
                return []
            
            # Simple keyword matching as fallback
            query_lower = query.lower()
            relevant_content = []
            
            for embedding in response.data:
                content_text = embedding.get('content_text', '').lower()
                relevance_score = 0
                
                # Score based on keyword matches
                keywords = ['investable', 'cryptocurrency', 'fundamentals', 'sentiment', 'growth', 'potential']
                for keyword in keywords:
                    if keyword in content_text:
                        relevance_score += 1
                
                if relevance_score > 0:
                    embedding['relevance_score'] = relevance_score
                    relevant_content.append(embedding)
            
            # Sort by relevance score and return top results
            relevant_content.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            return relevant_content[:top_k]
            
        except Exception as e:
            print(f"❌ Fallback search also failed: {e}")
            return []

    def get_token_from_content(self, content: Dict[str, Any]) -> Optional[str]:
        """Extract token symbol from content"""
        if content.get('content_type') == 'social_post':
            return content.get('token_symbol')
        elif content.get('content_type') == 'ai_report':
            return content.get('token_symbol')
        return None
    
    async def get_top_investable_token(self) -> Optional[str]:
        """Find the most investable token based on semantic search"""
        try:
            print("🎯 Finding most investable token...")
            
            # Define investment-focused queries
            queries = [
                "most investable cryptocurrency with strong fundamentals",
                "cryptocurrency investment opportunity positive sentiment",
                "best crypto to invest in with growth potential",
                "cryptocurrency with strong community and development"
            ]
            
            all_results = []
            
            # Perform semantic search for each query
            for query in queries:
                print(f"🔍 Searching: '{query}'")
                results = await self.semantic_search(query, top_k=10)
                if results:
                    all_results.extend(results)
                    print(f"✅ Found {len(results)} results for query")
            
            if not all_results:
                print("ℹ️ No search results found")
                return await self.fallback_token_selection()
            
            # Count token occurrences and calculate average similarity scores
            token_counts = {}
            token_scores = {}
            
            for result in all_results:
                token = result.get('token_symbol')
                if token:
                    if token not in token_counts:
                        token_counts[token] = 0
                        token_scores[token] = []
                    
                    token_counts[token] += 1
                    # Get similarity score from the result
                    similarity = result.get('similarity', 0)
                    token_scores[token].append(similarity)
            
            if not token_counts:
                print("ℹ️ No tokens found in search results")
                return await self.fallback_token_selection()
            
            # Find token with highest count and best average similarity
            best_token = None
            best_score = 0
            
            for token, count in token_counts.items():
                avg_similarity = sum(token_scores[token]) / len(token_scores[token])
                combined_score = count * avg_similarity  # Weight by both count and similarity
                
                print(f"🏆 {token}: {count} mentions, avg similarity: {avg_similarity:.3f}, score: {combined_score:.3f}")
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_token = token
            
            print(f"🏆 Top investable token: {best_token} (score: {best_score:.3f})")
            return best_token
            
        except Exception as e:
            print(f"❌ Error finding top investable token: {e}")
            return await self.fallback_token_selection()

    async def fallback_token_selection(self) -> Optional[str]:
        """Fallback method to select token when semantic search fails"""
        try:
            print("🔄 Using fallback token selection...")
            
            # Get all available tokens from embeddings
            response = self.supabase.table('embeddings').select('token_symbol').execute()
            
            if not response.data:
                print("ℹ️ No embeddings found")
                return None
            
            # Count token occurrences
            token_counts = {}
            for item in response.data:
                token = item.get('token_symbol')
                if token:
                    token_counts[token] = token_counts.get(token, 0) + 1
            
            if not token_counts:
                print("ℹ️ No tokens found in embeddings")
                return None
            
            # Select token with most data
            top_token = max(token_counts.items(), key=lambda x: x[1])
            print(f"🏆 Selected token by data volume: {top_token[0]} ({top_token[1]} embeddings)")
            
            return top_token[0]
            
        except Exception as e:
            print(f"❌ Fallback token selection failed: {e}")
            return None
    
    async def get_comprehensive_token_data(self, token_symbol: str) -> Dict[str, Any]:
        """Get comprehensive token data from all tables for today"""
        try:
            print(f"📊 Fetching comprehensive data for {token_symbol}...")
            
            comprehensive_data = {
                'token_symbol': token_symbol,
                'date': self.today_utc.isoformat(),
                'social_posts': [],
                'ai_reports': [],
                'trading_signals': [],
                'fundamental_grade': [],
                'hourly_ohlcv': [],
                'daily_ohlcv': []
            }
            
            # 1. Get social posts for today
            print(f"📱 Fetching social posts for {token_symbol}...")
            posts_response = self.supabase.table('posts').select('*').eq('token', token_symbol).execute()
            if posts_response.data:
                for post in posts_response.data:
                    if post.get('ingested_at'):
                        try:
                            post_date = datetime.fromisoformat(post['ingested_at'].replace('Z', '+00:00')).date()
                            if post_date == self.today_utc:
                                comprehensive_data['social_posts'].append(post)
                        except:
                            continue
            print(f"✅ Found {len(comprehensive_data['social_posts'])} social posts for today")
            
            # 2. Get AI reports for today
            print(f"🤖 Fetching AI reports for {token_symbol}...")
            reports_response = self.supabase.table('ai_reports').select('*').eq('token_symbol', token_symbol).execute()
            if reports_response.data:
                for report in reports_response.data:
                    if report.get('created_at'):
                        try:
                            report_date = datetime.fromisoformat(report['created_at'].replace('Z', '+00:00')).date()
                            if report_date == self.today_utc:
                                comprehensive_data['ai_reports'].append(report)
                        except:
                            continue
            print(f"✅ Found {len(comprehensive_data['ai_reports'])} AI reports for today")
            
            # 3. Get trading signals for today
            print(f"📈 Fetching trading signals for {token_symbol}...")
            signals_response = self.supabase.table('trading_signals').select('*').eq('token_symbol', token_symbol).execute()
            if signals_response.data:
                for signal in signals_response.data:
                    if signal.get('created_at'):
                        try:
                            signal_date = datetime.fromisoformat(signal['created_at'].replace('Z', '+00:00')).date()
                            if signal_date == self.today_utc:
                                comprehensive_data['trading_signals'].append(signal)
                        except:
                            continue
            print(f"✅ Found {len(comprehensive_data['trading_signals'])} trading signals for today")
            
            # 4. Get fundamental grade (latest data, not date-filtered)
            print(f"📊 Fetching fundamental grade for {token_symbol}...")
            fundamental_response = self.supabase.table('fundamental_grade').select('*').eq('token_symbol', token_symbol).execute()
            if fundamental_response.data:
                comprehensive_data['fundamental_grade'] = fundamental_response.data
            print(f"✅ Found {len(comprehensive_data['fundamental_grade'])} fundamental grade records")
            
            # 5. Get daily OHLCV data for today
            print(f"💰 Fetching daily OHLCV for {token_symbol}...")
            daily_ohlcv_response = self.supabase.table('daily_ohlcv').select('*').eq('token_symbol', token_symbol).execute()
            if daily_ohlcv_response.data:
                for ohlcv in daily_ohlcv_response.data:
                    if ohlcv.get('date_time'):
                        try:
                            ohlcv_date = datetime.fromisoformat(ohlcv['date_time'].replace('Z', '+00:00')).date()
                            if ohlcv_date == self.today_utc:
                                comprehensive_data['daily_ohlcv'].append(ohlcv)
                        except:
                            continue
            print(f"✅ Found {len(comprehensive_data['daily_ohlcv'])} daily OHLCV records for today")
            
            # 6. Get hourly OHLCV data for today
            print(f"⏰ Fetching hourly OHLCV for {token_symbol}...")
            hourly_ohlcv_response = self.supabase.table('hourly_ohlcv').select('*').eq('token_symbol', token_symbol).execute()
            if hourly_ohlcv_response.data:
                for ohlcv in hourly_ohlcv_response.data:
                    if ohlcv.get('date_time'):
                        try:
                            ohlcv_date = datetime.fromisoformat(ohlcv['date_time'].replace('Z', '+00:00')).date()
                            if ohlcv_date == self.today_utc:
                                comprehensive_data['hourly_ohlcv'].append(ohlcv)
                        except:
                            continue
            print(f"✅ Found {len(comprehensive_data['hourly_ohlcv'])} hourly OHLCV records for today")
            
            print(f"✅ Retrieved comprehensive data for {token_symbol}")
            return comprehensive_data
            
        except Exception as e:
            print(f"❌ Error getting comprehensive token data: {e}")
            return {}
    
    def print_comprehensive_data(self, data: Dict[str, Any]):
        """Print comprehensive token data in a structured way"""
        if not data:
            print("❌ No data to display")
            return
        
        print(f"\n{'='*100}")
        print(f"🏆 COMPREHENSIVE ANALYSIS FOR {data['token_symbol'].upper()}")
        print(f"📅 Date: {data['date']}")
        print(f"{'='*100}")
        
        # 1. SOCIAL SENTIMENT ANALYSIS
        if data['social_posts']:
            print(f"\n📱 SOCIAL SENTIMENT ANALYSIS ({len(data['social_posts'])} posts)")
            print("=" * 60)
            total_sentiment = sum(post.get('post_sentiment', 0) for post in data['social_posts'])
            avg_sentiment = total_sentiment / len(data['social_posts']) if data['social_posts'] else 0
            total_followers = sum(post.get('creator_followers', 0) for post in data['social_posts'])
            total_interactions = sum(post.get('interactions_total', 0) for post in data['social_posts'])
            
            print(f"📝 SUMMARY:")
            print(f"  • Average Sentiment: {avg_sentiment:.3f}")
            print(f"  • Total Followers: {total_followers:,}")
            print(f"  • Total Interactions: {total_interactions:,}")
            
            print(f"\n📝 TOP POSTS:")
            for i, post in enumerate(data['social_posts'][:5], 1):  # Show top 5
                print(f"  {i}. {post.get('post_title', 'No title')[:100]}...")
                print(f"     Sentiment: {post.get('post_sentiment', 'N/A')} | Followers: {post.get('creator_followers', 'N/A'):,} | Interactions: {post.get('interactions_total', 'N/A'):,}")
        else:
            print(f"\n📱 SOCIAL SENTIMENT ANALYSIS")
            print("=" * 60)
            print("  ⚠️ No social posts found for today")
        
        # 2. AI ANALYSIS REPORTS
        if data['ai_reports']:
            print(f"\n🤖 AI ANALYSIS REPORTS ({len(data['ai_reports'])} reports)")
            print("=" * 60)
            for i, report in enumerate(data['ai_reports'], 1):
                print(f"📋 Report {i}:")
                print(f"  • Token ID: {report.get('token_id', 'N/A')}")
                print(f"  • Token Name: {report.get('token_name', 'N/A')}")
                print(f"  • Investment Analysis: {report.get('investment_analysis_pointer', 'N/A')[:150]}...")
                if report.get('deep_dive'):
                    print(f"  • Deep Dive: {report.get('deep_dive', 'N/A')[:150]}...")
                if report.get('code_review'):
                    print(f"  • Code Review: {report.get('code_review', 'N/A')[:150]}...")
        else:
            print(f"\n🤖 AI ANALYSIS REPORTS")
            print("=" * 60)
            print("  ⚠️ No AI reports found for today")
        
        # 3. TRADING SIGNALS
        if data['trading_signals']:
            print(f"\n📈 TRADING SIGNALS ({len(data['trading_signals'])} signals)")
            print("=" * 60)
            for i, signal in enumerate(data['trading_signals'], 1):
                print(f"📊 Signal {i}:")
                print(f"  • Trading Signal: {signal.get('trading_signal', 'N/A')}")
                print(f"  • Token Trend: {signal.get('token_trend', 'N/A')}")
                print(f"  • Trading Returns: {signal.get('trading_signals_returns', 'N/A')}")
                print(f"  • Holding Returns: {signal.get('holding_returns', 'N/A')}")
                print(f"  • TM Trader Grade: {signal.get('tm_trader_grade', 'N/A')}")
                print(f"  • TM Investor Grade: {signal.get('tm_investor_grade', 'N/A')}")
                if signal.get('tm_link'):
                    print(f"  • TM Link: {signal.get('tm_link', 'N/A')}")
        else:
            print(f"\n📈 TRADING SIGNALS")
            print("=" * 60)
            print("  ⚠️ No trading signals found for today")
        
        # 4. FUNDAMENTAL ANALYSIS
        if data['fundamental_grade']:
            print(f"\n📊 FUNDAMENTAL ANALYSIS")
            print("=" * 60)
            for grade in data['fundamental_grade']:
                print(f"🏆 Overall Grade: {grade.get('fundamental_grade', 'N/A')}")
                print(f"📋 Grade Class: {grade.get('fundamental_grade_class', 'N/A')}")
                print(f"🏢 Community Score: {grade.get('community_score', 'N/A')}")
                print(f"🏢 Exchange Score: {grade.get('exchange_score', 'N/A')}")
                print(f"💼 VC Score: {grade.get('vc_score', 'N/A')}")
                print(f"🪙 Tokenomics Score: {grade.get('tokenomics_score', 'N/A')}")
                print(f"🏢 DeFi Scanner Score: {grade.get('defi_scanner_score', 'N/A')}")
        else:
            print(f"\n📊 FUNDAMENTAL ANALYSIS")
            print("=" * 60)
            print("  ⚠️ No fundamental grade data found")
        
        # 5. PRICE DATA - DAILY OHLCV
        if data['daily_ohlcv']:
            print(f"\n💰 DAILY PRICE DATA")
            print("=" * 60)
            for ohlcv in data['daily_ohlcv']:
                print(f"📅 Date: {ohlcv.get('date_time', 'N/A')}")
                print(f"  • Open: ${ohlcv.get('open_price', 'N/A')}")
                print(f"  • High: ${ohlcv.get('high_price', 'N/A')}")
                print(f"  • Low: ${ohlcv.get('low_price', 'N/A')}")
                print(f"  • Close: ${ohlcv.get('close_price', 'N/A')}")
                print(f"  • Volume: {ohlcv.get('volume', 'N/A'):,}")
        else:
            print(f"\n💰 DAILY PRICE DATA")
            print("=" * 60)
            print("  ⚠️ No daily OHLCV data found for today")
        
        # 6. PRICE DATA - HOURLY OHLCV
        if data['hourly_ohlcv']:
            print(f"\n⏰ HOURLY PRICE DATA ({len(data['hourly_ohlcv'])} records)")
            print("=" * 60)
            # Show last 5 hourly records
            for ohlcv in data['hourly_ohlcv'][-5:]:
                print(f"🕐 {ohlcv.get('date_time', 'N/A')}")
                print(f"  • Open: ${ohlcv.get('open_price', 'N/A')}")
                print(f"  • High: ${ohlcv.get('high_price', 'N/A')}")
                print(f"  • Low: ${ohlcv.get('low_price', 'N/A')}")
                print(f"  • Close: ${ohlcv.get('close_price', 'N/A')}")
                print(f"  • Volume: {ohlcv.get('volume', 'N/A'):,}")
        else:
            print(f"\n⏰ HOURLY PRICE DATA")
            print("=" * 60)
            print("  ⚠️ No hourly OHLCV data found for today")
        
        # 7. INVESTMENT RECOMMENDATION
        print(f"\n{'='*100}")
        print("🎯 INVESTMENT RECOMMENDATION")
        print("=" * 60)
        
        # Calculate overall metrics
        has_social_data = len(data['social_posts']) > 0
        has_ai_data = len(data['ai_reports']) > 0
        has_trading_data = len(data['trading_signals']) > 0
        has_fundamental_data = len(data['fundamental_grade']) > 0
        has_price_data = len(data['daily_ohlcv']) > 0 or len(data['hourly_ohlcv']) > 0
        
        print(f"📊 DATA AVAILABILITY:")
        print(f"  • Social Sentiment: {'✅' if has_social_data else '❌'}")
        print(f"  • AI Analysis: {'✅' if has_ai_data else '❌'}")
        print(f"  • Trading Signals: {'✅' if has_trading_data else '❌'}")
        print(f"  • Fundamental Grade: {'✅' if has_fundamental_data else '❌'}")
        print(f"  • Price Data: {'✅' if has_price_data else '❌'}")
        
        if has_social_data:
            avg_sentiment = sum(post.get('post_sentiment', 0) for post in data['social_posts']) / len(data['social_posts'])
            if avg_sentiment > 2.5:
                sentiment_rating = "POSITIVE"
                sentiment_emoji = "💚"
            elif avg_sentiment > 1.5:
                sentiment_rating = "NEUTRAL"
                sentiment_emoji = "🟡"
            else:
                sentiment_rating = "NEGATIVE"
                sentiment_emoji = "🔴"
            
            print(f"\n📊 SENTIMENT ANALYSIS:")
            print(f"  • Average Sentiment: {sentiment_rating} ({avg_sentiment:.3f}) {sentiment_emoji}")
        
        # Generate recommendation
        print(f"\n📊 RECOMMENDATION:")
        if has_social_data and has_ai_data and has_fundamental_data:
            if avg_sentiment > 2.5:
                print(f"  💚 STRONG BUY: {data['token_symbol'].upper()} shows excellent potential")
                print(f"     High social sentiment + AI analysis + fundamental data available")
            elif avg_sentiment > 1.5:
                print(f"  🟡 MODERATE BUY: {data['token_symbol'].upper()} shows good potential")
                print(f"     Moderate social sentiment with comprehensive data available")
            else:
                print(f"  🔴 CAUTION: {data['token_symbol'].upper()} shows weak sentiment")
                print(f"     Low social sentiment despite available data")
        elif has_social_data or has_ai_data:
            print(f"  🟡 CONSIDER: {data['token_symbol'].upper()} has partial data")
            print(f"     Some analysis available but incomplete dataset")
        else:
            print(f"  ⚠️ INSUFFICIENT DATA: {data['token_symbol'].upper()}")
            print(f"     Limited data available for analysis")
        
        print(f"\n{'='*100}")
    
    async def run_comprehensive_analysis(self) -> bool:
        """Run the complete comprehensive token analysis"""
        try:
            print("🚀 Starting Comprehensive Token Analysis")
            print(f"{'='*50}")
            
            # Step 1: Find most investable token
            top_token = await self.get_top_investable_token()
            if not top_token:
                print("❌ Could not determine top investable token")
                return False
            
            # Step 2: Get comprehensive data for that token
            comprehensive_data = await self.get_comprehensive_token_data(top_token)
            if not comprehensive_data:
                print(f"❌ Could not retrieve data for {top_token}")
                return False
            
            # Step 3: Print comprehensive analysis
            self.print_comprehensive_data(comprehensive_data)
            
            print(f"\n✅ Comprehensive analysis completed for {top_token}")
            return True
            
        except Exception as e:
            print(f"❌ Comprehensive analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Main function to run the comprehensive token analysis"""
    try:
        retriever = TokenRetriever()
        await retriever.run_comprehensive_analysis()
    except Exception as e:
        print(f"❌ Failed to start token retriever: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
