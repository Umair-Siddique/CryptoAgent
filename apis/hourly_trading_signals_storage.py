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

class HourlyTradingSignalsStorage:
    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Missing Supabase credentials")
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string with multiple format support"""
        if not timestamp_str:
            return datetime.now(timezone.utc)
        
        # Try different timestamp formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',  # 2025-03-20T02:00:00.000Z
            '%Y-%m-%dT%H:%M:%SZ',     # 2025-03-20T02:00:00Z
            '%Y-%m-%dT%H:%M:%S',      # 2025-03-20T02:00:00
            '%Y-%m-%d',               # 2025-03-20
        ]
        
        for fmt in formats:
            try:
                if fmt.endswith('Z'):
                    dt = datetime.strptime(timestamp_str, fmt)
                    return dt.replace(tzinfo=timezone.utc)
                else:
                    dt = datetime.strptime(timestamp_str, fmt)
                    return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        
        # If all formats fail, try isoformat
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            print(f"Warning: Could not parse timestamp '{timestamp_str}', using current time")
            return datetime.now(timezone.utc)
    
    def store_hourly_trading_signals(self, hourly_signals_data: List[Dict]) -> bool:
        """Store hourly trading signals data in Supabase"""
        try:
            if not hourly_signals_data:
                print("No hourly trading signals data to store")
                return True
            
            print(f"Processing {len(hourly_signals_data)} hourly trading signals records")
            
            # Prepare data for insertion
            db_data = []
            seen_combinations = set()  # Track unique combinations
            
            for i, signal in enumerate(hourly_signals_data):
                try:
                    # Debug: Print the first record
                    if i == 0:
                        print(f"Sample hourly signal data: {signal}")
                    
                    # Extract fields from API response
                    timestamp_str = signal.get('TIMESTAMP')
                    token_id = signal.get('TOKEN_ID')
                    token_name = signal.get('TOKEN_NAME')
                    token_sym = signal.get('TOKEN_SYMBOL')
                    close_price = signal.get('CLOSE')
                    signal_value = signal.get('SIGNAL')
                    position = signal.get('POSITION')
                    
                    # Convert timestamp string to datetime
                    timestamp = self._parse_timestamp(timestamp_str)
                    
                    # Create unique combination key
                    combination_key = f"{token_sym}_{timestamp.isoformat()}"
                    
                    # Skip if we've already seen this combination
                    if combination_key in seen_combinations:
                        print(f"Skipping duplicate record: {combination_key}")
                        continue
                    
                    seen_combinations.add(combination_key)
                    
                    # Prepare record
                    record = {
                        'user_id': USER_ID,
                        'token_id': str(token_id) if token_id else None,
                        'token_name': token_name,
                        'token_symbol': token_sym,
                        'timestamp': timestamp.isoformat(),
                        'close_price': float(close_price) if close_price is not None else None,
                        'signal': str(signal_value) if signal_value is not None else None,
                        'position': str(position) if position is not None else None
                    }
                    
                    # Debug: Print the first record structure
                    if i == 0:
                        print(f"Sample record structure: {record}")
                    
                    db_data.append(record)
                    
                except Exception as e:
                    print(f"Error processing hourly signal {i}: {e}")
                    print(f"Signal data: {signal}")
                    continue
            
            if not db_data:
                print("No valid data to store")
                return False
            
            print(f"Attempting to store {len(db_data)} unique records...")
            
            # Insert data with conflict resolution (upsert)
            result = self.supabase.table('hourly_trading_signals').upsert(
                db_data,
                on_conflict='token_symbol,timestamp'  # Use unique constraint
            ).execute()
            
            print(f"✅ Successfully stored {len(db_data)} hourly trading signals records")
            return True
            
        except Exception as e:
            print(f"❌ Error storing hourly trading signals data: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_hourly_trading_signals(self, token_symbol: str, limit: int = 30) -> List[Dict]:
        """Retrieve hourly trading signals data from Supabase"""
        try:
            result = self.supabase.table('hourly_trading_signals')\
                .select('*')\
                .eq('token_symbol', token_symbol.upper())\
                .order('timestamp', desc=True)\
                .limit(limit)\
                .execute()
            
            if result.data:
                print(f"✅ Retrieved {len(result.data)} hourly trading signals records for {token_symbol.upper()}")
                return result.data
            else:
                print(f"ℹ️ No hourly trading signals data found for {token_symbol.upper()}")
                return []
                
        except Exception as e:
            print(f"❌ Error retrieving hourly trading signals data for {token_symbol}: {e}")
            return []
