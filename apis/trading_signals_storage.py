import os
from datetime import datetime, timezone
from typing import List, Dict, Any
from dotenv import load_dotenv

try:
    from supabase import create_client, Client
except ImportError:
    print("Supabase client not found. Installing...")
    os.system("pip install supabase")
    from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = os.getenv('USER_ID')

class TradingSignalsStorage:
    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Missing Supabase credentials")
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string with multiple format support"""
        if not date_str:
            return datetime.now(timezone.utc)
        
        # Try different date formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',  # 2025-01-26T00:00:00.000Z
            '%Y-%m-%dT%H:%M:%SZ',     # 2025-01-26T00:00:00Z
            '%Y-%m-%dT%H:%M:%S',      # 2025-01-26T00:00:00
            '%Y-%m-%d',               # 2025-01-26
        ]
        
        for fmt in formats:
            try:
                if fmt.endswith('Z'):
                    dt = datetime.strptime(date_str, fmt)
                    return dt.replace(tzinfo=timezone.utc)
                else:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        
        # If all formats fail, try isoformat
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            print(f"Warning: Could not parse date '{date_str}', using current time")
            return datetime.now(timezone.utc)
    
    def store_trading_signals(self, trading_signals_data: List[Dict]) -> bool:
        """Store trading signals data in Supabase"""
        try:
            if not trading_signals_data:
                print("No trading signals data to store")
                return True
            
            print(f"Processing {len(trading_signals_data)} trading signals records")
            
            # Prepare data for insertion
            db_data = []
            seen_combinations = set()  # Track unique combinations
            
            for i, signal in enumerate(trading_signals_data):
                try:
                    # Debug: Print the first record
                    if i == 0:
                        print(f"Sample signal data: {signal}")
                    
                    # Handle different possible field names from API
                    date_str = signal.get('DATE') or signal.get('date')
                    token_id = signal.get('TOKEN_ID') or signal.get('token_id')
                    token_name = signal.get('TOKEN_NAME') or signal.get('token_name')
                    token_sym = signal.get('TOKEN_SYMBOL') or signal.get('token_symbol')
                    
                    # Convert date string to datetime
                    date_time = self._parse_date(date_str)
                    
                    # Create unique combination key
                    combination_key = f"{token_sym}_{date_time.isoformat()}"
                    
                    # Skip if we've already seen this combination
                    if combination_key in seen_combinations:
                        print(f"Skipping duplicate record: {combination_key}")
                        continue
                    
                    seen_combinations.add(combination_key)
                    
                    # Extract trading signals fields
                    trading_signal = signal.get('TRADING_SIGNAL')
                    token_trend = signal.get('TOKEN_TREND')
                    trading_signals_returns = signal.get('TRADING_SIGNALS_RETURNS')
                    holding_returns = signal.get('HOLDING_RETURNS')
                    tm_link = signal.get('tm_link') or signal.get('TM_LINK')
                    tm_trader_grade = signal.get('TM_TRADER_GRADE')
                    tm_investor_grade = signal.get('TM_INVESTOR_GRADE')
                    
                    # Prepare record
                    record = {
                        'user_id': USER_ID,
                        'token_id': token_id,
                        'token_name': token_name,
                        'token_symbol': token_sym,
                        'date_time': date_time.isoformat(),
                        'trading_signal': int(trading_signal) if trading_signal is not None else None,
                        'token_trend': int(token_trend) if token_trend is not None else None,
                        'trading_signals_returns': float(trading_signals_returns) if trading_signals_returns is not None else None,
                        'holding_returns': float(holding_returns) if holding_returns is not None else None,
                        'tm_link': tm_link,
                        'tm_trader_grade': float(tm_trader_grade) if tm_trader_grade is not None else None,
                        'tm_investor_grade': float(tm_investor_grade) if tm_investor_grade is not None else None
                    }
                    
                    # Debug: Print the first record structure
                    if i == 0:
                        print(f"Sample record structure: {record}")
                    
                    db_data.append(record)
                    
                except Exception as e:
                    print(f"Error processing signal {i}: {e}")
                    print(f"Signal data: {signal}")
                    continue
            
            if not db_data:
                print("No valid data to store")
                return False
            
            print(f"Attempting to store {len(db_data)} unique records...")
            
            # Insert data with conflict resolution (upsert)
            result = self.supabase.table('trading_signals').upsert(
                db_data,
                on_conflict='token_symbol,date_time'  # Use simpler conflict key
            ).execute()
            
            print(f"✅ Successfully stored {len(db_data)} trading signals records")
            return True
            
        except Exception as e:
            print(f"❌ Error storing trading signals data: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_trading_signals(self, token_symbol: str, limit: int = 30) -> List[Dict]:
        """Retrieve trading signals data from Supabase"""
        try:
            result = self.supabase.table('trading_signals')\
                .select('*')\
                .eq('token_symbol', token_symbol.upper())\
                .order('date_time', desc=True)\
                .limit(limit)\
                .execute()
            
            if result.data:
                print(f"✅ Retrieved {len(result.data)} trading signals records for {token_symbol.upper()}")
                return result.data
            else:
                print(f"ℹ️ No trading signals data found for {token_symbol.upper()}")
                return []
                
        except Exception as e:
            print(f"❌ Error retrieving trading signals data for {token_symbol}: {e}")
            return []
