#!/usr/bin/env python3
"""
Simplified Crypto Data Pipeline
This script processes 3 dummy tokens (BTC, ETH, ADA):
1. Stores token metadata in Supabase
2. Fetches social posts using LunarCrush API (using token name)
3. Fetches hourly and daily OHLCV data in parallel (using token ID)
4. Fetches trading signals data (using token ID)
5. Fetches AI reports data (using token ID)
6. Fetches fundamental grade data (using token ID)
7. Stores all data in Supabase
"""

import asyncio
import os
from typing import List, Dict
from dotenv import load_dotenv

# Import our modules
from apis.token_metrics import TokenMetricsAPI
from apis.social_sentiment import fetch_social_sentiment, filter_posts, store_in_supabase
from apis.ohlcv_storage import OHLCVStorage
from apis.trading_signals import TradingSignalsAPI
from apis.trading_signals_storage import TradingSignalsStorage
from apis.ai_report import AIReportAPI
from apis.fundamental_grade import FundamentalGradeAPI
from apis.hourly_trading_signals import HourlyTradingSignalsAPI
from apis.hourly_trading_signals_storage import HourlyTradingSignalsStorage

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

class CryptoPipeline:
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
    
    def get_dummy_tokens(self) -> List[Dict]:
        """Get dummy data for BTC, ETH, ADA"""
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
    
    def store_token_data(self, token: Dict) -> bool:
        """Store token metadata in Supabase"""
        try:
            # For now, just print the token data
            print(f"📊 Token: {token.get('TOKEN_SYMBOL')} - {token.get('TOKEN_NAME')}")
            print(f"   Price: ${token.get('CURRENT_PRICE'):,.2f}")
            print(f"   Market Cap: ${token.get('MARKET_CAP'):,.0f}")
            print(f"   24h Change: {token.get('PRICE_CHANGE_PERCENTAGE_24H_IN_CURRENCY')}%")
            return True
        except Exception as e:
            print(f"❌ Error storing token data: {e}")
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
            
            # Store data - FIXED: Added token_symbol parameter
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
            print(f"📊 Fetching AI report for {token_symbol} (ID: {token_id})...")
            
            # Fetch and store AI report data using token ID
            success = await self.ai_report_api.get_and_store_ai_report_by_id(token_id)
            
            if success:
                print(f"✅ Successfully processed AI report for {token_symbol}")
                return True
            else:
                print(f"❌ Failed to process AI report for {token_symbol}")
                print(f"   This could be due to:")
                print(f"   - API authentication issues")
                print(f"   - Network connectivity problems")
                print(f"   - API rate limiting")
                print(f"   - Invalid token ID")
                print(f"   - Missing environment variables")
                return False
                
        except Exception as e:
            print(f"❌ Error processing AI report for {token_symbol}: {e}")
            import traceback
            print("Full error details:")
            traceback.print_exc()
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
                print(f"   This could be due to:")
                print(f"   - API authentication issues")
                print(f"   - Network connectivity problems")
                print(f"   - API rate limiting")
                print(f"   - Invalid token ID")
                print(f"   - Missing environment variables")
                return False
                
        except Exception as e:
            print(f"❌ Error processing fundamental grade for {token_symbol}: {e}")
            import traceback
            print("Full error details:")
            traceback.print_exc()
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
    
    async def process_token(self, token: Dict) -> bool:
        """Process a single token with delays between API calls"""
        symbol = token.get('TOKEN_SYMBOL', '').upper()
        name = token.get('TOKEN_NAME', 'N/A')
        token_id = token.get('TOKEN_ID')
        
        print(f"\n{'='*50}")
        print(f"Processing: {symbol} ({name}) - ID: {token_id}")
        print(f"{'='*50}")
        
        # Store token metadata
        token_success = self.store_token_data(token)
        if not token_success:
            print(f"❌ Failed to store token data for {symbol}")
            return False
        
        # Process APIs sequentially with delays instead of in parallel
        print(f" Processing {symbol} APIs sequentially to avoid rate limits...")
        
        # Social posts (using token name)
        social_success = await self.process_social_posts(name, symbol)
        await asyncio.sleep(2)  # 2 second delay
        
        # OHLCV data (using token ID)
        ohlcv_success = await self.process_ohlcv_data(token_id, symbol)
        await asyncio.sleep(2)  # 2 second delay
        
        # AI report (paid API) (using token ID)
        ai_report_success = await self.process_ai_report(token_id, symbol)
        await asyncio.sleep(3)  # 3 second delay for paid APIs
        
        # Fundamental grade (paid API) (using token ID)
        fundamental_grade_success = await self.process_fundamental_grade(token_id, symbol)
        await asyncio.sleep(3)  # 3 second delay for paid APIs
        
        overall_success = social_success and ohlcv_success and ai_report_success and fundamental_grade_success
        
        if overall_success:
            print(f"✅ Successfully processed {symbol}")
        else:
            print(f"❌ Failed to process {symbol}")
        
        return overall_success
    
    async def process_all_tokens_batched(self, tokens: List[Dict]) -> bool:
        """Process all tokens using batched API calls"""
        try:
            print(f"\n{'='*50}")
            print("Processing all tokens with batched API calls")
            print(f"{'='*50}")
            
            # Extract symbols, names, and IDs from tokens
            symbols = [token.get('TOKEN_SYMBOL', '').upper() for token in tokens]
            names = [token.get('TOKEN_NAME', 'N/A') for token in tokens]
            token_ids = [token.get('TOKEN_ID') for token in tokens]
            
            print(f"Processing symbols: {', '.join(symbols)}")
            print(f"Processing names: {', '.join(names)}")
            print(f"Processing IDs: {token_ids}")
            
            # Store token metadata for all tokens
            print("\n📊 Storing token metadata...")
            for token in tokens:
                self.store_token_data(token)
            
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
            
            # Calculate overall success
            social_success = all(social_results)
            overall_success = social_success and ohlcv_success and ai_report_success and fundamental_grade_success and trading_signals_success and hourly_trading_signals_success
            
            if overall_success:
                print(f"\n✅ Successfully processed all tokens: {', '.join(symbols)}")
            else:
                print(f"\n❌ Some components failed for tokens: {', '.join(symbols)}")
                print(f"   Social posts: {'✅' if social_success else '❌'}")
                print(f"   OHLCV data: {'✅' if ohlcv_success else '❌'}")
                print(f"   AI reports: {'✅' if ai_report_success else '❌'}")
                print(f"   Fundamental grade: {'✅' if fundamental_grade_success else '❌'}")
                print(f"   Trading signals: {'✅' if trading_signals_success else '❌'}")
                print(f"   Hourly trading signals: {'✅' if hourly_trading_signals_success else '❌'}")
            
            return overall_success
            
        except Exception as e:
            print(f"❌ Error in batch processing: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def run_pipeline(self):
        """Run the complete pipeline with batched API calls"""
        try:
            print("🚀 Starting Crypto Data Pipeline")
            print("Processing: BTC, ETH, ADA")
            print(f"{'='*50}")
            
            # Get dummy tokens
            tokens = self.get_dummy_tokens()
            print(f"Loaded {len(tokens)} tokens")
            
            # Process all tokens with batched API calls
            success = await self.process_all_tokens_batched(tokens)
            
            # Summary
            print(f"\n{'='*50}")
            print("PIPELINE COMPLETED")
            print(f"{'='*50}")
            
            if success:
                print("🎉 All tokens processed successfully with batched API calls!")
            else:
                print("⚠️ Some components failed during batch processing")
            
        except Exception as e:
            print(f"❌ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()

async def main():
    """Main function"""
    try:
        pipeline = CryptoPipeline()
        await pipeline.run_pipeline()
    except Exception as e:
        print(f"❌ Failed to start pipeline: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())