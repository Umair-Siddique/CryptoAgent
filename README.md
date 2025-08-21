# Crypto Data Pipeline

A simplified pipeline that processes 3 dummy tokens (BTC, ETH, ADA) by:
1. Storing token metadata in Supabase
2. Fetching social posts using LunarCrush API
3. Fetching hourly and daily OHLCV data in parallel
4. Storing all data in Supabase

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables** in `.env`:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   USER_ID=your_user_id
   X402_PRIVATE_KEY_B64=your_x402_private_key
   LUNAR_CRUSH_API=your_lunar_crush_api_key
   ```

3. **Create database tables** in Supabase using `database_schema.sql`

## Usage

Run the pipeline:
```bash
python run_pipeline.py
```

## What it does

The pipeline processes 3 dummy tokens (BTC, ETH, ADA):

1. **Token Metadata**: Stores basic token information (price, market cap, etc.)
2. **Social Posts**: Fetches and stores social sentiment data from LunarCrush
3. **OHLCV Data**: Fetches and stores hourly and daily price data in parallel

## File Structure

```
├── run_pipeline.py          # Main pipeline script
├── config.py               # Configuration settings
├── database_schema.sql     # Database table definitions
├── requirements.txt        # Python dependencies
├── apis/
│   ├── token_metrics.py    # Token Metrics API client
│   ├── social_sentiment.py # LunarCrush API client
│   └── ohlcv_storage.py    # OHLCV data storage
└── README.md              # This file
```

## Database Tables

- `tokens`: Token metadata
- `social_posts`: Social sentiment data
- `hourly_ohlcv`: Hourly price data
- `daily_ohlcv`: Daily price data
