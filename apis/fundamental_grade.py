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

class FundamentalGradeAPI:
    def __init__(self):
        self.key_b64 = os.environ.get("X402_PRIVATE_KEY_B64")
        if not self.key_b64:
            raise RuntimeError("Missing X402_PRIVATE_KEY_B64 in env.")
        self.account = load_account_from_b64(self.key_b64)
        self.timeouts = httpx.Timeout(connect=20.0, read=120.0, write=20.0, pool=20.0)
        
        # Initialize Supabase client
        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_key = os.environ.get('SUPABASE_KEY')
        self.user_id = os.environ.get('USER_ID')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
    
    async def _make_paid_request(self, endpoint: str, headers: Dict[str, str] = None) -> Optional[Dict]:
        """Make a paid request to Token Metrics API"""
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
                    
                    r = await client.get(endpoint, headers=payment_headers)
                    return json.loads((await r.aread()).decode("utf-8", errors="ignore") or "{}")

                except Exception as e:
                    error_msg = f"Request failed: {str(e)}"
                    print(f"❌ API Error: {error_msg}")
                    return {"error": error_msg, "exception": str(e)}
                    
        except Exception as e:
            error_msg = f"Client initialization failed: {str(e)}"
            print(f"❌ API Error: {error_msg}")
            return {"error": error_msg, "exception": str(e)}
    
    async def get_fundamental_grade(self, symbol: str) -> Optional[Dict]:
        """
        Get fundamental grade data for a specific token symbol
        
        Args:
            symbol: Token symbol (e.g., "BTC", "ETH")
        """
        endpoint = f"/v2/fundamental-grade?symbol={symbol.upper()}"
        print(f"Fetching fundamental grade for {symbol.upper()} from: {endpoint}")
        
        result = await self._make_paid_request(endpoint)
        
        # Check if there was an error in the request
        if result and "error" in result:
            print(f"❌ API request failed for {symbol.upper()}: {result['error']}")
            if "response_body" in result:
                print(f"   Response body: {result['response_body']}")
            if "status_code" in result:
                print(f"   Status code: {result['status_code']}")
            if "exception" in result:
                print(f"   Exception: {result['exception']}")
            return None
            
        if result and result.get('success') and 'data' in result and result['data']:
            print(f"✅ Successfully fetched fundamental grade for {symbol.upper()}")
            return result['data'][0]  # Return the first (and only) item
        else:
            print(f"❌ Failed to fetch fundamental grade for {symbol.upper()}. Response: {result}")
            if result:
                print(f"   Success field: {result.get('success')}")
                print(f"   Data field present: {'data' in result}")
                print(f"   Data content: {result.get('data')}")
                print(f"   Full response: {result}")
            return None
    
    def store_fundamental_grade(self, fundamental_data: Dict) -> bool:
        """Store fundamental grade data in Supabase"""
        try:
            if not fundamental_data:
                print("No fundamental grade data to store")
                return False
            
            print(f"Processing fundamental grade data for {fundamental_data.get('TOKEN_SYMBOL', 'Unknown')}")
            
            # Prepare data for insertion
            record = {
                'user_id': self.user_id,
                'token_id': fundamental_data.get('TOKEN_ID'),
                'token_name': fundamental_data.get('TOKEN_NAME'),
                'token_symbol': fundamental_data.get('TOKEN_SYMBOL'),
                'fundamental_grade': float(fundamental_data.get('FUNDAMENTAL_GRADE', 0)) if fundamental_data.get('FUNDAMENTAL_GRADE') else None,
                'fundamental_grade_class': fundamental_data.get('FUNDAMENTAL_GRADE_CLASS'),
                'community_score': float(fundamental_data.get('COMMUNITY_SCORE', 0)) if fundamental_data.get('COMMUNITY_SCORE') else None,
                'exchange_score': float(fundamental_data.get('EXCHANGE_SCORE', 0)) if fundamental_data.get('EXCHANGE_SCORE') else None,
                'vc_score': float(fundamental_data.get('VC_SCORE', 0)) if fundamental_data.get('VC_SCORE') else None,
                'tokenomics_score': float(fundamental_data.get('TOKENOMICS_SCORE', 0)) if fundamental_data.get('TOKENOMICS_SCORE') else None,
                'defi_scanner_score': float(fundamental_data.get('DEFI_SCANNER_SCORE', 0)) if fundamental_data.get('DEFI_SCANNER_SCORE') else None,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            print(f"Sample record structure: {record}")
            
            # Insert data with conflict resolution (upsert)
            result = self.supabase.table('fundamental_grade').upsert(
                record,
                on_conflict='token_symbol'  # Update if token_symbol already exists
            ).execute()
            
            print(f"✅ Successfully stored fundamental grade for {fundamental_data.get('TOKEN_SYMBOL', 'Unknown')}")
            return True
            
        except Exception as e:
            print(f"❌ Error storing fundamental grade data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_fundamental_grade_from_db(self, token_symbol: str) -> Optional[Dict]:
        """Retrieve fundamental grade data from Supabase"""
        try:
            result = self.supabase.table('fundamental_grade')\
                .select('*')\
                .eq('token_symbol', token_symbol.upper())\
                .single()\
                .execute()
            
            if result.data:
                print(f"✅ Retrieved fundamental grade for {token_symbol.upper()}")
                return result.data
            else:
                print(f"ℹ️ No fundamental grade data found for {token_symbol.upper()}")
                return None
                
        except Exception as e:
            print(f"❌ Error retrieving fundamental grade data for {token_symbol}: {e}")
            return None
    
    async def fetch_and_store_fundamental_grade(self, symbol: str) -> bool:
        """
        Fetch fundamental grade from API and store in database
        
        Args:
            symbol: Token symbol (e.g., "BTC", "ETH")
        """
        try:
            # Fetch data from API
            fundamental_data = await self.get_fundamental_grade(symbol)
            
            if fundamental_data:
                # Store in database
                success = self.store_fundamental_grade(fundamental_data)
                return success
            else:
                print(f"❌ No fundamental grade data received for {symbol}")
                return False
                
        except Exception as e:
            print(f"❌ Error in fetch_and_store_fundamental_grade for {symbol}: {e}")
            return False

async def main():
    """Test function for Fundamental Grade API"""
    try:
        api = FundamentalGradeAPI()
        
        # Test with Bitcoin
        print("Fetching fundamental grade for BTC...")
        success = await api.fetch_and_store_fundamental_grade("BTC")
        
        if success:
            print("✅ Successfully fetched and stored fundamental grade for BTC")
            
            # Retrieve from database to verify
            stored_data = api.get_fundamental_grade_from_db("BTC")
            if stored_data:
                print("Retrieved data from database:")
                print(f"Token: {stored_data.get('token_symbol')} ({stored_data.get('token_name')})")
                print(f"Fundamental Grade: {stored_data.get('fundamental_grade')}")
                print(f"Grade Class: {stored_data.get('fundamental_grade_class')}")
                print(f"Community Score: {stored_data.get('community_score')}")
                print(f"Exchange Score: {stored_data.get('exchange_score')}")
                print(f"VC Score: {stored_data.get('vc_score')}")
                print(f"Tokenomics Score: {stored_data.get('tokenomics_score')}")
                print(f"DeFi Scanner Score: {stored_data.get('defi_scanner_score')}")
        else:
            print("❌ Failed to fetch and store fundamental grade for BTC")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
