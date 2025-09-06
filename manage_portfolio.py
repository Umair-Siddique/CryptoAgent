#!/usr/bin/env python3
"""
Portfolio Manager
Fetches active positions from new_positions table and gets current token data
"""

import asyncio
import os
import sys
import json
import urllib.parse
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Add the current directory to Python path to import our modules
sys.path.append(os.path.dirname(__file__))

# Import our API modules
from apis.token_data import TokenDataAPI
from config import Config

# Supabase client
try:
    from supabase import create_client, Client
except ImportError:
    print("Supabase client not found. Please install it with: pip install supabase")
    sys.exit(1)

# OpenAI client
try:
    import openai
except ImportError:
    print("OpenAI client not found. Please install it with: pip install openai")
    sys.exit(1)

# Load environment variables
load_dotenv()

class PortfolioManager:
    def __init__(self, total_budget: float = 100.0):
        """Initialize the portfolio manager with database and API connections"""
        try:
            # Validate configuration
            Config.validate()
            
            # Initialize Supabase client
            self.supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
            
            # Initialize Token Metrics API
            self.token_api = TokenDataAPI()
            
            # Initialize OpenAI client for newer version
            self.openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
            
            # API key for direct requests (you'll need to add this to your .env file)
            self.api_key = Config.TOKEN_METRICS_API_KEY
            
            # Cookie from your curl example
            self.cookie = '__cf_bm=HzOq0GLthadKg4RWGWYFPsAEaF5YE3BbIwtYXA.2qsc-1757117314-1.0.1.1-F1Ecz.yWE30oXRiE8KUYaKzGJYEvzJledZMIXb7He9NyuuYO8JuomdS2KZkU8AmXzrU3HgL3z3QWh8q6LDJOj5eIXcMWKFx0FbVtolFQ7T8'
            
            # Portfolio settings
            self.total_budget = total_budget
            
            print("✅ Portfolio Manager initialized successfully")
            
        except Exception as e:
            print(f"❌ Error initializing Portfolio Manager: {e}")
            sys.exit(1)
    
    def get_active_positions(self) -> List[Dict[str, Any]]:
        """Fetch all active positions from the new_positions table"""
        try:
            print("🔍 Fetching active positions from new_positions table...")
            
            # Query for active positions (assuming status = 'active' or similar)
            # You may need to adjust the status filter based on your data
            response = self.supabase.table('new_positions').select('*').eq('status', 'active').execute()
            
            if response.data:
                print(f"✅ Found {len(response.data)} active positions")
                return response.data
            else:
                print("ℹ️ No active positions found")
                return []
                
        except Exception as e:
            print(f"❌ Error fetching positions: {e}")
            return []
    
    def extract_token_names(self, positions: List[Dict[str, Any]]) -> List[str]:
        """Extract unique token names from positions"""
        token_names = set()
        
        for position in positions:
            # Assuming the symbol field contains the token name
            # You may need to adjust this based on your actual data structure
            symbol = position.get('symbol', '').strip()
            if symbol:
                # Convert symbol to token name (you may need to adjust this mapping)
                # For now, assuming symbol is already the token name
                token_names.add(symbol)
        
        unique_token_names = list(token_names)
        print(f"📋 Extracted {len(unique_token_names)} unique token names: {unique_token_names}")
        return unique_token_names
    
    async def get_token_data_direct(self, token_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get current token data using direct API calls with API key and Cookie"""
        if not token_names:
            print("ℹ️ No token names to fetch data for")
            return {}
        
        print(f"🔄 Fetching current data for {len(token_names)} tokens using direct API calls...")
        
        token_data_dict = {}
        
        # Create a persistent session to maintain cookies
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        ) as client:
            for token_name in token_names:
                try:
                    # Don't URL encode the token name - use it directly like in your curl
                    url = f"https://api.tokenmetrics.com/v2/tokens?token_name={token_name}"
                    
                    print(f" Fetching data for: {token_name}")
                    print(f"📡 URL: {url}")
                    
                    headers = {
                        'accept': 'application/json',
                        'x-api-key': 'tm-2633e0ff-1d54-4d9c-89ce-6874ca0a72a6',
                        'Cookie': '__cf_bm=HzOq0GLthadKg4RWGWYFPsAEaF5YE3BbIwtYXA.2qsc-1757117314-1.0.1.1-F1Ecz.yWE30oXRiE8KUYaKzGJYEvzJledZMIXb7He9NyuuYO8JuomdS2KZkU8AmXzrU3HgL3z3QWh8q6LDJOj5eIXcMWKFx0FbVtolFQ7T8'
                    }
                    
                    response = await client.get(url, headers=headers)
                    
                    print(f" Response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            print(f"📋 Response data: {json.dumps(data, indent=2)[:300]}...")
                            
                            if data.get('success') and 'data' in data and data['data']:
                                token_info = data['data'][0]  # Take the first result
                                
                                # Extract the fields we need
                                token_data_dict[token_name] = {
                                    'price': token_info.get('CURRENT_PRICE'),
                                    'volume': token_info.get('TOTAL_VOLUME'),
                                    'market_cap': token_info.get('MARKET_CAP'),
                                    'symbol': token_info.get('TOKEN_SYMBOL', ''),
                                    'price_change_24h': token_info.get('PRICE_CHANGE_PERCENTAGE_24H_IN_CURRENCY')
                                }
                                
                                print(f"✅ Successfully fetched data for {token_name}")
                                print(f"   Price: ${token_info.get('CURRENT_PRICE', 'N/A')}")
                                print(f"   Volume: ${token_info.get('TOTAL_VOLUME', 'N/A')}")
                                print(f"   Market Cap: ${token_info.get('MARKET_CAP', 'N/A')}")
                            else:
                                print(f"❌ No data found for {token_name}. Response: {data}")
                                
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON decode error for {token_name}: {e}")
                            print(f"Raw response: {response.text[:200]}...")
                    else:
                        print(f"❌ HTTP error {response.status_code} for {token_name}")
                        print(f"Response: {response.text[:200]}...")
                    
                    # Add delay between requests to avoid rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"❌ Error fetching data for {token_name}: {e}")
                    continue
        
        print(f"✅ Successfully fetched data for {len(token_data_dict)} out of {len(token_names)} tokens")
        return token_data_dict
    
    async def get_token_data_batch(self, token_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get current token data using batch API call with comma-separated token names"""
        if not token_names:
            print("ℹ️ No token names to fetch data for")
            return {}
        
        print(f"🔄 Fetching current data for {len(token_names)} tokens in batch...")
        
        try:
            # Create comma-separated token names for the API call
            token_names_str = ",".join(token_names)
            
            # Use the endpoint format you suggested: /v2/tokens?limit=50&page=1&token_name=...
            endpoint = f"/v2/tokens?limit=50&page=1&token_name={urllib.parse.quote(token_names_str)}"
            print(f" API Endpoint: {endpoint}")
            
            # Make the API call using the existing _make_paid_request method
            result = await self.token_api._make_paid_request(endpoint)
            
            if not result:
                print("❌ No response received from API")
                return {}
            
            print(f"📊 API Response: {json.dumps(result, indent=2)[:500]}...")  # Show first 500 chars
            
            if result.get('success') and 'data' in result and result['data']:
                print(f"✅ Successfully fetched token data for {len(result['data'])} tokens")
                
                # Convert to dictionary for easy lookup
                token_data_dict = {}
                for token_info in result['data']:
                    token_name = token_info.get('TOKEN_NAME', '')
                    if token_name:
                        # Extract only the fields we need: price, volume, market cap
                        token_data_dict[token_name] = {
                            'price': token_info.get('CURRENT_PRICE'),
                            'volume': token_info.get('TOTAL_VOLUME'),
                            'market_cap': token_info.get('MARKET_CAP'),
                            'symbol': token_info.get('TOKEN_SYMBOL', ''),
                            'price_change_24h': token_info.get('PRICE_CHANGE_PERCENTAGE_24H_IN_CURRENCY')
                        }
                
                print(f"✅ Successfully processed data for {len(token_data_dict)} tokens")
                return token_data_dict
            else:
                print(f"❌ API call failed or returned no data. Response: {result}")
                return {}
                
        except Exception as e:
            print(f"❌ Error fetching token data: {e}")
            return {}
    
    async def get_token_data_individual(self, token_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fallback method: Get token data one by one if batch fails"""
        if not token_names:
            print("ℹ️ No token names to fetch data for")
            return {}
        
        print(f"🔄 Fetching current data for {len(token_names)} tokens individually...")
        
        try:
            # Use the existing API method to get token data
            token_data_list = await self.token_api.get_token_data_by_names(token_names)
            
            if not token_data_list:
                print("❌ No token data received from API")
                return {}
            
            # Convert to dictionary for easy lookup
            token_data_dict = {}
            for token_info in token_data_list:
                token_name = token_info.get('TOKEN_NAME', '')
                if token_name:
                    # Extract only the fields we need: price, volume, market cap
                    token_data_dict[token_name] = {
                        'price': token_info.get('CURRENT_PRICE'),
                        'volume': token_info.get('TOTAL_VOLUME'),
                        'market_cap': token_info.get('MARKET_CAP'),
                        'symbol': token_info.get('TOKEN_SYMBOL', ''),
                        'price_change_24h': token_info.get('PRICE_CHANGE_PERCENTAGE_24H_IN_CURRENCY')
                    }
            
            print(f"✅ Successfully fetched data for {len(token_data_dict)} tokens")
            return token_data_dict
            
        except Exception as e:
            print(f"❌ Error fetching token data: {e}")
            return {}
    
    async def get_token_data(self, token_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get current token data (price, volume, market cap) from API with multiple fallback methods"""
        if not token_names:
            print("ℹ️ No token names to fetch data for")
            return {}
        
        # Try direct API calls first (most reliable)
        print("🔄 Attempting direct API calls with API key...")
        token_data = await self.get_token_data_direct(token_names)
        
        # If direct calls fail, try batch API call
        if not token_data:
            print("⚠️ Direct API calls failed, trying batch API call...")
            token_data = await self.get_token_data_batch(token_names)
        
        # If batch fails, try individual calls with x402
        if not token_data:
            print("⚠️ Batch API call failed, trying individual x402 calls...")
            token_data = await self.get_token_data_individual(token_names)
        
        return token_data
    
    def calculate_position_performance(self, position: Dict[str, Any], current_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance metrics for a position"""
        entry_price = position.get('entry_price', 0)
        current_price = current_data.get('price', 0)
        size_usd = position.get('size_usd', 0)
        created_at = position.get('created_at', '')
        
        # Calculate P&L
        pnl_percent = 0
        pnl_usd = 0
        if entry_price and current_price:
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            pnl_usd = (current_price - entry_price) * (size_usd / entry_price)
        
        # Calculate days held
        days_held = 0
        if created_at:
            try:
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                days_held = (datetime.now() - created_date.replace(tzinfo=None)).days
            except:
                days_held = 0
        
        # Calculate performance score (0-100)
        performance_score = 50  # Base score
        
        # Adjust based on P&L
        if pnl_percent > 20:
            performance_score += 30
        elif pnl_percent > 10:
            performance_score += 20
        elif pnl_percent > 0:
            performance_score += 10
        elif pnl_percent < -20:
            performance_score -= 30
        elif pnl_percent < -10:
            performance_score -= 20
        elif pnl_percent < 0:
            performance_score -= 10
        
        # Adjust based on time held (longer held positions with poor performance get lower scores)
        if days_held > 30 and pnl_percent < -10:
            performance_score -= 20
        elif days_held > 60 and pnl_percent < -5:
            performance_score -= 15
        
        # Adjust based on 24h change
        price_change_24h = current_data.get('price_change_24h', 0)
        if price_change_24h > 5:
            performance_score += 10
        elif price_change_24h < -5:
            performance_score -= 10
        
        performance_score = max(0, min(100, performance_score))
        
        return {
            'pnl_percent': pnl_percent,
            'pnl_usd': pnl_usd,
            'days_held': days_held,
            'performance_score': performance_score,
            'price_change_24h': price_change_24h
        }
    
    async def analyze_portfolio_with_ai(self, positions: List[Dict[str, Any]], token_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Use OpenAI to analyze portfolio and make allocation decisions"""
        print("🤖 Analyzing portfolio with AI...")
        
        # Prepare data for AI analysis
        portfolio_data = []
        total_current_value = 0
        
        for position in positions:
            symbol = position.get('symbol', '')
            current_data = token_data.get(symbol, {})
            
            if current_data:
                performance = self.calculate_position_performance(position, current_data)
                
                position_info = {
                    'symbol': symbol,
                    'entry_price': position.get('entry_price', 0),
                    'current_price': current_data.get('price', 0),
                    'position_size_usd': position.get('size_usd', 0),
                    'target_1': position.get('target_1', 0),
                    'target_2': position.get('target_2', 0),
                    'stop_loss': position.get('stop_loss', 0),
                    'rationale': position.get('rationale', ''),
                    'days_held': performance['days_held'],
                    'days_field': position.get('days', 0),  # The days field from database
                    'created_at': position.get('created_at', ''),
                    'pnl_percent': performance['pnl_percent'],
                    'pnl_usd': performance['pnl_usd'],
                    'performance_score': performance['performance_score'],
                    'price_change_24h': performance['price_change_24h'],
                    'market_cap': current_data.get('market_cap', 0),
                    'volume_24h': current_data.get('volume', 0)
                }
                
                portfolio_data.append(position_info)
                total_current_value += position.get('size_usd', 0)
        
        # Create AI prompt
        prompt = f"""
You are an expert cryptocurrency portfolio manager with a total budget of ${self.total_budget}. 

Current Portfolio Analysis:
- Total current value: ${total_current_value:.2f}
- Available budget: ${self.total_budget:.2f}
- Number of positions: {len(portfolio_data)}

Current Positions:
{json.dumps(portfolio_data, indent=2)}

Your task is to analyze each existing position and decide:

1. **SELL Decision**: Only sell a token if:
   - It has been held for a long time (check days_held vs days_field)
   - Current price is significantly below entry price (poor performance)
   - The token is not showing signs of reaching its targets
   - Performance score is very low (< 30)

2. **KEEP Decision**: Keep the token if:
   - It's performing well or showing potential
   - It hasn't been held too long compared to expected days
   - Current price is close to or above entry price
   - Performance score is reasonable (> 30)

3. **Budget Allocation**: 
   - If you decide to KEEP tokens, redistribute the ${self.total_budget} budget among them
   - Give more allocation to better performing tokens
   - Give less allocation to underperforming but still viable tokens
   - If you SELL any tokens, redistribute their budget to the remaining tokens

Focus on:
- Entry price vs current price performance
- Days held vs expected days (days_field)
- Whether the token is on track to reach targets
- Overall performance metrics

Provide your analysis in this JSON format:
{{
    "analysis": "Brief analysis focusing on entry points, days performance, and whether tokens should be sold or kept",
    "recommendations": [
        {{
            "symbol": "TOKEN_SYMBOL",
            "action": "KEEP|SELL",
            "new_allocation_usd": 0,
            "reason": "Detailed reason focusing on entry price performance, days analysis, and target achievement potential"
        }}
    ],
    "total_allocated": 0,
    "remaining_budget": 0,
    "expected_portfolio_value": 0
}}

Rules:
- Only analyze the existing tokens shown above
- DO NOT add new tokens
- For KEEP: set new_allocation_usd to the amount you want to allocate (0-{self.total_budget})
- For SELL: set new_allocation_usd to 0
- Make sure total_allocated does not exceed ${self.total_budget}
- Focus on entry price performance and days analysis
- Only sell if token is clearly underperforming and unlikely to reach targets
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert cryptocurrency portfolio manager. Focus on entry price performance and days analysis. Only sell tokens that are clearly underperforming. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            ai_response = response.choices[0].message.content
            print(f"🤖 AI Response: {ai_response}")
            
            # Parse AI response
            try:
                ai_analysis = json.loads(ai_response)
                return ai_analysis
            except json.JSONDecodeError as e:
                print(f"❌ Error parsing AI response: {e}")
                return {"error": "Failed to parse AI response"}
                
        except Exception as e:
            print(f"❌ Error calling OpenAI: {e}")
            return {"error": f"OpenAI API error: {e}"}
    
    async def update_positions_in_database(self, ai_analysis: Dict[str, Any]) -> bool:
        """Update the new_positions table in Supabase with AI recommendations"""
        print(" Updating positions in database...")
        
        if "error" in ai_analysis:
            print(f"❌ Cannot update database due to AI error: {ai_analysis['error']}")
            return False
        
        try:
            # Get current active positions to update
            current_positions = self.get_active_positions()
            if not current_positions:
                print("⚠️ No active positions to update")
                return True
            
            # Create a mapping of symbol to new allocation and reason from AI analysis
            recommendations = ai_analysis.get('recommendations', [])
            allocation_map = {}
            reason_map = {}
            
            for rec in recommendations:
                symbol = rec.get('symbol', '')
                action = rec.get('action', '')
                new_allocation = rec.get('new_allocation_usd', 0)
                reason = rec.get('reason', '')
                
                if symbol and action == 'KEEP' and new_allocation > 0:
                    allocation_map[symbol] = new_allocation
                    reason_map[symbol] = reason
                elif symbol and action == 'SELL':
                    allocation_map[symbol] = 0
                    reason_map[symbol] = f"SOLD: {reason}"
            
            print(f"📝 Updating {len(current_positions)} existing positions...")
            
            updated_count = 0
            for position in current_positions:
                symbol = position.get('symbol', '')
                position_id = position.get('id')
                
                if not position_id:
                    print(f"⚠️ No ID found for position {symbol}, skipping")
                    continue
                
                # Check if this symbol should be kept or sold
                if symbol in allocation_map:
                    new_size_usd = allocation_map[symbol]
                    new_reason = reason_map.get(symbol, '')
                    
                    if new_size_usd > 0:
                        # Keep position active with new allocation
                        new_status = 'active'
                        print(f"✅ Keeping {symbol} active with ${new_size_usd:.2f} allocation")
                        print(f"   Reason: {new_reason}")
                    else:
                        # Sell position - try different status values
                        new_status = 'closed'  # Try 'closed' instead
                        print(f"❌ Selling {symbol} (marking as closed)")
                        print(f"   Reason: {new_reason}")
                else:
                    # Not in recommendations, keep as is
                    print(f"⚠️ No recommendation for {symbol}, keeping unchanged")
                    continue
                
                # Update size_usd, status, and reason fields
                try:
                    update_result = self.supabase.table('new_positions').update({
                        'size_usd': new_size_usd,
                        'status': new_status,
                        'reason': new_reason,
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', position_id).execute()
                    
                    if update_result.data:
                        updated_count += 1
                        print(f"✅ Updated {symbol}: ${new_size_usd:.2f}, status: {new_status}")
                    else:
                        print(f"❌ Failed to update {symbol}")
                        
                except Exception as e:
                    print(f"❌ Error updating {symbol}: {e}")
                    # Try with 'completed' status if 'closed' fails
                    if new_status == 'closed':
                        try:
                            update_result = self.supabase.table('new_positions').update({
                                'size_usd': new_size_usd,
                                'status': 'completed',
                                'reason': new_reason,
                                'updated_at': datetime.now().isoformat()
                            }).eq('id', position_id).execute()
                            
                            if update_result.data:
                                updated_count += 1
                                print(f"✅ Updated {symbol}: ${new_size_usd:.2f}, status: completed")
                        except Exception as e2:
                            print(f"❌ Error updating {symbol} with completed status: {e2}")
                            # Try with 'finished' status
                            try:
                                update_result = self.supabase.table('new_positions').update({
                                    'size_usd': new_size_usd,
                                    'status': 'finished',
                                    'reason': new_reason,
                                    'updated_at': datetime.now().isoformat()
                                }).eq('id', position_id).execute()
                                
                                if update_result.data:
                                    updated_count += 1
                                    print(f"✅ Updated {symbol}: ${new_size_usd:.2f}, status: finished")
                            except Exception as e3:
                                print(f"❌ Error updating {symbol} with finished status: {e3}")
            
            print(f"✅ Successfully updated {updated_count} out of {len(current_positions)} positions")
            return updated_count > 0
                
        except Exception as e:
            print(f"❌ Error updating database: {e}")
            return False
    
    def display_ai_analysis(self, ai_analysis: Dict[str, Any]):
        """Display the AI analysis results"""
        print("\n" + "="*80)
        print("🤖 AI PORTFOLIO ANALYSIS")
        print("="*80)
        
        if "error" in ai_analysis:
            print(f"❌ Error: {ai_analysis['error']}")
            return
        
        print(f"📊 Analysis: {ai_analysis.get('analysis', 'No analysis provided')}")
        print(f"💰 Total Allocated: ${ai_analysis.get('total_allocated', 0):.2f}")
        print(f"💵 Remaining Budget: ${ai_analysis.get('remaining_budget', 0):.2f}")
        print(f" Expected Portfolio Value: ${ai_analysis.get('expected_portfolio_value', 0):.2f}")
        
        # Display recommendations
        recommendations = ai_analysis.get('recommendations', [])
        if recommendations:
            print(f"\n📋 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                action = rec.get('action', 'UNKNOWN')
                symbol = rec.get('symbol', 'UNKNOWN')
                new_allocation = rec.get('new_allocation_usd', 0)
                reason = rec.get('reason', 'No reason provided')
                
                action_emoji = {
                    'KEEP': '✅',
                    'SELL': '❌'
                }.get(action, '❓')
                
                print(f"{i}. {action_emoji} {symbol} - {action}")
                if action == 'KEEP':
                    print(f"   New Allocation: ${new_allocation:.2f}")
                print(f"   Reason: {reason}")
        
        print("="*80)
    
    def display_portfolio_summary(self, positions: List[Dict[str, Any]], token_data: Dict[str, Dict[str, Any]]):
        """Display a summary of the portfolio with current token data"""
        if not positions:
            print("📊 No active positions to display")
            return
        
        print("\n" + "="*80)
        print("📊 PORTFOLIO SUMMARY")
        print("="*80)
        
        total_positions = len(positions)
        total_value = 0
        
        for i, position in enumerate(positions, 1):
            symbol = position.get('symbol', 'N/A')
            entry_price = position.get('entry_price', 0)
            size_usd = position.get('size_usd', 0)
            target_1 = position.get('target_1', 0)
            target_2 = position.get('target_2', 0)
            stop_loss = position.get('stop_loss', 0)
            rationale = position.get('rationale', 'No rationale provided')
            
            print(f"\n📍 Position #{i}: {symbol}")
            print(f"   Entry Price: ${entry_price:,.2f}")
            print(f"   Position Size: ${size_usd:,.2f}")
            print(f"   Target 1: ${target_1:,.2f}")
            print(f"   Target 2: ${target_2:,.2f}")
            print(f"   Stop Loss: ${stop_loss:,.2f}")
            print(f"   Rationale: {rationale}")
            
            # Get current token data
            current_data = token_data.get(symbol, {})
            if current_data:
                current_price = current_data.get('price', 0)
                volume = current_data.get('volume', 0)
                market_cap = current_data.get('market_cap', 0)
                price_change = current_data.get('price_change_24h', 0)
                
                print(f"   📈 Current Price: ${current_price:,.2f}")
                print(f"   📊 24h Volume: ${volume:,.0f}")
                print(f"   💰 Market Cap: ${market_cap:,.0f}")
                print(f"   24h Change: {price_change:+.2f}%")
                
                # Calculate P&L if we have both entry and current price
                if entry_price and current_price:
                    pnl_percent = ((current_price - entry_price) / entry_price) * 100
                    pnl_usd = (current_price - entry_price) * (size_usd / entry_price)
                    print(f"   P&L: {pnl_percent:+.2f}% (${pnl_usd:+,.2f})")
                    
                    # Check if targets or stop loss are hit
                    if current_price >= target_2:
                        print(f"   🎯 Target 2 HIT! (${target_2:,.2f})")
                    elif current_price >= target_1:
                        print(f"   🎯 Target 1 HIT! (${target_1:,.2f})")
                    elif current_price <= stop_loss:
                        print(f"   Stop Loss HIT! (${stop_loss:,.2f})")
            else:
                print(f"   ❌ No current data available for {symbol}")
            
            total_value += size_usd
        
        print(f"\n📊 PORTFOLIO TOTALS:")
        print(f"   Total Positions: {total_positions}")
        print(f"   Total Value: ${total_value:,.2f}")
        print("="*80)
    
    async def run(self):
        """Main method to run the portfolio manager"""
        print(" Starting Portfolio Manager...")
        print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"💰 Total Budget: ${self.total_budget}")
        
        try:
            # Step 1: Get active positions
            positions = self.get_active_positions()
            
            if not positions:
                print("ℹ️ No active positions found. Exiting.")
                return
            
            # Step 2: Extract token names
            token_names = self.extract_token_names(positions)
            
            if not token_names:
                print("ℹ️ No token names found in positions. Exiting.")
                return
            
            # Step 3: Get current token data
            token_data = await self.get_token_data(token_names)
            
            if not token_data:
                print("❌ No token data available. Cannot proceed with AI analysis.")
                return
            
            # Step 4: Display portfolio summary
            self.display_portfolio_summary(positions, token_data)
            
            # Step 5: Analyze with AI
            ai_analysis = await self.analyze_portfolio_with_ai(positions, token_data)
            
            # Step 6: Display AI analysis
            self.display_ai_analysis(ai_analysis)
            
            # Step 7: Update database with new positions
            if "error" not in ai_analysis:
                print("\n🔄 Updating database with AI recommendations...")
                update_success = await self.update_positions_in_database(ai_analysis)
                
                if update_success:
                    print("✅ Database updated successfully!")
                else:
                    print("❌ Failed to update database")
            else:
                print("⚠️ Skipping database update due to AI analysis error")
            
            print("\n✅ Portfolio Manager completed successfully!")
            
        except Exception as e:
            print(f"❌ Error in Portfolio Manager: {e}")
            raise

async def main():
    """Main entry point"""
    try:
        # Initialize with $100 budget
        portfolio_manager = PortfolioManager(total_budget=100.0)
        await portfolio_manager.run()
    except KeyboardInterrupt:
        print("\n⏹️ Portfolio Manager stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
