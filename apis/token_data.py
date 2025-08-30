import os
import base64
import asyncio
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import httpx

from dotenv import load_dotenv
from eth_account import Account
from x402.clients.httpx import x402HttpxClient

try:
    from supabase import create_client, Client
except ImportError:
    print("Supabase client not found. Installing...")
    os.system("pip install supabase")
    from supabase import create_client, Client

load_dotenv()

API_BASE = "https://api.tokenmetrics.com"

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = os.getenv('USER_ID')

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

class TokenDataAPI:
    def __init__(self):
        self.key_b64 = os.environ.get("X402_PRIVATE_KEY_B64")
        if not self.key_b64:
            raise RuntimeError("Missing X402_PRIVATE_KEY_B64 in env.")
        self.account = load_account_from_b64(self.key_b64)
        self.timeouts = httpx.Timeout(connect=20.0, read=120.0, write=20.0, pool=20.0)
        
        # Initialize Supabase client
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Missing Supabase credentials")
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.user_id = USER_ID
    
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
    
    async def get_token_data_by_ids(self, token_ids: List[int]) -> Optional[List[Dict]]:
        """
        Get token data for specific token IDs
        
        Args:
            token_ids: List of token IDs to fetch data for
        """
        if not token_ids:
            print("No token IDs provided")
            return None
        
        # Create comma-separated string of token IDs
        token_ids_str = ",".join([str(tid) for tid in token_ids])
        endpoint = f"/v2/tokens?token_id={token_ids_str}"
        
        print(f"Fetching token data for IDs: {token_ids_str}")
        
        result = await self._make_paid_request(endpoint)
        if result and result.get('success') and 'data' in result:
            print(f"✅ Successfully fetched token data for {len(result['data'])} tokens")
            return result['data']
        else:
            print(f"❌ Failed to fetch token data. Response: {result}")
            return None
    
    def store_token_data(self, token_data: List[Dict]) -> bool:
        """
        Store token data in Supabase
        
        Args:
            token_data: List of token data dictionaries
        """
        if not token_data:
            print("No token data to store")
            return False
        
        try:
            db_data = []
            seen_tokens = set()
            
            for i, record in enumerate(token_data):
                try:
                    token_id = record.get('TOKEN_ID')
                    token_name = record.get('TOKEN_NAME', '')
                    token_symbol = record.get('TOKEN_SYMBOL', '').upper()
                    
                    if not token_symbol:
                        print(f"Skipping record {i}: missing token symbol")
                        continue
                    
                    # Skip if we've already processed this token
                    combination_key = f"{token_symbol}_{token_id}"
                    if combination_key in seen_tokens:
                        continue
                    
                    seen_tokens.add(combination_key)
                    
                    # Map fields to match the exact database schema
                    db_record = {
                        'user_id': self.user_id,
                        'token_id': str(token_id) if token_id else None,
                        'token_name': token_name,
                        'token_symbol': token_symbol,
                        'current_price': float(record.get('CURRENT_PRICE', 0)) if record.get('CURRENT_PRICE') else None,
                        'market_cap': float(record.get('MARKET_CAP', 0)) if record.get('MARKET_CAP') else None,
                        'total_volume': float(record.get('TOTAL_VOLUME', 0)) if record.get('TOTAL_VOLUME') else None,
                        'circulating_supply': float(record.get('CIRCULATING_SUPPLY', 0)) if record.get('CIRCULATING_SUPPLY') else None,
                        'total_supply': float(record.get('TOTAL_SUPPLY', 0)) if record.get('TOTAL_SUPPLY') else None,
                        'max_supply': float(record.get('MAX_SUPPLY', 0)) if record.get('MAX_SUPPLY') else None,
                        'fully_diluted_valuation': float(record.get('FULLY_DILUTED_VALUATION', 0)) if record.get('FULLY_DILUTED_VALUATION') else None,
                        'high_24h': float(record.get('HIGH_24H', 0)) if record.get('HIGH_24H') else None,
                        'low_24h': float(record.get('LOW_24H', 0)) if record.get('LOW_24H') else None,
                        'price_change_percentage_24h': float(record.get('PRICE_CHANGE_PERCENTAGE_24H_IN_CURRENCY', 0)) if record.get('PRICE_CHANGE_PERCENTAGE_24H_IN_CURRENCY') else None,
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    db_data.append(db_record)
                    
                except Exception as e:
                    print(f"Error processing token data record {i}: {e}")
                    continue
            
            if not db_data:
                print("No valid token data to insert")
                return False
            
            print(f"Inserting {len(db_data)} unique token records...")
            
            # Use simple insert instead of upsert to avoid constraint issues
            result = self.supabase.table('tokens').insert(db_data).execute()
            
            if result.data:
                print(f"✅ Successfully stored {len(result.data)} token records in Supabase")
                return True
            else:
                print("❌ Failed to store token data in Supabase")
                return False
                
        except Exception as e:
            print(f"❌ Error storing token data: {e}")
            return False
    
    async def get_and_store_token_data(self, token_ids: List[int]) -> bool:
        """
        Get token data from API and store in Supabase
        
        Args:
            token_ids: List of token IDs to fetch and store
        """
        try:
            # Fetch token data from API
            token_data = await self.get_token_data_by_ids(token_ids)
            
            if not token_data:
                print("❌ No token data received from API")
                return False
            
            # Store in Supabase
            success = self.store_token_data(token_data)
            
            if success:
                print(f"✅ Successfully processed token data for {len(token_ids)} tokens")
            else:
                print(f"❌ Failed to store token data for {len(token_ids)} tokens")
            
            return success
            
        except Exception as e:
            print(f"❌ Error in get_and_store_token_data: {e}")
            return False
