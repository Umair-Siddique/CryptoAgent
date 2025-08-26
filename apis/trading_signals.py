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
    # Use UTC timezone to ensure we get the correct current date
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')

class TradingSignalsAPI:
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
    
    async def get_trading_signals(self, token_symbols: str, start_date: str = None) -> Optional[List[Dict]]:
        """
        Get trading signals data for specific tokens
        
        Args:
            token_symbols: Comma-separated token symbols (e.g., "BTC,ETH,ADA")
            start_date: Start date in YYYY-MM-DD format (default: today)
        """
        if start_date is None:
            start_date = get_today_date()
        
        # Build the endpoint with parameters
        endpoint = f"/v2/trading-signals?startDate={start_date}&symbol={token_symbols.upper()}"
        print(f"Fetching trading signals from: {endpoint}")
        
        result = await self._make_paid_request(endpoint)
        if result and result.get('success') and 'data' in result:
            print(f"✅ Successfully fetched {len(result['data'])} trading signals records")
            return result['data']
        else:
            print(f"❌ Failed to fetch trading signals. Response: {result}")
            return None

    async def get_trading_signals_by_ids(self, token_ids: List[int], start_date: str = None) -> Optional[List[Dict]]:
        """
        Get trading signals data for specific tokens using token IDs
        
        Args:
            token_ids: List of token IDs (e.g., [3375, 3306, 3315])
            start_date: Start date in YYYY-MM-DD format (default: today)
        """
        if start_date is None:
            start_date = get_today_date()
        
        # Join token IDs with comma for the API call
        token_ids_str = ",".join([str(tid) for tid in token_ids])
        
        # Build the endpoint with parameters
        endpoint = f"/v2/trading-signals?startDate={start_date}&token_id={token_ids_str}"
        print(f"Fetching trading signals from: {endpoint}")
        
        result = await self._make_paid_request(endpoint)
        if result and result.get('success') and 'data' in result:
            print(f"✅ Successfully fetched {len(result['data'])} trading signals records")
            return result['data']
        else:
            print(f"❌ Failed to fetch trading signals. Response: {result}")
            return None

async def main():
    """Test function for Trading Signals API"""
    try:
        api = TradingSignalsAPI()
        
        # Get trading signals for BTC, ETH, ADA
        print("Fetching trading signals for BTC, ETH, ADA...")
        signals = await api.get_trading_signals("BTC,ETH,ADA")
        
        if signals:
            print(f"Found {len(signals)} trading signals:")
            for signal in signals:
                print(f"- {signal.get('TOKEN_SYMBOL', 'N/A')} ({signal.get('TOKEN_NAME', 'N/A')})")
                print(f"  Date: {signal.get('DATE', 'N/A')}")
                print(f"  Trading Signal: {signal.get('TRADING_SIGNAL', 'N/A')}")
                print(f"  Token Trend: {signal.get('TOKEN_TREND', 'N/A')}")
                print(f"  Trading Signals Returns: {signal.get('TRADING_SIGNALS_RETURNS', 'N/A')}")
                print(f"  Holding Returns: {signal.get('HOLDING_RETURNS', 'N/A')}")
                print(f"  TM Trader Grade: {signal.get('TM_TRADER_GRADE', 'N/A')}")
                print(f"  TM Investor Grade: {signal.get('TM_INVESTOR_GRADE', 'N/A')}")
                print()
        else:
            print("No trading signals found")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
