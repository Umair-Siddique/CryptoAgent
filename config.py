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
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    TOKEN_METRICS_API_KEY=os.getenv('TOKEN_METRICS_API')
    
    # Add rate limiting configuration
    API_RATE_LIMITS = {
        'ai_report': {
            'requests_per_minute': 10,
            'delay_between_requests': 6.0  # seconds
        },
        'fundamental_grade': {
            'requests_per_minute': 10,
            'delay_between_requests': 6.0  # seconds
        },
        'social_sentiment': {
            'requests_per_minute': 30,
            'delay_between_requests': 2.0  # seconds
        },
        'ohlcv': {
            'requests_per_minute': 60,
            'delay_between_requests': 1.0  # seconds
        }
    }
    
    @classmethod
    def validate(cls):
        """Validate that all required environment variables are set"""
        required_vars = [
            'SUPABASE_URL',
            'SUPABASE_KEY', 
            'USER_ID',
            'X402_PRIVATE_KEY_B64',
            'LUNAR_CRUSH_API',
            'OPENAI_API_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True