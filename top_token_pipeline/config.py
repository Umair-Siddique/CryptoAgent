"""
Configuration file for the Top Token Pipeline
"""

# Google Sheets Configuration
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1BBu8h0joeIyPJuyIqK3anFAoomT2oSQkAfU92qVKYzo/edit?usp=sharing"
TARGET_DATE_COLUMN = "8/26"

# API Configuration
TOKEN_METRICS_BASE_URL = "https://api.tokenmetrics.com"
BATCH_SIZE_TOKEN_LOOKUP = 3  # Process 3 tokens at a time for token ID lookup
BATCH_SIZE_TM_GRADE = 4      # Process 4 tokens at a time for TM grade lookup

# Rate Limiting
REQUEST_DELAY = 1.0  # Delay between API calls in seconds

# Output Configuration
OUTPUT_FILE = "top_10_tokens_results.json"
LOG_LEVEL = "INFO"

# Error Handling
MAX_RETRIES = 3
RETRY_DELAY = 2.0
