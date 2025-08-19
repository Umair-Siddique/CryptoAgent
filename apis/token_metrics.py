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
    
    async def get_hourly_ohlcv(self, token_symbol: str, hours: int = 24) -> Optional[List[Dict]]:
        """Get hourly OHLCV data for a specific token"""
        endpoint = "/v2/hourly-ohlcv"
        headers = {
            "symbol": token_symbol.upper(),
            "hours": str(hours)
        }
        
        result = await self._make_paid_request(endpoint, headers)
        if result and 'data' in result:
            return result['data']
        return None

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