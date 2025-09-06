#!/usr/bin/env python3
"""
Complete Crypto Data Workflow
This script combines both the data collection pipeline and the embeddings pipeline
into a single workflow that:
1. Collects social posts, token metrics, AI reports, and trading signals
2. Automatically runs embeddings on the collected data
3. Uses retriever logic to find top 4 tokens from embeddings search
4. Gets comprehensive token info for today from other tables
5. Passes all info to LLM to get new position recommendations in strict JSON format
"""

import asyncio
import os
import sys
import json
from typing import List, Dict
from dotenv import load_dotenv
import urllib.parse

# Add the top_token_pipeline directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'top_token_pipeline'))

# Import our modules
from apis.token_metrics import TokenMetricsAPI
from apis.social_sentiment import fetch_social_sentiment, filter_posts, store_in_supabase
from apis.ohlcv_storage import OHLCVStorage
from apis.trading_signals import TradingSignalsAPI
from apis.trading_signals_storage import TradingSignalsStorage
from apis.hourly_trading_signals import HourlyTradingSignalsAPI
from apis.hourly_trading_signals_storage import HourlyTradingSignalsStorage
from apis.ai_report import AIReportAPI
from apis.fundamental_grade import FundamentalGradeAPI
from apis.token_data import TokenDataAPI
from apis.embedding_pipeline import EmbeddingPipeline
from apis.resistance_support import ResistanceSupportAPI

# Import retriever logic
from retriever import TokenRetriever

# Import top token pipeline - fix the import path
try:
    from top_token_pipeline.token_pipeline import TopTokenPipeline
except ImportError:
    try:
        from token_pipeline import TopTokenPipeline
    except ImportError:
        print("❌ Could not import TopTokenPipeline. Using dummy tokens instead.")
        TopTokenPipeline = None

# Supabase client
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

