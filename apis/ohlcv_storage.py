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

class OHLCVStorage:
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
    
    def store_hourly_ohlcv(self, token_symbol: str, ohlcv_data: List[Dict]) -> bool:
        """Store hourly OHLCV data in Supabase"""
        try:
            if not ohlcv_data:
                print(f"No hourly OHLCV data to store for {token_symbol}")
                return True
            
            print(f"Processing {len(ohlcv_data)} hourly OHLCV records for {token_symbol}")
            
            # Prepare data for insertion
            db_data = []
            seen_combinations = set()  # Track unique combinations
            
            for i, candle in enumerate(ohlcv_data):
                try:
                    # Debug: Print the first record
                    if i == 0:
                        print(f"Sample candle data: {candle}")
                    
                    # Handle different possible field names from API
                    # For hourly data, use TIMESTAMP field
                    date_str = candle.get('TIMESTAMP') or candle.get('DATE') or candle.get('date') or candle.get('timestamp')
                    token_id = candle.get('TOKEN_ID') or candle.get('token_id')
                    token_name = candle.get('TOKEN_NAME') or candle.get('token_name')
                    token_sym = candle.get('TOKEN_SYMBOL') or candle.get('token_symbol') or token_symbol.upper()
                    
                    # Convert date string to datetime
                    date_time = self._parse_date(date_str)
                    
                    # Create unique combination key
                    combination_key = f"{token_sym}_{date_time.isoformat()}"
                    
                    # Skip if we've already seen this combination
                    if combination_key in seen_combinations:
                        print(f"Skipping duplicate record: {combination_key}")
                        continue
                    
                    seen_combinations.add(combination_key)
                    
                    # Handle different price field names
                    open_price = candle.get('OPEN') or candle.get('open') or candle.get('open_price')
                    high_price = candle.get('HIGH') or candle.get('high') or candle.get('high_price')
                    low_price = candle.get('LOW') or candle.get('low') or candle.get('low_price')
                    close_price = candle.get('CLOSE') or candle.get('close') or candle.get('close_price')
                    volume = candle.get('VOLUME') or candle.get('volume')
                    
                    # Prepare record
                    record = {
                        'user_id': USER_ID,
                        'token_id': token_id,
                        'token_name': token_name,
                        'token_symbol': token_sym,
                        'date_time': date_time.isoformat(),
                        'open_price': float(open_price) if open_price is not None else None,
                        'high_price': float(high_price) if high_price is not None else None,
                        'low_price': float(low_price) if low_price is not None else None,
                        'close_price': float(close_price) if close_price is not None else None,
                        'volume': float(volume) if volume is not None else None
                    }
                    
                    # Debug: Print the first record structure
                    if i == 0:
                        print(f"Sample record structure: {record}")
                    
                    db_data.append(record)
                    
                except Exception as e:
                    print(f"Error processing candle {i}: {e}")
                    print(f"Candle data: {candle}")
                    continue
            
            if not db_data:
                print(f"No valid data to store for {token_symbol}")
                return False
            
            print(f"Attempting to store {len(db_data)} unique records...")
            
            # Insert data with conflict resolution (upsert)
            result = self.supabase.table('hourly_ohlcv').upsert(
                db_data,
                on_conflict='token_symbol,date_time'  # Use simpler conflict key
            ).execute()
            
            print(f"✅ Successfully stored {len(db_data)} hourly OHLCV records for {token_symbol.upper()}")
            return True
            
        except Exception as e:
            print(f"❌ Error storing hourly OHLCV data for {token_symbol}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def store_daily_ohlcv(self, token_symbol: str, ohlcv_data: List[Dict]) -> bool:
        """Store daily OHLCV data in Supabase"""
        try:
            if not ohlcv_data:
                print(f"No daily OHLCV data to store for {token_symbol}")
                return True
            
            print(f"Processing {len(ohlcv_data)} daily OHLCV records for {token_symbol}")
            
            # Prepare data for insertion
            db_data = []
            seen_combinations = set()  # Track unique combinations
            
            for i, candle in enumerate(ohlcv_data):
                try:
                    # Debug: Print the first record
                    if i == 0:
                        print(f"Sample candle data: {candle}")
                    
                    # Handle different possible field names from API
                    # For daily data, use DATE field
                    date_str = candle.get('DATE') or candle.get('TIMESTAMP') or candle.get('date') or candle.get('timestamp')
                    token_id = candle.get('TOKEN_ID') or candle.get('token_id')
                    token_name = candle.get('TOKEN_NAME') or candle.get('token_name')
                    token_sym = candle.get('TOKEN_SYMBOL') or candle.get('token_symbol') or token_symbol.upper()
                    
                    # Convert date string to datetime
                    date_time = self._parse_date(date_str)
                    
                    # Create unique combination key
                    combination_key = f"{token_sym}_{date_time.isoformat()}"
                    
                    # Skip if we've already seen this combination
                    if combination_key in seen_combinations:
                        print(f"Skipping duplicate record: {combination_key}")
                        continue
                    
                    seen_combinations.add(combination_key)
                    
                    # Handle different price field names
                    open_price = candle.get('OPEN') or candle.get('open') or candle.get('open_price')
                    high_price = candle.get('HIGH') or candle.get('high') or candle.get('high_price')
                    low_price = candle.get('LOW') or candle.get('low') or candle.get('low_price')
                    close_price = candle.get('CLOSE') or candle.get('close') or candle.get('close_price')
                    volume = candle.get('VOLUME') or candle.get('volume')
                    
                    # Prepare record
                    record = {
                        'user_id': USER_ID,
                        'token_id': token_id,
                        'token_name': token_name,
                        'token_symbol': token_sym,
                        'date_time': date_time.isoformat(),
                        'open_price': float(open_price) if open_price is not None else None,
                        'high_price': float(high_price) if high_price is not None else None,
                        'low_price': float(low_price) if low_price is not None else None,
                        'close_price': float(close_price) if close_price is not None else None,
                        'volume': float(volume) if volume is not None else None
                    }
                    
                    # Debug: Print the first record structure
                    if i == 0:
                        print(f"Sample record structure: {record}")
                    
                    db_data.append(record)
                    
                except Exception as e:
                    print(f"Error processing candle {i}: {e}")
                    print(f"Candle data: {candle}")
                    continue
            
            if not db_data:
                print(f"No valid data to store for {token_symbol}")
                return False
            
            print(f"Attempting to store {len(db_data)} unique records...")
            
            # Insert data with conflict resolution (upsert)
            result = self.supabase.table('daily_ohlcv').upsert(
                db_data,
                on_conflict='token_symbol,date_time'  # Use simpler conflict key
            ).execute()
            
            print(f"✅ Successfully stored {len(db_data)} daily OHLCV records for {token_symbol.upper()}")
            return True
            
        except Exception as e:
            print(f"❌ Error storing daily OHLCV data for {token_symbol}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_hourly_ohlcv(self, token_symbol: str, limit: int = 24) -> List[Dict]:
        """Retrieve hourly OHLCV data from Supabase"""
        try:
            result = self.supabase.table('hourly_ohlcv')\
                .select('*')\
                .eq('token_symbol', token_symbol.upper())\
                .order('date_time', desc=True)\
                .limit(limit)\
                .execute()
            
            if result.data:
                print(f"✅ Retrieved {len(result.data)} hourly OHLCV records for {token_symbol.upper()}")
                return result.data
            else:
                print(f"ℹ️ No hourly OHLCV data found for {token_symbol.upper()}")
                return []
                
        except Exception as e:
            print(f"❌ Error retrieving hourly OHLCV data for {token_symbol}: {e}")
            return []

    def get_daily_ohlcv(self, token_symbol: str, limit: int = 30) -> List[Dict]:
        """Retrieve daily OHLCV data from Supabase"""
        try:
            result = self.supabase.table('daily_ohlcv')\
                .select('*')\
                .eq('token_symbol', token_symbol.upper())\
                .order('date_time', desc=True)\
                .limit(limit)\
                .execute()
            
            if result.data:
                print(f"✅ Retrieved {len(result.data)} daily OHLCV records for {token_symbol.upper()}")
                return result.data
            else:
                print(f"ℹ️ No daily OHLCV data found for {token_symbol.upper()}")
                return []
                
        except Exception as e:
            print(f"❌ Error retrieving daily OHLCV data for {token_symbol}: {e}")
            return []
