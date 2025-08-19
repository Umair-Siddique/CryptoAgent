import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Supabase Configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    USER_ID = os.getenv('USER_ID')
    
    # Token Metrics API Configuration
    X402_PRIVATE_KEY_B64 = os.getenv('X402_PRIVATE_KEY_B64')
    
    # LunarCrush API Configuration
    LUNAR_CRUSH_API = os.getenv('LUNAR_CRUSH_API')
    
    # Processing Configuration
    TOP_TOKENS_LIMIT = int(os.getenv('TOP_TOKENS_LIMIT', '3')) 
    OHLCV_HOURS = int(os.getenv('OHLCV_HOURS', '24'))
    
    # Token Filtering Configuration
    TOKEN_CATEGORY = os.getenv('TOKEN_CATEGORY', 'altcoin,defi')  # Default to altcoins and DeFi
    TOKEN_EXCHANGE = os.getenv('TOKEN_EXCHANGE', 'binance,coinbase,gate')  # Default to major exchanges
    
    # API Timeouts
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '120'))
    CONNECT_TIMEOUT = int(os.getenv('CONNECT_TIMEOUT', '20'))
    
    @classmethod
    def validate(cls):
        """Validate that all required environment variables are set"""
        required_vars = [
            'SUPABASE_URL',
            'SUPABASE_KEY', 
            'USER_ID',
            'X402_PRIVATE_KEY_B64',
            'LUNAR_CRUSH_API'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True