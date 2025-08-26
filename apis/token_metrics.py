import os
import base64
import asyncio
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, date
import httpx

from dotenv import load_dotenv
from eth_account import Account
from x402.clients.httpx import x402HttpxClient

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

def get_today_date() -> str:
    """Get today's date in YYYY-MM-DD format"""
    return date.today().strftime('%Y-%m-%d')

class TokenMetricsAPI:
    def __init__(self):
        self.key_b64 = os.environ.get("X402_PRIVATE_KEY_B64")
        if not self.key_b64:
            raise RuntimeError("Missing X402_PRIVATE_KEY_B64 in env.")
        self.account = load_account_from_b64(self.key_b64)
        self.timeouts = httpx.Timeout(connect=20.0, read=120.0, write=20.0, pool=20.0)
    
    async def _make_paid_request(self, endpoint: str, headers: Dict[str, str] = None) -> Optional[Dict]:
        """Make a paid request to Token Metrics API"""
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
                    raise RuntimeError(f"No 'accepts' found in 402 challenge: {body}")

                chosen = pick_payment_token_from_accepts(accepts)
                if not chosen:
                    raise RuntimeError(f"Could not pick token from accepts: {accepts}")

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
    
    async def get_tokens(self, limit: int = 3, page: int = 1, category: str = None, exchange: str = None) -> Optional[List[Dict]]:
        """
        Get tokens from /v2/tokens endpoint with optional filtering
        
        Args:
            limit: Number of tokens to fetch (default: 3)
            page: Page number (default: 1)
            category: Comma-separated category names (e.g., "defi,yield farming,altcoin")
            exchange: Comma-separated exchange names (e.g., "binance,gate,coinbase")
        """
        # Build the endpoint with parameters
        params = [f"limit={limit}", f"page={page}"]
        
        if category:
            params.append(f"category={category}")
        
        if exchange:
            params.append(f"exchange={exchange}")
        
        endpoint = f"/v2/tokens?{'&'.join(params)}"
        print(f"Fetching tokens from: {endpoint}")
        
        result = await self._make_paid_request(endpoint)
        if result and result.get('success') and 'data' in result:
            print(f"Successfully fetched {len(result['data'])} tokens from API")
            return result['data']
        else:
            print(f"Failed to fetch tokens. Response: {result}")
            return None
    
    async def get_hourly_ohlcv_today(self, token_symbol: str) -> Optional[List[Dict]]:
        """
        Get hourly OHLCV data for today only for a specific token
        
        Args:
            token_symbol: Token symbol (e.g., "BTC", "ETH")
        """
        # Use the correct endpoint that returns multiple tokens
        endpoint = f"/v2/hourly-ohlcv?limit=50&page=1"
        print(f"Fetching hourly OHLCV data from: {endpoint}")
        
        result = await self._make_paid_request(endpoint)
        if result and result.get('success') and 'data' in result and result['data']:
            # Filter data for the specific token
            filtered_data = [
                record for record in result['data'] 
                if record.get('TOKEN_SYMBOL', '').upper() == token_symbol.upper()
            ]
            
            if filtered_data:
                print(f"✅ Successfully fetched {len(filtered_data)} hourly OHLCV records for {token_symbol.upper()}")
                return filtered_data
            else:
                print(f"ℹ️ No hourly OHLCV data found for {token_symbol.upper()}")
                return []
        else:
            print(f"❌ Failed to fetch hourly OHLCV data. Response: {result}")
            return None
    
    async def get_daily_ohlcv_today(self, token_symbol: str) -> Optional[List[Dict]]:
        """
        Get daily OHLCV data for today only for a specific token
        
        Args:
            token_symbol: Token symbol (e.g., "BTC", "ETH")
        """
        # Use the correct endpoint that returns multiple tokens
        endpoint = f"/v2/daily-ohlcv?limit=50&page=1"
        print(f"Fetching daily OHLCV data from: {endpoint}")
        
        result = await self._make_paid_request(endpoint)
        if result and result.get('success') and 'data' in result and result['data']:
            # Filter data for the specific token
            filtered_data = [
                record for record in result['data'] 
                if record.get('TOKEN_SYMBOL', '').upper() == token_symbol.upper()
            ]
            
            if filtered_data:
                print(f"✅ Successfully fetched {len(filtered_data)} daily OHLCV records for {token_symbol.upper()}")
                return filtered_data
            else:
                print(f"ℹ️ No daily OHLCV data found for {token_symbol.upper()}")
                return []
        else:
            print(f"❌ Failed to fetch daily OHLCV data. Response: {result}")
            return None
    
    # Keep the original methods for backward compatibility
    async def get_hourly_ohlcv(self, token_symbol: str, hours: int = 24) -> Optional[List[Dict]]:
        """
        Get hourly OHLCV data for a specific token (legacy method)
        
        Args:
            token_symbol: Token symbol (e.g., "BTC", "ETH")
            hours: Number of hours to fetch (default: 24)
        """
        endpoint = f"/v2/hourly-ohlcv?symbol={token_symbol.upper()}&hours={hours}"
        print(f"Fetching hourly OHLCV for {token_symbol.upper()} from: {endpoint}")
        
        result = await self._make_paid_request(endpoint)
        if result and result.get('success') and 'data' in result:
            print(f"Successfully fetched {len(result['data'])} hourly OHLCV records for {token_symbol.upper()}")
            return result['data']
        else:
            print(f"Failed to fetch hourly OHLCV for {token_symbol.upper()}. Response: {result}")
            return None

   
    
    async def get_daily_ohlcv(self, token_symbol: str, days: int = 30) -> Optional[List[Dict]]:
        """
        Get daily OHLCV data for a specific token (legacy method)
        
        Args:
            token_symbol: Token symbol (e.g., "BTC", "ETH")
            days: Number of days to fetch (default: 30)
        """
        endpoint = f"/v2/daily-ohlcv?symbol={token_symbol.upper()}&days={days}"
        print(f"Fetching daily OHLCV for {token_symbol.upper()} from: {endpoint}")
        
        result = await self._make_paid_request(endpoint)
        if result and result.get('success') and 'data' in result:
            print(f"Successfully fetched {len(result['data'])} daily OHLCV records for {token_symbol.upper()}")
            return result['data']
        else:
            print(f"Failed to fetch daily OHLCV for {token_symbol.upper()}. Response: {result}")
            return None

    async def get_hourly_ohlcv_by_id(self, token_id: int) -> Optional[List[Dict]]:
        """
        Get hourly OHLCV data for today only for a specific token using token ID
        
        Args:
            token_id: Token ID (e.g., 3375 for BTC)
        """
        # Use the correct endpoint that returns multiple tokens
        endpoint = f"/v2/hourly-ohlcv?limit=50&page=1"
        print(f"Fetching hourly OHLCV data from: {endpoint}")
        
        result = await self._make_paid_request(endpoint)
        if result and result.get('success') and 'data' in result and result['data']:
            # Filter data for the specific token ID
            filtered_data = [
                record for record in result['data'] 
                if record.get('TOKEN_ID') == token_id
            ]
            
            if filtered_data:
                print(f"✅ Successfully fetched {len(filtered_data)} hourly OHLCV records for token ID {token_id}")
                return filtered_data
            else:
                print(f"ℹ️ No hourly OHLCV data found for token ID {token_id}")
                return []
        else:
            print(f"❌ Failed to fetch hourly OHLCV data. Response: {result}")
            return None
    
    async def get_daily_ohlcv_by_id(self, token_id: int) -> Optional[List[Dict]]:
        """
        Get daily OHLCV data for today only for a specific token using token ID
        
        Args:
            token_id: Token ID (e.g., 3375 for BTC)
        """
        # Use the correct endpoint that returns multiple tokens
        endpoint = f"/v2/daily-ohlcv?limit=50&page=1"
        print(f"Fetching daily OHLCV data from: {endpoint}")
        
        result = await self._make_paid_request(endpoint)
        if result and result.get('success') and 'data' in result and result['data']:
            # Filter data for the specific token ID
            filtered_data = [
                record for record in result['data'] 
                if record.get('TOKEN_ID') == token_id
            ]
            
            if filtered_data:
                print(f"✅ Successfully fetched {len(filtered_data)} daily OHLCV records for token ID {token_id}")
                return filtered_data
            else:
                print(f"ℹ️ No daily OHLCV data found for token ID {token_id}")
                return []
        else:
            print(f"❌ Failed to fetch daily OHLCV data. Response: {result}")
            return None

    async def get_ohlcv_data_multiple(self, symbols: List[str]) -> Dict[str, Dict[str, List[Dict]]]:
        """
        Get both hourly and daily OHLCV data for multiple tokens in a single call
        
        Args:
            symbols: List of token symbols (e.g., ["BTC", "ETH", "ADA"])
        """
        try:
            print(f"📈 Fetching OHLCV data for {', '.join(symbols)}...")
            
            # Join symbols with comma for the API call
            symbols_str = ",".join([s.upper() for s in symbols])
            
            # Fetch hourly OHLCV data for all symbols at once
            hourly_endpoint = f"/v2/hourly-ohlcv?symbol={symbols_str}&limit=50&page=1"
            print(f"Fetching hourly OHLCV from: {hourly_endpoint}")
            hourly_result = await self._make_paid_request(hourly_endpoint)
            
            # Fetch daily OHLCV data for all symbols at once
            daily_endpoint = f"/v2/daily-ohlcv?symbol={symbols_str}&limit=50&page=1"
            print(f"Fetching daily OHLCV from: {daily_endpoint}")
            daily_result = await self._make_paid_request(daily_endpoint)
            
            # Organize data by symbol
            result = {}
            for symbol in symbols:
                symbol_upper = symbol.upper()
                result[symbol_upper] = {
                    'hourly': [],
                    'daily': []
                }
                
                # Filter hourly data for this symbol
                if hourly_result and hourly_result.get('success') and 'data' in hourly_result:
                    symbol_hourly = [record for record in hourly_result['data'] 
                                   if record.get('TOKEN_SYMBOL', '').upper() == symbol_upper]
                    result[symbol_upper]['hourly'] = symbol_hourly
                
                # Filter daily data for this symbol
                if daily_result and daily_result.get('success') and 'data' in daily_result:
                    symbol_daily = [record for record in daily_result['data'] 
                                  if record.get('TOKEN_SYMBOL', '').upper() == symbol_upper]
                    result[symbol_upper]['daily'] = symbol_daily
            
            return result
            
        except Exception as e:
            print(f"❌ Error fetching OHLCV data for multiple symbols: {e}")
            return {}

    async def get_ohlcv_data_multiple_by_ids(self, token_ids: List[int]) -> Dict[int, Dict[str, List[Dict]]]:
        """
        Get both hourly and daily OHLCV data for multiple tokens using token IDs
        
        Args:
            token_ids: List of token IDs (e.g., [3375, 3306, 3315])
        """
        try:
            print(f"📈 Fetching OHLCV data for token IDs: {token_ids}...")
            
            # Fetch hourly OHLCV data for all tokens at once
            hourly_endpoint = f"/v2/hourly-ohlcv?limit=50&page=1"
            print(f"Fetching hourly OHLCV from: {hourly_endpoint}")
            hourly_result = await self._make_paid_request(hourly_endpoint)
            
            # Fetch daily OHLCV data for all tokens at once
            daily_endpoint = f"/v2/daily-ohlcv?limit=50&page=1"
            print(f"Fetching daily OHLCV from: {daily_endpoint}")
            daily_result = await self._make_paid_request(daily_endpoint)
            
            # Organize data by token ID
            result = {}
            for token_id in token_ids:
                result[token_id] = {
                    'hourly': [],
                    'daily': []
                }
                
                # Filter hourly data for this token ID
                if hourly_result and hourly_result.get('success') and 'data' in hourly_result:
                    token_hourly = [record for record in hourly_result['data'] 
                                  if record.get('TOKEN_ID') == token_id]
                    result[token_id]['hourly'] = token_hourly
                
                # Filter daily data for this token ID
                if daily_result and daily_result.get('success') and 'data' in daily_result:
                    token_daily = [record for record in daily_result['data'] 
                                 if record.get('TOKEN_ID') == token_id]
                    result[token_id]['daily'] = token_daily
            
            return result
            
        except Exception as e:
            print(f"❌ Error fetching OHLCV data for multiple token IDs: {e}")
            return {}

async def main():
    """Test function for Token Metrics API"""
    try:
        api = TokenMetricsAPI()
        
        # Get 3 altcoin tokens from major exchanges
        print("Fetching 3 altcoin tokens from /v2/tokens...")
        tokens = await api.get_tokens(
            limit=3, 
            page=1,
            category="altcoin,defi",  # Filter for altcoins and DeFi tokens
            exchange="binance,coinbase,gate"  # Filter for major exchanges
        )
        
        if tokens:
            print(f"Found {len(tokens)} tokens:")
            for token in tokens:
                print(f"- {token.get('TOKEN_SYMBOL', 'N/A')} ({token.get('TOKEN_NAME', 'N/A')})")
                print(f"  Price: ${token.get('CURRENT_PRICE', 'N/A')}")
                print(f"  Market Cap: ${token.get('MARKET_CAP', 'N/A')}")
                print(f"  24h Change: {token.get('PRICE_CHANGE_PERCENTAGE_24H_IN_CURRENCY', 'N/A')}%")
                print()
        else:
            print("No tokens found")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())