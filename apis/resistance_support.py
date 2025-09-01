#!/usr/bin/env python3
"""
Resistance Support API
This module handles fetching resistance and support levels for tokens
and storing them in Supabase
"""

import os
import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import httpx
import base64
from eth_account import Account
from x402.clients.httpx import x402HttpxClient

# Supabase client
try:
    from supabase import create_client, Client
except ImportError:
    print("Supabase client not found. Installing...")
    os.system("pip install supabase")
    from supabase import create_client, Client

load_dotenv()

API_BASE = "https://api.tokenmetrics.com"

def load_account_from_b64(b64: str) -> Account:
    raw = base64.b64decode(b64)
    priv32 = raw[:32]  # first 32 bytes
    return Account.from_key(priv32)

def pick_payment_token_from_accepts(accepts: list[str|dict]) -> Optional[Dict[str, Any]]:
    """
    Normalize and pick the first accept entry. Prefer USDC if present, else take TMAI.
    Each entry can be a dict (newer servers) or string alias.
    """
    norm = []
    for a in accepts:
        if isinstance(a, dict):
            norm.append(a)
        else:
            norm.append({"scheme":"exact","asset":a})
    # prefer usdc-like
    preferred = [x for x in norm if str(x.get("asset","")).lower().startswith("usdc") or str(x.get("extra",{}).get("name","")).lower()=="usdc"]
    if preferred:
        return preferred[0]
    # else take first
    return norm[0] if norm else None

