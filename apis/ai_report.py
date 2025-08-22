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

class AIReportAPI:
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
    
    async def get_ai_report(self, symbol: str) -> Optional[List[Dict]]:
        """
        Get AI report for a specific token symbol
        
        Args:
            symbol: Token symbol (e.g., "BTC", "ETH")
        """
        endpoint = f"/v2/ai-reports?symbol={symbol.upper()}"
        print(f"Fetching AI report for {symbol.upper()} from: {endpoint}")
        
        result = await self._make_paid_request(endpoint)
        if result and result.get('success') and 'data' in result:
            print(f"✅ Successfully fetched {len(result['data'])} AI report records for {symbol.upper()}")
            return result['data']
        else:
            print(f"❌ Failed to fetch AI report for {symbol.upper()}. Response: {result}")
            return None
    
    def store_ai_report(self, ai_report_data: List[Dict]) -> bool:
        """Store AI report data in Supabase"""
        try:
            if not ai_report_data:
                print("No AI report data to store")
                return True
            
            print(f"Processing {len(ai_report_data)} AI report records")
            
            # Prepare data for insertion
            db_data = []
            seen_combinations = set()  # Track unique combinations
            
            for i, report in enumerate(ai_report_data):
                try:
                    # Debug: Print the first record
                    if i == 0:
                        print(f"Sample AI report data: {report}")
                    
                    # Extract fields from the AI report
                    token_id = report.get('TOKEN_ID')
                    token_symbol = report.get('TOKEN_SYMBOL', '').upper()
                    token_name = report.get('TOKEN_NAME')
                    investment_analysis_pointer = report.get('INVESTMENT_ANALYSIS_POINTER')
                    investment_analysis = report.get('INVESTMENT_ANALYSIS')
                    deep_dive = report.get('DEEP_DIVE')
                    code_review = report.get('CODE_REVIEW')
                    
                    # Create unique combination key
                    combination_key = f"{token_symbol}_{token_id}"
                    
                    # Skip if we've already seen this combination
                    if combination_key in seen_combinations:
                        print(f"Skipping duplicate record: {combination_key}")
                        continue
                    
                    seen_combinations.add(combination_key)
                    
                    # Prepare data for database insertion
                    db_record = {
                        'user_id': self.user_id,
                        'token_id': str(token_id) if token_id else None,
                        'token_name': token_name,
                        'token_symbol': token_symbol,
                        'investment_analysis_pointer': investment_analysis_pointer,
                        'investment_analysis': investment_analysis,
                        'deep_dive': deep_dive,
                        'code_review': code_review,
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    db_data.append(db_record)
                    
                except Exception as e:
                    print(f"Error processing AI report record {i}: {e}")
                    continue
            
            if not db_data:
                print("No valid AI report data to insert")
                return True
            
            # Insert data into Supabase
            print(f"Inserting {len(db_data)} AI report records into Supabase...")
            
            # Use upsert to handle duplicates
            result = self.supabase.table('ai_reports').upsert(
                db_data,
                on_conflict='token_symbol,token_id'
            ).execute()
            
            if result.data:
                print(f"✅ Successfully stored {len(result.data)} AI report records in Supabase")
                return True
            else:
                print("❌ Failed to store AI report data in Supabase")
                return False
                
        except Exception as e:
            print(f"❌ Error storing AI report data: {e}")
            return False
    
    async def get_and_store_ai_report(self, symbol: str) -> bool:
        """
        Get AI report for a symbol and store it in Supabase
        
        Args:
            symbol: Token symbol (e.g., "BTC", "ETH")
        """
        try:
            # Get AI report data
            ai_report_data = await self.get_ai_report(symbol)
            
            if ai_report_data:
                # Store the data
                success = self.store_ai_report(ai_report_data)
                if success:
                    print(f"✅ Successfully fetched and stored AI report for {symbol.upper()}")
                    return True
                else:
                    print(f"❌ Failed to store AI report for {symbol.upper()}")
                    return False
            else:
                print(f"❌ No AI report data received for {symbol.upper()}")
                return False
                
        except Exception as e:
            print(f"❌ Error in get_and_store_ai_report for {symbol}: {e}")
            return False

async def main():
    """Test function for AI Report API"""
    try:
        api = AIReportAPI()
        
        # Test with a few popular tokens
        test_symbols = ["BTC", "ETH", "ADA"]
        
        for symbol in test_symbols:
            print(f"\n{'='*50}")
            print(f"Testing AI Report for {symbol}")
            print(f"{'='*50}")
            
            success = await api.get_and_store_ai_report(symbol)
            
            if success:
                print(f"✅ AI Report test completed successfully for {symbol}")
            else:
                print(f"❌ AI Report test failed for {symbol}")
            
            # Add a small delay between requests
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