class CompleteCryptoWorkflow:
    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY or not USER_ID:
            raise ValueError("Missing required environment variables: SUPABASE_URL, SUPABASE_KEY, USER_ID")
        
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.token_api = TokenMetricsAPI()
        self.ohlcv_storage = OHLCVStorage()
        self.trading_signals_api = TradingSignalsAPI()
        self.trading_signals_storage = TradingSignalsStorage()
        self.hourly_trading_signals_api = HourlyTradingSignalsAPI()
        self.hourly_trading_signals_storage = HourlyTradingSignalsStorage()
        self.ai_report_api = AIReportAPI()
        self.fundamental_grade_api = FundamentalGradeAPI()
        self.token_data_api = TokenDataAPI()
        self.embedding_pipeline = EmbeddingPipeline()
        # Add resistance support API
        self.resistance_support_api = ResistanceSupportAPI()
        
        # Initialize retriever
        try:
            self.retriever = TokenRetriever()
            print("✅ TokenRetriever initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize TokenRetriever: {e}")
            print("⚠️ Retriever analysis will not work without proper OpenAI API key")
            self.retriever = None
        
        # Initialize top token pipeline only if available
        if TopTokenPipeline:
            self.top_token_pipeline = TopTokenPipeline()
        else:
            self.top_token_pipeline = None
    
    async def get_top_10_tokens(self) -> List[Dict]:
        """Get top 10 tokens from the top token pipeline"""
        try:
            if not self.top_token_pipeline:
                print("⚠️ TopTokenPipeline not available. Using dummy tokens.")
                return self.get_dummy_tokens()
            
            print("🔄 Getting top 10 tokens from token pipeline...")
            
            # Run the top token pipeline to get the top 10 tokens
            top_tokens = await self.top_token_pipeline.get_top_10_tokens()
            
            if not top_tokens:
                print("⚠️ No tokens returned from pipeline. Using dummy tokens.")
                return self.get_dummy_tokens()
            
            # Convert TokenData objects to the format expected by the workflow
            tokens = []
            for token_data in top_tokens:
                token = {
                    'TOKEN_ID': token_data.token_id,
                    'TOKEN_NAME': token_data.name,
                    'TOKEN_SYMBOL': token_data.symbol,
                    'CURRENT_PRICE': 0.0,  # Will be fetched by token metrics API
                    'MARKET_CAP': 0,  # Will be fetched by token metrics API
                    'TOTAL_VOLUME': 0,  # Will be fetched by token metrics API
                    'CIRCULATING_SUPPLY': 0,  # Will be fetched by token metrics API
                    'TOTAL_SUPPLY': 0,  # Will be fetched by token metrics API
                    'MAX_SUPPLY': None,  # Will be fetched by token metrics API
                    'FULLY_DILUTED_VALUATION': 0,  # Will be fetched by token metrics API
                    'HIGH_24H': 0.0,  # Will be fetched by token metrics API
                    'LOW_24H': 0.0,  # Will be fetched by token metrics API
                    'PRICE_CHANGE_PERCENTAGE_24H_IN_CURRENCY': 0.0  # Will be fetched by token metrics API
                }
                tokens.append(token)
            
            print(f"✅ Retrieved {len(tokens)} top tokens")
            for token in tokens:
                print(f"   - {token['TOKEN_SYMBOL']} ({token['TOKEN_NAME']}) - ID: {token['TOKEN_ID']}")
            
            return tokens
            
        except Exception as e:
            print(f"❌ Error getting top 10 tokens: {e}")
            print("⚠️ Falling back to dummy tokens...")
            return self.get_dummy_tokens()
    
    def get_dummy_tokens(self) -> List[Dict]:
        """Get dummy data for BTC, ETH, ADA (fallback)"""
        return [
            {
                'TOKEN_ID': 3375,
                'TOKEN_NAME': 'Bitcoin',
                'TOKEN_SYMBOL': 'BTC',
                'CURRENT_PRICE': 45000.00,
                'MARKET_CAP': 850000000000,
                'TOTAL_VOLUME': 25000000000,
                'CIRCULATING_SUPPLY': 19500000,
                'TOTAL_SUPPLY': 21000000,
                'MAX_SUPPLY': 21000000,
                'FULLY_DILUTED_VALUATION': 945000000000,
                'HIGH_24H': 46000.00,
                'LOW_24H': 44000.00,
                'PRICE_CHANGE_PERCENTAGE_24H_IN_CURRENCY': 2.5
            },
            {
                'TOKEN_ID': 3306,
                'TOKEN_NAME': 'Ethereum',
                'TOKEN_SYMBOL': 'ETH',
                'CURRENT_PRICE': 3200.00,
                'MARKET_CAP': 380000000000,
                'TOTAL_VOLUME': 15000000000,
                'CIRCULATING_SUPPLY': 120000000,
                'TOTAL_SUPPLY': 120000000,
                'MAX_SUPPLY': None,
                'FULLY_DILUTED_VALUATION': 384000000000,
                'HIGH_24H': 3300.00,
                'LOW_24H': 3100.00,
                'PRICE_CHANGE_PERCENTAGE_24H_IN_CURRENCY': 1.8
            },
            {
                'TOKEN_ID': 3315,
                'TOKEN_NAME': 'Cardano',
                'TOKEN_SYMBOL': 'ADA',
                'CURRENT_PRICE': 0.85,
                'MARKET_CAP': 30000000000,
                'TOTAL_VOLUME': 800000000,
                'CIRCULATING_SUPPLY': 35000000000,
                'TOTAL_SUPPLY': 45000000000,
                'MAX_SUPPLY': 45000000000,
                'FULLY_DILUTED_VALUATION': 38250000000,
                'HIGH_24H': 0.88,
                'LOW_24H': 0.82,
                'PRICE_CHANGE_PERCENTAGE_24H_IN_CURRENCY': 3.2
            }
        ]
    
    async def fetch_and_store_real_token_data(self, token_names: List[str]) -> bool:
        """Fetch real token data from API and store in Supabase"""
        try:
            print(f"🔄 Fetching real token data for: {', '.join(token_names)}")
            
            # Use the new method to fetch and store real token data
            success = await self.token_data_api.get_and_store_token_data_by_names(token_names)
            
            if success:
                print(f"✅ Successfully fetched and stored real token data for {len(token_names)} tokens")
            else:
                print(f"❌ Failed to fetch and store real token data")
            
            return success
            
        except Exception as e:
            print(f"❌ Error fetching real token data: {e}")
            return False
    
    async def get_top_4_tokens_from_embeddings(self) -> List[str]:
        """Get top 4 tokens from embeddings search using retriever logic"""
        try:
            print("🔍 Getting top 4 tokens from embeddings search...")
            
            # Use the retriever's semantic search to find top tokens
            # We'll search for multiple queries to get diverse results
            queries = [
                "most investable cryptocurrency with strong fundamentals",
                "cryptocurrency investment opportunity positive sentiment",
                "best crypto to invest in with growth potential",
                "cryptocurrency with strong community and development"
            ]
            
            all_tokens = set()
            
            for query in queries:
                print(f" Searching: '{query}'")
                results = await self.retriever.semantic_search(query, top_k=3)
                if results:
                    for result in results:
                        token_name = result.get('token_name')
                        if token_name:
                            all_tokens.add(token_name)
                    print(f"✅ Found {len(results)} results for query")
            
            # Convert to list and take top 4
            top_tokens = list(all_tokens)[:4]
            
            if not top_tokens:
                print("⚠️ No tokens found from embeddings search. Using fallback...")
                # Get tokens from posts table as fallback
                posts_response = self.supabase.table('posts').select('token_name').execute()
                if posts_response.data:
                    post_tokens = set()
                    for post in posts_response.data:
                        if post.get('token_name'):
                            post_tokens.add(post['token_name'])
                    top_tokens = list(post_tokens)[:4]
            
            print(f"✅ Top 4 tokens from embeddings: {', '.join(top_tokens)}")
            return top_tokens
            
        except Exception as e:
            print(f"❌ Error getting top 4 tokens from embeddings: {e}")
            return []
    
    async def get_comprehensive_token_data_for_today(self, token_names: List[str]) -> Dict[str, Dict]:
        """Get comprehensive token data for today from all tables"""
        try:
            print(f"📊 Getting comprehensive token data for today: {', '.join(token_names)}")
            
            comprehensive_data = {}
            
            for token_name in token_names:
                # 🆕 FIX: URL decode the token name if it's encoded
                decoded_token_name = urllib.parse.unquote(token_name)
                if decoded_token_name != token_name:
                    print(f" Decoded token name: {token_name} → {decoded_token_name}")
                    token_name = decoded_token_name
                
                print(f"\n🔄 Processing {token_name}...")
                
                # Use the retriever's method to get comprehensive data
                token_data = await self.retriever.get_comprehensive_token_data(token_name)
                if token_data:
                    # Add resistance support data to the comprehensive data
                    print(f"🔄 Adding resistance support data for {token_name}...")
                    
                    # Get token ID from the data
                    token_id = None
                    if token_data.get('ai_reports'):
                        token_id = token_data['ai_reports'][0].get('token_id')
                    elif token_data.get('fundamental_grade'):
                        token_id = token_data['fundamental_grade'][0].get('token_id')
                    
                    if token_id:
                        # ✅ FIXED: Actually fetch resistance support data
                        try:
                            resistance_support_data = await self.resistance_support_api.get_resistance_support_by_id(token_id)
                            if resistance_support_data:
                                token_data['resistance_support'] = resistance_support_data
                                print(f"✅ Added resistance support data for {token_name}")
                            else:
                                print(f"⚠️ No resistance support data found for {token_name}")
                                token_data['resistance_support'] = {}
                        except Exception as e:
                            print(f"⚠️ Error fetching resistance support data for {token_name}: {e}")
                            token_data['resistance_support'] = {}
                    else:
                        print(f"⚠️ Could not determine token ID for {token_name}")
                        token_data['resistance_support'] = {}
                    
                    comprehensive_data[token_name] = token_data
                    print(f"✅ Retrieved comprehensive data for {token_name}")
                else:
                    print(f"⚠️ No comprehensive data found for {token_name}")
            
            print(f"✅ Retrieved comprehensive data for {len(comprehensive_data)} tokens")
            return comprehensive_data
            
        except Exception as e:
            print(f"❌ Error getting comprehensive token data: {e}")
            return {}
    
    async def generate_llm_recommendations(self, comprehensive_data: Dict[str, Dict]) -> Dict:
        """Generate LLM recommendations for new positions in strict JSON format"""
        try:
            print("🤖 Generating LLM recommendations for new positions...")
            
            # Prepare data summary for LLM
            data_summary = []
            for token_name, token_data in comprehensive_data.items():
                summary = f"{token_name}: "
                
                # Add social sentiment info
                if token_data.get('social_posts'):
                    avg_sentiment = sum(post.get('post_sentiment', 0) for post in token_data['social_posts']) / len(token_data['social_posts'])
                    summary += f"Social sentiment: {avg_sentiment:.2f}/5, "
                
                # Add AI reports info
                if token_data.get('ai_reports'):
                    summary += f"AI reports: {len(token_data['ai_reports'])}, "
                
                # Add fundamental grade info
                if token_data.get('fundamental_grade'):
                    grade = token_data['fundamental_grade'][0]
                    summary += f"Fundamental grade: {grade.get('fundamental_grade', 'N/A')}, "
                
                # 🆕 ADD TOKEN METRICS DATA FROM TOKENS TABLE
                if token_data.get('token_metrics'):
                    metrics = token_data['token_metrics'][0]  # Get latest metrics
                    summary += f"Current price: ${metrics.get('current_price', 'N/A')}, "
                    summary += f"Market cap: ${metrics.get('market_cap', 'N/A'):,.0f}, "
                    summary += f"24h change: {metrics.get('price_change_percentage_24h', 'N/A')}%, "
                    summary += f"24h volume: ${metrics.get('total_volume', 'N/A'):,.0f}, "
                # Fallback to OHLCV data if no token metrics
                elif token_data.get('daily_ohlcv'):
                    latest_price = token_data['daily_ohlcv'][-1].get('close_price', 'N/A')
                    summary += f"Current price: ${latest_price}, "
                elif token_data.get('hourly_ohlcv'):
                    latest_price = token_data['hourly_ohlcv'][-1].get('close_price', 'N/A')
                    summary += f"Current price: ${latest_price}, "
                
                # Add hourly trading signals info
                if token_data.get('hourly_trading_signals'):
                    latest_signal = token_data['hourly_trading_signals'][-1]
                    summary += f"Latest signal: {latest_signal.get('signal', 'N/A')}, "
                
                data_summary.append(summary.rstrip(', '))
            
            # Create LLM prompt
            prompt = f"""
You are a cryptocurrency investment analyst. Based on the following comprehensive data for multiple tokens, generate trading recommendations for new positions in the EXACT JSON format specified below.

TOKEN DATA SUMMARY:
{chr(10).join(f"- {summary}" for summary in data_summary)}

AVAILABLE DATA FOR EACH TOKEN:
- Social sentiment analysis
- AI analysis reports
- Trading signals and hourly signals
- Fundamental grades
- Price data (daily and hourly OHLCV)
- 🆕 Token metrics (current price, market cap, volume, supply, 24h changes)

REQUIRED OUTPUT FORMAT (JSON only, no other text):
{{
  "new_positions": [
    {{
      "symbol": "[TOKEN_SYMBOL]",
      "entry": [entry_price],
      "size_usd": [position_size_in_usd],
      "stop_loss": [stop_loss_price],
      "target_1": [first_target_price],
      "target_2": [second_target_price],
      "days": [estimated_days_to_reach_target_based_on_analysis],
      "rationale": "[Detailed rationale based on the data provided, including social sentiment, AI analysis, trading signals, and token metrics. Also explain your days estimate based on market conditions, volatility, and technical analysis.]"
    }}
  ]
}}

IMPORTANT RULES:
- Use ONLY the exact JSON format above
- Do not include any explanatory text before or after the JSON
- Base your analysis on the available data for each token
- If insufficient data, use conservative estimates
- The rationale should reference specific data points from the provided information
- All prices should be realistic based on current market conditions
- Position size should be reasonable (typically 10-50 USD for testing)
- Consider hourly trading signals for short-term entry/exit timing
- Generate recommendations for the top 2-4 most promising tokens based on the data
- Focus on tokens with strong social sentiment, AI analysis, trading signals, and favorable token metrics
- Use the current price from token metrics for realistic entry/exit calculations
- The "days" field should be your AI-estimated time to reach the target price based on your expert analysis of the provided data
"""

            # Call OpenAI API using the retriever's client
            response = self.retriever.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a cryptocurrency investment analyst. You must respond with ONLY valid JSON in the exact format specified. No additional text or explanations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            # Extract and parse the response
            llm_response = response.choices[0].message.content.strip()
            
            # Try to extract JSON from the response
            import re
            
            # Look for JSON pattern in the response
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    result = json.loads(json_str)
                    print("✅ LLM recommendations generated successfully")
                    return result
                except json.JSONDecodeError as e:
                    print(f"❌ Failed to parse LLM JSON response: {e}")
                    print(f"Raw response: {llm_response}")
                    return self.generate_fallback_recommendations(list(comprehensive_data.keys()))
            else:
                print(f"❌ No JSON found in LLM response: {llm_response}")
                return self.generate_fallback_recommendations(list(comprehensive_data.keys()))
                
        except Exception as e:
            print(f"❌ Error generating LLM recommendations: {e}")
            return self.generate_fallback_recommendations(list(comprehensive_data.keys()))
    
    def generate_fallback_recommendations(self, token_names: List[str]) -> Dict:
        """Generate fallback recommendations when LLM fails"""
        fallback_positions = []
        
        for token_name in token_names:
            fallback_positions.append({
                "symbol": token_name,
                "entry": 1.00,
                "size_usd": 20,
                "stop_loss": 0.80,
                "target_1": 1.20,
                "target_2": 1.50,
                "days": 30,
                "rationale": f"Fallback recommendation for {token_name} due to insufficient data or LLM processing error. Conservative 30-day estimate for target achievement."
            })
        
        return {
            "new_positions": fallback_positions
        }
    
    def print_llm_recommendations(self, llm_result: Dict):
        """Print the LLM recommendations in a structured way"""
        print(f"\n{'='*100}")
        print(" LLM TRADING RECOMMENDATIONS")
        print("=" * 60)
        
        if llm_result and 'new_positions' in llm_result:
            for i, position in enumerate(llm_result['new_positions'], 1):
                print(f"📊 Position {i}:")
                print(f"  • Symbol: {position.get('symbol', 'N/A')}")
                print(f"  • Entry Price: ${position.get('entry', 'N/A')}")
                print(f"  • Position Size: ${position.get('size_usd', 'N/A')}")
                print(f"  • Stop Loss: ${position.get('stop_loss', 'N/A')}")
                print(f"  • Target 1: ${position.get('target_1', 'N/A')}")
                print(f"  • Target 2: ${position.get('target_2', 'N/A')}")
                print(f"  • Estimated Days: {position.get('days', 'N/A')} days")
                print(f"  • Rationale: {position.get('rationale', 'N/A')}")
                print()
        else:
            print("❌ No valid LLM recommendations")
        
        print(f"{'='*100}")
    
    async def process_resistance_support_data(self, token_ids: List[int], token_symbols: List[str]) -> bool:
        """Process resistance support data for multiple tokens using token IDs"""
        try:
            print(f"📊 Fetching resistance support data for {len(token_ids)} tokens...")
            
            # Fetch resistance support data using token IDs
            resistance_support_data = await self.resistance_support_api.get_resistance_support_multiple_by_ids(token_ids)
            
            if not resistance_support_data:
                print(f"ℹ️ No resistance support data found for tokens")
                return True
            
            # Store resistance support data
            success = True
            for i, token_id in enumerate(token_ids):
                if token_id in resistance_support_data:
                    symbol = token_symbols[i]
                    data = resistance_support_data[token_id]
                    success = self.resistance_support_api.store_resistance_support_data(symbol, data)
                    if not success:
                        print(f"❌ Failed to store resistance support data for {symbol}")
                    else:
                        print(f"✅ Successfully stored resistance support data for {symbol}")
                else:
                    print(f"⚠️ No resistance support data found for token ID {token_id}")
            
            if success:
                print(f"✅ Successfully processed resistance support data for all tokens")
                return True
            else:
                print(f"⚠️ Some resistance support data failed to store")
                return False
                
        except Exception as e:
            print(f"❌ Error processing resistance support data: {e}")
            return False
    
    async def run_data_collection_pipeline(self) -> bool:
        """Run the complete data collection pipeline"""
        try:
            print("🚀 Starting Data Collection Pipeline")
            print("Processing: Top 10 tokens from token pipeline")
            print(f"{'='*50}")
            
            # Get top 10 tokens from the token pipeline
            tokens = await self.get_top_10_tokens()
            print(f"Loaded {len(tokens)} tokens")
            
            # Extract symbols, names, and IDs from tokens
            symbols = [token.get('TOKEN_SYMBOL', '').upper() for token in tokens]
            names = [token.get('TOKEN_NAME', 'N/A') for token in tokens]
            token_ids = [token.get('TOKEN_ID') for token in tokens]
            
            print(f"Processing symbols: {', '.join(symbols)}")
            print(f"Processing names: {', '.join(names)}")
            print(f"Processing IDs: {token_ids}")
            
            # Fetch and store real token data from API
            print("\n📊 Fetching and storing real token data from API...")
            real_data_success = await self.fetch_and_store_real_token_data(names)
            
            if not real_data_success:
                print("⚠️ Failed to fetch real token data. Continuing with available data...")
            else:
                print("✅ Real token data successfully fetched and stored")
            
            # 1. Process social posts (individual calls using token names)
            print("\n📱 Processing social posts...")
            social_results = []
            for i, name in enumerate(names):
                social_success = await self.process_social_posts(name, symbols[i])
                social_results.append(social_success)
                await asyncio.sleep(1)  # Small delay between social calls
            
            # 2. Process OHLCV data (batched using token IDs)
            print("\n📈 Processing OHLCV data...")
            ohlcv_data = await self.token_api.get_ohlcv_data_multiple_by_ids(token_ids)
            
            # Store OHLCV data
            ohlcv_success = True
            for i, symbol in enumerate(symbols):
                data = ohlcv_data.get(token_ids[i], {})
                hourly_success = self.ohlcv_storage.store_hourly_ohlcv(symbol, data.get('hourly', []))
                daily_success = self.ohlcv_storage.store_daily_ohlcv(symbol, data.get('daily', []))
                if not hourly_success or not daily_success:
                    ohlcv_success = False
            
            await asyncio.sleep(2)  # Delay before next API call
            
            # 3. Process AI reports (batched using token IDs)
            print("\n🤖 Processing AI reports...")
            ai_report_success = await self.ai_report_api.get_and_store_ai_report_multiple_by_ids(token_ids)
            
            await asyncio.sleep(3)  # Delay before next API call
            
            # 4. Process fundamental grade (batched using token IDs)
            print("\n📊 Processing fundamental grade...")
            fundamental_grade_success = await self.fundamental_grade_api.fetch_and_store_fundamental_grade_multiple_by_ids(token_ids)
            
            await asyncio.sleep(2)  # Delay before next API call
            
            # 5. Process trading signals (using token IDs)
            print("\n Processing trading signals...")
            token_symbols_str = ",".join(symbols)
            trading_signals_success = await self.process_trading_signals(token_ids, token_symbols_str)
            
            await asyncio.sleep(2)  # Delay before next API call
            
            # 6. Process hourly trading signals (using token IDs)
            print("\n📊 Processing hourly trading signals...")
            hourly_trading_signals_success = await self.process_hourly_trading_signals(token_ids, token_symbols_str)
            
            await asyncio.sleep(2)  # Delay before next API call
            
            # 7. Process resistance support data (using token IDs)
            print("\n📊 Processing resistance support data...")
            resistance_support_success = await self.process_resistance_support_data(token_ids, symbols)
            
            # Calculate overall success
            social_success = all(social_results)
            overall_success = social_success and ohlcv_success and ai_report_success and fundamental_grade_success and trading_signals_success and hourly_trading_signals_success and resistance_support_success
            
            if overall_success:
                print(f"\n✅ Successfully processed all tokens: {', '.join(symbols)}")
            else:
                print(f"\n⚠️ Some components failed for tokens: {', '.join(symbols)}")
                print(f"   Social posts: {'✅' if social_success else '❌'}")
                print(f"   OHLCV data: {'✅' if ohlcv_success else '❌'}")
                print(f"   AI reports: {'✅' if ai_report_success else '❌'}")
                print(f"   Fundamental grade: {'✅' if fundamental_grade_success else '❌'}")
                print(f"   Trading signals: {'✅' if trading_signals_success else '❌'}")
                print(f"   Hourly trading signals: {'✅' if hourly_trading_signals_success else '❌'}")
                print(f"   Resistance support data: {'✅' if resistance_support_success else '❌'}")
            
            return overall_success
            
        except Exception as e:
            print(f"❌ Error in data collection pipeline: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def process_social_posts(self, token_name: str, token_symbol: str) -> bool:
        """Process social posts for a token using token name"""
        try:
            print(f"📱 Fetching social posts for {token_name} (symbol: {token_symbol})...")
            
            # Fetch social sentiment data using token name instead of symbol
            posts = await fetch_social_sentiment(token_name)
            if not posts:
                print(f"ℹ️ No social posts found for {token_name}")
                return True
            
            # Filter posts
            filtered_posts = filter_posts(posts)
            if not filtered_posts:
                print(f"ℹ️ No filtered posts for {token_name}")
                return True
            
            # Store in Supabase
            success = store_in_supabase(filtered_posts, token_symbol)
            
            if success:
                print(f"✅ Successfully processed {len(filtered_posts)} social posts for {token_name}")
            else:
                print(f"❌ Failed to store social posts for {token_name}")
            
            return success
            
        except Exception as e:
            print(f"❌ Error processing social posts for {token_name}: {e}")
            return False
    
    async def process_ohlcv_data(self, token_id: int, token_symbol: str) -> bool:
        """Process OHLCV data for a token using token ID"""
        try:
            print(f"📈 Fetching OHLCV data for {token_symbol} (ID: {token_id})...")
            
            # Fetch hourly and daily OHLCV data using token ID
            hourly_data = await self.token_api.get_hourly_ohlcv_by_id(token_id)
            daily_data = await self.token_api.get_daily_ohlcv_by_id(token_id)
            
            # Store data
            hourly_success = self.ohlcv_storage.store_hourly_ohlcv(token_symbol, hourly_data or [])
            daily_success = self.ohlcv_storage.store_daily_ohlcv(token_symbol, daily_data or [])
            
            if hourly_success and daily_success:
                print(f"✅ Successfully processed OHLCV data for {token_symbol}")
                return True
            else:
                print(f"❌ Failed to process OHLCV data for {token_symbol}")
                return False
                
        except Exception as e:
            print(f"❌ Error processing OHLCV data for {token_symbol}: {e}")
            return False
    
    async def process_ai_report(self, token_id: int, token_symbol: str) -> bool:
        """Process AI report for a token using token ID"""
        try:
            print(f" Fetching AI report for {token_symbol} (ID: {token_id})...")
            
            # Fetch and store AI report data using token ID
            success = await self.ai_report_api.get_and_store_ai_report_by_id(token_id)
            
            if success:
                print(f"✅ Successfully processed AI report for {token_symbol}")
                return True
            else:
                print(f"❌ Failed to process AI report for {token_symbol}")
                return False
                
        except Exception as e:
            print(f"❌ Error processing AI report for {token_symbol}: {e}")
            return False
    
    async def process_fundamental_grade(self, token_id: int, token_symbol: str) -> bool:
        """Process fundamental grade for a token using token ID"""
        try:
            print(f"📊 Fetching fundamental grade for {token_symbol} (ID: {token_id})...")
            
            # Fetch and store fundamental grade data using token ID
            success = await self.fundamental_grade_api.fetch_and_store_fundamental_grade_by_id(token_id)
            
            if success:
                print(f"✅ Successfully processed fundamental grade for {token_symbol}")
                return True
            else:
                print(f"❌ Failed to process fundamental grade for {token_symbol}")
                return False
                
        except Exception as e:
            print(f"❌ Error processing fundamental grade for {token_symbol}: {e}")
            return False
    
    async def process_trading_signals(self, token_ids: List[int], token_symbols: str) -> bool:
        """Process trading signals for multiple tokens using token IDs"""
        try:
            print(f"📊 Fetching trading signals for {token_symbols} (IDs: {token_ids})...")
            
            # Fetch trading signals using token IDs
            signals = await self.trading_signals_api.get_trading_signals_by_ids(token_ids)
            
            if not signals:
                print(f"ℹ️ No trading signals found for {token_symbols}")
                return True
            
            # Store trading signals
            success = self.trading_signals_storage.store_trading_signals(signals)
            
            if success:
                print(f"✅ Successfully processed trading signals for {token_symbols}")
                return True
            else:
                print(f"❌ Failed to store trading signals for {token_symbols}")
                return False
                
        except Exception as e:
            print(f"❌ Error processing trading signals for {token_symbols}: {e}")
            return False
    
    async def process_hourly_trading_signals(self, token_ids: List[int], token_symbols: str) -> bool:
        """Process hourly trading signals for multiple tokens using token IDs"""
        try:
            print(f"📊 Fetching hourly trading signals for {token_symbols} (IDs: {token_ids})...")
            
            # Fetch hourly trading signals using token IDs
            signals = await self.hourly_trading_signals_api.get_hourly_trading_signals(token_ids=token_ids)
            
            if not signals:
                print(f"ℹ️ No hourly trading signals found for {token_symbols}")
                return True
            
            # Store hourly trading signals
            success = self.hourly_trading_signals_storage.store_hourly_trading_signals(signals)
            
            if success:
                print(f"✅ Successfully processed hourly trading signals for {token_symbols}")
                return True
            else:
                print(f"❌ Failed to store hourly trading signals for {token_symbols}")
                return False
                
        except Exception as e:
            print(f"❌ Error processing hourly trading signals for {token_symbols}: {e}")
            return False
    
    async def run_embeddings_pipeline(self) -> bool:
        """Run the embeddings pipeline on collected data"""
        try:
            print(f"\n{'='*50}")
            print("🔍 Starting Embeddings Pipeline")
            print(f"{'='*50}")
            
            # Get tokens from posts table
            posts_response = self.supabase.table('posts').select('token_name').execute()
            post_tokens = set()
            if posts_response.data:
                for post in posts_response.data:
                    if post.get('token_name'):
                        # 🆕 FIX: URL decode token names from database
                        raw_token_name = post['token_name']
                        decoded_token_name = urllib.parse.unquote(raw_token_name)
                        if decoded_token_name != raw_token_name:
                            print(f"🔄 Decoded post token name: {raw_token_name} → {decoded_token_name}")
                        post_tokens.add(decoded_token_name)
            
            # Get tokens from ai_reports table
            reports_response = self.supabase.table('ai_reports').select('token_name').execute()
            report_tokens = set()
            if reports_response.data:
                for report in reports_response.data:
                    if report.get('token_name'):
                        # 🆕 FIX: URL decode token names from database
                        raw_token_name = report['token_name']
                        decoded_token_name = urllib.parse.unquote(raw_token_name)
                        if decoded_token_name != raw_token_name:
                            print(f"🔄 Decoded report token name: {raw_token_name} → {decoded_token_name}")
                        report_tokens.add(decoded_token_name)
            
            # Combine all tokens
            all_tokens = list(post_tokens.union(report_tokens))
            
            if not all_tokens:
                print("❌ No tokens found in your data!")
                print("Please run your data collection scripts first to populate posts and ai_reports tables.")
                return False
            
            print(f"✅ Found tokens: {', '.join(all_tokens)}")
            
            # Use all available tokens (now decoded)
            token_names = all_tokens
            
            print(f" Processing TODAY'S embeddings for tokens: {', '.join(token_names)}")
            
            # Run the embedding pipeline with DECODED token names
            success = await self.embedding_pipeline.run_embedding_pipeline(token_names)
            
            if success:
                print("\n✅ Embedding pipeline completed successfully!")
                print("📅 Only processed data created today.")
                print("🔍 You can now use the embeddings for semantic search.")
            else:
                print("\n⚠️ Embedding pipeline completed with some errors.")
                print("Check the logs above for details.")
            
            return success
            
        except Exception as e:
            print(f"❌ Error in embeddings pipeline: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def store_new_positions(self, llm_recommendations: Dict) -> bool:
        """
        Store new positions from LLM recommendations in Supabase
        
        Args:
            llm_recommendations (Dict): LLM recommendations with new_positions array
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not llm_recommendations or 'new_positions' not in llm_recommendations:
                print("⚠️ No new positions to store")
                return False
            
            positions = llm_recommendations['new_positions']
            if not positions:
                print("⚠️ Empty new_positions array")
                return False
            
            print(f"💾 Storing {len(positions)} new positions in Supabase...")
            
            # Prepare data for storage
            positions_to_store = []
            for position in positions:
                position_data = {
                    'symbol': position.get('symbol', '').upper(),
                    'entry_price': float(position.get('entry', 0)),
                    'size_usd': float(position.get('size_usd', 0)),
                    'stop_loss': float(position.get('stop_loss', 0)),
                    'target_1': float(position.get('target_1', 0)),
                    'target_2': float(position.get('target_2', 0)),
                    'days': int(position.get('days', 30)),
                    'rationale': position.get('rationale', ''),
                    'status': 'active'
                }
                
                # Validate required fields
                if not position_data['symbol']:
                    print(f"⚠️ Missing symbol for position: {position}")
                    continue
                
                if position_data['entry_price'] <= 0:
                    print(f"⚠️ Invalid entry price for {position_data['symbol']}: {position_data['entry_price']}")
                    continue
                
                if position_data['days'] <= 0:
                    print(f"⚠️ Invalid days estimate for {position_data['symbol']}: {position_data['days']}")
                    position_data['days'] = 30  # Set default to 30 days
                
                positions_to_store.append(position_data)
            
            if not positions_to_store:
                print("❌ No valid positions to store")
                return False
            
            # Store positions in Supabase
            success_count = 0
            for position_data in positions_to_store:
                try:
                    # Insert new position
                    response = self.supabase.table('new_positions').insert(position_data).execute()
                    
                    if response.data:
                        print(f"✅ Stored position for {position_data['symbol']}")
                        print(f"   - Entry: ${position_data['entry_price']:.8f}")
                        print(f"   - Size: ${position_data['size_usd']:.2f}")
                        print(f"   - Stop Loss: ${position_data['stop_loss']:.8f}")
                        print(f"   - Target 1: ${position_data['target_1']:.8f}")
                        print(f"   - Target 2: ${position_data['target_2']:.8f}")
                        print(f"   - Estimated Days: {position_data['days']} days")
                        success_count += 1
                    else:
                        print(f"❌ Failed to store position for {position_data['symbol']}")
                        
                except Exception as e:
                    print(f"❌ Error storing position for {position_data['symbol']}: {e}")
            
            print(f"✅ Successfully stored {success_count} out of {len(positions_to_store)} positions")
            return success_count > 0
            
        except Exception as e:
            print(f"❌ Error storing new positions: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def get_stored_positions(self, symbol: str = None, status: str = 'active') -> List[Dict]:
        """
        Retrieve stored positions from Supabase
        
        Args:
            symbol (str, optional): Filter by specific symbol
            status (str): Filter by status (active, closed, cancelled)
            
        Returns:
            List[Dict]: List of stored positions
        """
        try:
            print(f"🔍 Retrieving stored positions (status: {status})...")
            
            query = self.supabase.table('new_positions').select('*').eq('status', status)
            
            if symbol:
                query = query.eq('symbol', symbol.upper())
                print(f"   Filtering by symbol: {symbol}")
            
            response = query.order('created_at', desc=True).execute()
            
            if response.data:
                positions = response.data
                print(f"✅ Found {len(positions)} stored positions")
                
                for position in positions:
                    print(f"   - {position['symbol']}: Entry ${position['entry_price']:.8f}, Size ${position['size_usd']:.2f}")
                
                return positions
            else:
                print(f"ℹ️ No stored positions found with status: {status}")
                return []
                
        except Exception as e:
            print(f"❌ Error retrieving stored positions: {e}")
            return []
    
    def update_position_status(self, position_id: int, new_status: str) -> bool:
        """
        Update the status of a stored position
        
        Args:
            position_id (int): ID of the position to update
            new_status (str): New status (active, closed, cancelled)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if new_status not in ['active', 'closed', 'cancelled']:
                print(f"❌ Invalid status: {new_status}. Must be one of: active, closed, cancelled")
                return False
            
            print(f"🔄 Updating position {position_id} status to: {new_status}")
            
            response = self.supabase.table('new_positions').update({
                'status': new_status
            }).eq('id', position_id).execute()
            
            if response.data:
                print(f"✅ Successfully updated position {position_id} status to {new_status}")
                return True
            else:
                print(f"❌ Failed to update position {position_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating position status: {e}")
            return False
    
    async def run_retriever_analysis(self) -> bool:
        """Run the retriever analysis to get top 4 tokens and LLM recommendations"""
        try:
            print(f"\n{'='*50}")
            print(" Starting Retriever Analysis")
            print(f"{'='*50}")
            
            # Step 1: Get top 4 tokens from embeddings search
            print("\n🔄 Step 1: Getting top 4 tokens from embeddings search...")
            top_4_tokens = await self.get_top_4_tokens_from_embeddings()
            
            if not top_4_tokens:
                print("❌ No tokens found from embeddings search")
                return False
            
            # Step 2: Get comprehensive token data for today
            print("\n🔄 Step 2: Getting comprehensive token data for today...")
            comprehensive_data = await self.get_comprehensive_token_data_for_today(top_4_tokens)
            
            if not comprehensive_data:
                print("❌ No comprehensive data found for tokens")
                return False
            
            # Step 3: Generate LLM recommendations
            print("\n Step 3: Generating LLM recommendations...")
            llm_recommendations = await self.generate_llm_recommendations(comprehensive_data)
            
            # Step 4: Store new positions in Supabase
            print("\n💾 Step 4: Storing new positions in Supabase...")
            storage_success = self.store_new_positions(llm_recommendations)
            
            if storage_success:
                print("✅ New positions stored successfully")
            else:
                print("⚠️ Some positions failed to store")
            
            # Step 5: Print LLM recommendations
            print("\n Step 5: Displaying LLM recommendations...")
            self.print_llm_recommendations(llm_recommendations)
            
            # Step 6: Print the raw JSON for easy copying
            print(f"\n📋 RAW JSON OUTPUT:")
            print("=" * 60)
            print(json.dumps(llm_recommendations, indent=2))
            print("=" * 60)
            
            # Step 7: Show stored positions
            print(f"\n💾 STORED POSITIONS IN SUPABASE:")
            print("=" * 60)
            stored_positions = await self.get_stored_positions()
            if stored_positions:
                print(f"✅ Found {len(stored_positions)} active positions")
            else:
                print("ℹ️ No active positions found")
            
            print(f"\n✅ Retriever analysis completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error in retriever analysis: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_complete_workflow(self):
        """Run the complete workflow: data collection + embeddings + retriever analysis"""
        try:
            print("🎯 COMPLETE CRYPTO DATA WORKFLOW")
            print("=" * 60)
            print("This workflow will:")
            print("1. 📊 Get top 10 tokens from token pipeline")
            print("2. 📊 Collect social posts, token metrics, AI reports, and trading signals")
            print("3. 🔍 Create embeddings for semantic search")
            print("4. 🔍 Use retriever logic to find top 4 tokens from embeddings")
            print("5. 📊 Get comprehensive token info for today from all tables")
            print("6. 🤖 Pass all info to LLM for new position recommendations in strict JSON format")
            print("7. 💾 Store everything in Supabase")
            print("=" * 60)
            
            # Step 1: Data Collection Pipeline
            print("\n🔄 STEP 1: Data Collection Pipeline")
            print("-" * 40)
            data_collection_success = await self.run_data_collection_pipeline()
            
            if not data_collection_success:
                print("❌ Data collection pipeline failed. Stopping workflow.")
                return False
            
            # Step 2: Embeddings Pipeline
            print("\n STEP 2: Embeddings Pipeline")
            print("-" * 40)
            embeddings_success = await self.run_embeddings_pipeline()
            
            if not embeddings_success:
                print("⚠️ Embeddings pipeline failed. Continuing with retriever analysis...")
            
            # Step 3: Retriever Analysis
            print("\n🔍 STEP 3: Retriever Analysis")
            print("-" * 40)
            retriever_success = await self.run_retriever_analysis()
            
            # Final Summary
            print(f"\n{'='*60}")
            print(" WORKFLOW COMPLETED")
            print(f"{'='*60}")
            
            if data_collection_success and embeddings_success and retriever_success:
                print("🎉 Complete workflow executed successfully!")
                print("✅ Data collection: Completed")
                print("✅ Embeddings: Completed")
                print("✅ Retriever analysis: Completed")
                print("🤖 LLM recommendations generated in strict JSON format!")
                print("🔍 Your crypto data is now ready for semantic search and trading decisions!")
            else:
                print("⚠️ Workflow completed with some issues:")
                print(f"   Data collection: {'✅' if data_collection_success else '❌'}")
                print(f"   Embeddings: {'✅' if embeddings_success else '❌'}")
                print(f"   Retriever analysis: {'✅' if retriever_success else '❌'}")
            
            return data_collection_success and embeddings_success and retriever_success
            
        except Exception as e:
            print(f"❌ Workflow failed: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Main function"""
    try:
        workflow = CompleteCryptoWorkflow()
        await workflow.run_complete_workflow()
    except Exception as e:
        print(f"❌ Failed to start workflow: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