class ResistanceSupportAPI:
    def __init__(self):
        # Use X402 payment system like other APIs
        self.key_b64 = os.environ.get("X402_PRIVATE_KEY_B64")
        if not self.key_b64:
            raise RuntimeError("Missing X402_PRIVATE_KEY_B64 in env.")
        self.account = load_account_from_b64(self.key_b64)
        self.timeouts = httpx.Timeout(connect=20.0, read=120.0, write=20.0, pool=20.0)
        
        # Initialize Supabase client
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials: SUPABASE_URL, SUPABASE_KEY")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        print("✅ ResistanceSupportAPI initialized successfully")
    
    async def _make_paid_request(self, endpoint: str, headers: Dict[str, str] = None) -> Optional[Dict]:
        """Make a paid request to Token Metrics API using X402 payment system"""
        try:
            async with x402HttpxClient(account=self.account, base_url=API_BASE, timeout=self.timeouts) as client:
                # Preflight to get payment requirements
                try:
                    pre = await client.get(
                        endpoint,
                        headers={
                            "x-coinbase-402": "true",
                            "accept": "application/json",
                            **(headers or {})
                        },
                    )
                    
                    if pre.status_code == 200:
                        return json.loads((await pre.aread()).decode("utf-8", errors="ignore") or "{}")
                    
                    # Expect 402 with accepts
                    body = json.loads((await pre.aread()).decode("utf-8", errors="ignore") or "{}")
                    accepts = body.get("accepts", [])
                    if not accepts:
                        error_msg = f"No 'accepts' found in 402 challenge: {body}"
                        print(f"❌ API Error: {error_msg}")
                        return {"error": error_msg, "status_code": pre.status_code, "response_body": body}

                    chosen = pick_payment_token_from_accepts(accepts)
                    if not chosen:
                        error_msg = f"Could not pick token from accepts: {accepts}"
                        print(f"❌ API Error: {error_msg}")
                        return {"error": error_msg, "status_code": pre.status_code, "response_body": body}

                    # Real call with payment
                    payment_headers = {
                        "x-coinbase-402": "true",
                        "accept": "application/json",
                        **(headers or {})
                    }
                    
                    alias = (chosen.get("extra", {}) or {}).get("name")
                    if alias:
                        payment_headers["x-payment-token"] = alias.lower()
                    else:
                        if chosen.get("asset"):
                            payment_headers["x-payment-token"] = str(chosen["asset"])

                    r = await client.get(endpoint, headers=payment_headers)
                    return json.loads((await r.aread()).decode("utf-8", errors="ignore") or "{}")

                except httpx.TimeoutException as e:
                    print(f"Request timed out for {endpoint}: {e}")
                    return None
                except Exception as e:
                    print(f"Request failed for {endpoint}: {e}")
                    return None
                    
        except Exception as e:
            print(f"Error in _make_paid_request: {e}")
            return None

    async def get_resistance_support_by_id(self, token_id: int) -> Optional[Dict[str, Any]]:
        """
        Get resistance and support levels for a specific token by ID
        
        Args:
            token_id (int): The token ID to fetch data for
            
        Returns:
            Optional[Dict]: Resistance support data or None if failed
        """
        try:
            print(f"🔄 Fetching resistance support data for token ID {token_id}...")
            
            endpoint = f"/v2/resistance-support"
            params = {
                'limit': 50,
                'page': 1
            }
            
            # Build URL with query parameters
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            full_endpoint = f"{endpoint}?{query_string}"
            
            data = await self._make_paid_request(full_endpoint)
            
            if data and not data.get('error'):
                if data.get('success') and data.get('data'):
                    # Find the specific token in the response
                    for token_data in data['data']:
                        if token_data.get('TOKEN_ID') == token_id:
                            print(f"✅ Found resistance support data for token ID {token_id}")
                            return token_data
                    
                    print(f"⚠️ Token ID {token_id} not found in resistance support data")
                    return None
                else:
                    print(f"❌ No data returned for token ID {token_id}")
                    return None
            else:
                error_msg = data.get('error', 'Unknown error') if data else 'No response'
                print(f"❌ API request failed: {error_msg}")
                return None
                
        except Exception as e:
            print(f"❌ Error fetching resistance support for token ID {token_id}: {e}")
            return None

    async def get_resistance_support_multiple_by_ids(self, token_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        Get resistance and support levels for multiple tokens by IDs
        
        Args:
            token_ids (List[int]): List of token IDs to fetch data for
            
        Returns:
            Dict[int, Dict]: Dictionary mapping token ID to resistance support data
        """
        try:
            print(f"🔄 Fetching resistance support data for {len(token_ids)} tokens...")
            
            endpoint = f"/v2/resistance-support"
            params = {
                'limit': 50,
                'page': 1
            }
            
            # Build URL with query parameters
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            full_endpoint = f"{endpoint}?{query_string}"
            
            data = await self._make_paid_request(full_endpoint)
            
            if data and not data.get('error'):
                if data.get('success') and data.get('data'):
                    # Create a mapping of token ID to data
                    result = {}
                    available_tokens = set()
                    
                    for token_data in data['data']:
                        token_id = token_data.get('TOKEN_ID')
                        if token_id in token_ids:
                            result[token_id] = token_data
                            available_tokens.add(token_id)
                    
                    # Check which tokens were found
                    missing_tokens = set(token_ids) - available_tokens
                    if missing_tokens:
                        print(f"⚠️ Resistance support data not found for tokens: {missing_tokens}")
                    
                    print(f"✅ Found resistance support data for {len(result)} out of {len(token_ids)} tokens")
                    return result
                else:
                    print(f"❌ No data returned from resistance support API")
                    return {}
            else:
                error_msg = data.get('error', 'Unknown error') if data else 'No response'
                print(f"❌ API request failed: {error_msg}")
                return {}
                
        except Exception as e:
            print(f"❌ Error fetching resistance support data: {e}")
            return {}
    
    def store_resistance_support_data(self, token_symbol: str, resistance_support_data: Dict[str, Any]) -> bool:
        """
        Store resistance support data in Supabase
        
        Args:
            token_symbol (str): Token symbol for identification
            resistance_support_data (Dict): Resistance support data to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"�� Storing resistance support data for {token_symbol} in Supabase...")
            
            # Prepare data for storage
            data_to_store = {
                'token_symbol': token_symbol.upper(),
                'token_id': resistance_support_data.get('TOKEN_ID'),
                'token_name': resistance_support_data.get('TOKEN_NAME'),
                'date': resistance_support_data.get('DATE'),
                'historical_levels': resistance_support_data.get('HISTORICAL_RESISTANCE_SUPPORT_LEVELS', [])
            }
            
            # Validate required fields
            if not data_to_store['token_symbol']:
                print(f"❌ Missing token symbol for {token_symbol}")
                return False
            
            if not data_to_store['historical_levels']:
                print(f"⚠️ No historical levels found for {token_symbol}")
                # Still store the record but with empty levels
                data_to_store['historical_levels'] = []
            
            # Insert or update data using upsert
            response = self.supabase.table('resistance_support').upsert(
                data_to_store,
                on_conflict='token_symbol,date'
            ).execute()
            
            if response.data:
                print(f"✅ Successfully stored resistance support data for {token_symbol}")
                print(f"   - Token ID: {data_to_store['token_id']}")
                print(f"   - Token Name: {data_to_store['token_name']}")
                print(f"   - Historical Levels: {len(data_to_store['historical_levels'])}")
                print(f"   - Date: {data_to_store['date']}")
                return True
            else:
                print(f"❌ Failed to store resistance support data for {token_symbol}")
                return False
                
        except Exception as e:
            print(f"❌ Error storing resistance support data for {token_symbol}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def get_stored_resistance_support_data(self, token_symbol: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve stored resistance support data from Supabase
        
        Args:
            token_symbol (str): Token symbol to retrieve data for
            
        Returns:
            Optional[Dict]: Stored data or None if not found
        """
        try:
            print(f"🔍 Retrieving stored resistance support data for {token_symbol}...")
            
            response = self.supabase.table('resistance_support').select('*').eq('token_symbol', token_symbol.upper()).order('date', desc=True).limit(1).execute()
            
            if response.data:
                data = response.data[0]
                print(f"✅ Found stored data for {token_symbol}")
                print(f"   - Date: {data.get('date')}")
                print(f"   - Historical Levels: {len(data.get('historical_levels', []))}")
                return data
            else:
                print(f"ℹ️ No stored resistance support data found for {token_symbol}")
                return None
                
        except Exception as e:
            print(f"❌ Error retrieving stored resistance support data for {token_symbol}: {e}")
            return None
    
    def get_nearest_support_resistance_levels(self, resistance_support_data: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """
        Calculate nearest support and resistance levels based on current price
        
        Args:
            resistance_support_data (Dict): Resistance support data
            current_price (float): Current token price
            
        Returns:
            Dict: Nearest support and resistance levels
        """
        try:
            if not resistance_support_data or 'HISTORICAL_RESISTANCE_SUPPORT_LEVELS' not in resistance_support_data:
                return {}
            
            levels = resistance_support_data['HISTORICAL_RESISTANCE_SUPPORT_LEVELS']
            if not levels:
                return {}
            
            # Extract all price levels
            price_levels = [level['level'] for level in levels if 'level' in level]
            
            if not price_levels:
                return {}
            
            # Find nearest support (below current price)
            support_levels = [price for price in price_levels if price < current_price]
            nearest_support = max(support_levels) if support_levels else None
            
            # Find nearest resistance (above current price)
            resistance_levels = [price for price in price_levels if price > current_price]
            nearest_resistance = min(resistance_levels) if resistance_levels else None
            
            # Calculate distances as percentages
            support_distance = None
            resistance_distance = None
            
            if nearest_support:
                support_distance = ((current_price - nearest_support) / current_price) * 100
            
            if nearest_resistance:
                resistance_distance = ((nearest_resistance - current_price) / current_price) * 100
            
            return {
                'nearest_support': nearest_support,
                'nearest_resistance': nearest_resistance,
                'current_price': current_price,
                'total_levels': len(price_levels),
                'support_distance_percent': support_distance,
                'resistance_distance_percent': resistance_distance,
                'support_distance_usd': current_price - nearest_support if nearest_support else None,
                'resistance_distance_usd': nearest_resistance - current_price if nearest_resistance else None
            }
            
        except Exception as e:
            print(f"❌ Error calculating nearest support/resistance levels: {e}")
            return {}
    
    def analyze_support_resistance_trends(self, resistance_support_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze trends in support and resistance levels
        
        Args:
            resistance_support_data (Dict): Resistance support data
            
        Returns:
            Dict: Analysis results
        """
        try:
            if not resistance_support_data or 'HISTORICAL_RESISTANCE_SUPPORT_LEVELS' not in resistance_support_data:
                return {}
            
            levels = resistance_support_data['HISTORICAL_RESISTANCE_SUPPORT_LEVELS']
            if not levels:
                return {}
            
            # Sort levels by date
            sorted_levels = sorted(levels, key=lambda x: x.get('date', ''))
            
            # Calculate price ranges over time
            if len(sorted_levels) >= 2:
                first_level = sorted_levels[0]['level']
                last_level = sorted_levels[-1]['level']
                price_change = last_level - first_level
                price_change_percent = (price_change / first_level) * 100 if first_level > 0 else 0
                
                # Find highest and lowest levels
                all_levels = [level['level'] for level in levels]
                highest_level = max(all_levels)
                lowest_level = min(all_levels)
                
                # Calculate average level
                avg_level = sum(all_levels) / len(all_levels)
                
                # Find most recent levels (last 5)
                recent_levels = sorted_levels[-5:] if len(sorted_levels) >= 5 else sorted_levels
                recent_avg = sum(level['level'] for level in recent_levels) / len(recent_levels)
                
                return {
                    'total_levels': len(levels),
                    'first_level_date': sorted_levels[0].get('date'),
                    'last_level_date': sorted_levels[-1].get('date'),
                    'first_level_price': first_level,
                    'last_level_price': last_level,
                    'price_change': price_change,
                    'price_change_percent': price_change_percent,
                    'highest_level': highest_level,
                    'lowest_level': lowest_level,
                    'price_range': highest_level - lowest_level,
                    'average_level': avg_level,
                    'recent_average_level': recent_avg,
                    'trend': 'bullish' if price_change > 0 else 'bearish' if price_change < 0 else 'sideways',
                    'volatility': (highest_level - lowest_level) / avg_level * 100 if avg_level > 0 else 0
                }
            
            return {}
            
        except Exception as e:
            print(f"❌ Error analyzing support/resistance trends: {e}")
            return {}
    
    async def cleanup_old_data(self, days_to_keep: int = 30) -> bool:
        """
        Clean up old resistance support data
        
        Args:
            days_to_keep (int): Number of days to keep data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"🧹 Cleaning up resistance support data older than {days_to_keep} days...")
            
            # Calculate cutoff date
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            # Delete old records
            response = self.supabase.table('resistance_support').delete().lt('created_at', cutoff_date.isoformat()).execute()
            
            if response.data is not None:
                print(f"✅ Cleaned up old resistance support data")
                return True
            else:
                print(f"⚠️ No old data to clean up")
                return True
                
        except Exception as e:
            print(f"❌ Error cleaning up old data: {e}")
            return False

async def main():
    """Test the API"""
    try:
        api = ResistanceSupportAPI()
        
        # Test with a single token
        print("Testing single token fetch...")
        result = await api.get_resistance_support_by_id(3306)  # ETH
        if result:
            print(f"✅ Found data for {result.get('TOKEN_NAME')}")
            print(f"   Historical levels: {len(result.get('HISTORICAL_RESISTANCE_SUPPORT_LEVELS', []))}")
            
            # Test storing in Supabase
            print("\nTesting data storage...")
            storage_success = api.store_resistance_support_data('ETH', result)
            if storage_success:
                print("✅ Data stored successfully")
                
                # Test retrieving stored data
                print("\nTesting data retrieval...")
                stored_data = await api.get_stored_resistance_support_data('ETH')
                if stored_data:
                    print("✅ Stored data retrieved successfully")
                    
                    # Test analysis functions
                    print("\nTesting analysis functions...")
                    if result.get('HISTORICAL_RESISTANCE_SUPPORT_LEVELS'):
                        # Test with a sample price
                        sample_price = 3000.0
                        nearest_levels = api.get_nearest_support_resistance_levels(result, sample_price)
                        print(f"Nearest levels for ${sample_price}: {nearest_levels}")
                        
                        trends = api.analyze_support_resistance_trends(result)
                        print(f"Trend analysis: {trends}")
        
        # Test with multiple tokens
        print("\nTesting multiple tokens fetch...")
        results = await api.get_resistance_support_multiple_by_ids([3306, 3375])  # ETH, BTC
        print(f"✅ Found data for {len(results)} tokens")
        
        for token_id, data in results.items():
            print(f"   Token ID {token_id}: {data.get('TOKEN_NAME')} - {len(data.get('HISTORICAL_RESISTANCE_SUPPORT_LEVELS', []))} levels")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
