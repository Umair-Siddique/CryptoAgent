-- Create hourly_ohlcv table
CREATE TABLE IF NOT EXISTS hourly_ohlcv (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    token_id VARCHAR(50),
    token_name VARCHAR(100),
    token_symbol VARCHAR(20) NOT NULL,
    date_time TIMESTAMPTZ NOT NULL,
    open_price DECIMAL(20, 8),
    high_price DECIMAL(20, 8),
    low_price DECIMAL(20, 8),
    close_price DECIMAL(20, 8),
    volume DECIMAL(30, 8),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(token_symbol, date_time)
);

-- Create daily_ohlcv table
CREATE TABLE IF NOT EXISTS daily_ohlcv (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    token_id VARCHAR(50),
    token_name VARCHAR(100),
    token_symbol VARCHAR(20) NOT NULL,
    date_time TIMESTAMPTZ NOT NULL,
    open_price DECIMAL(20, 8),
    high_price DECIMAL(20, 8),
    low_price DECIMAL(20, 8),
    close_price DECIMAL(20, 8),
    volume DECIMAL(30, 8),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(token_symbol, date_time)
);

-- Create trading_signals table
CREATE TABLE IF NOT EXISTS trading_signals (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    token_id VARCHAR(50),
    token_name VARCHAR(100),
    token_symbol VARCHAR(20) NOT NULL,
    date_time TIMESTAMPTZ NOT NULL,
    trading_signal INTEGER,
    token_trend INTEGER,
    trading_signals_returns DECIMAL(20, 8),
    holding_returns DECIMAL(20, 8),
    tm_link VARCHAR(255),
    tm_trader_grade DECIMAL(10, 2),
    tm_investor_grade DECIMAL(10, 2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(token_symbol, date_time)
);

-- Create posts table for social sentiment data
create table public.posts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,

  -- renamed (avoid reserved word)
  ingested_at timestamptz not null default now(),

  token_name text,        -- CHANGE: Use token_name instead of token
  post_title text not null,
  post_link text,
  post_sentiment double precision,
  creator_followers bigint,
  interactions_24h bigint,
  interactions_total bigint
);

-- Create ai_reports table
CREATE TABLE IF NOT EXISTS ai_reports (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    token_id VARCHAR(50),
    token_name VARCHAR(100),
    token_symbol VARCHAR(20) NOT NULL,
    investment_analysis_pointer TEXT,
    investment_analysis TEXT,
    deep_dive TEXT,
    code_review TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(token_symbol, token_id)
);

-- Create fundamental_grade table
CREATE TABLE IF NOT EXISTS fundamental_grade (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    token_id VARCHAR(50),
    token_name VARCHAR(100),
    token_symbol VARCHAR(20) NOT NULL,
    fundamental_grade DECIMAL(10, 2),
    fundamental_grade_class VARCHAR(50),
    community_score DECIMAL(10, 8),
    exchange_score DECIMAL(10, 2),
    vc_score DECIMAL(10, 2),
    tokenomics_score DECIMAL(10, 2),
    defi_scanner_score DECIMAL(10, 2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(token_symbol)
);


CREATE TABLE IF NOT EXISTS embeddings (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    content_id UUID NOT NULL,  -- CHANGE: Use UUID instead of BIGINT
    token_name VARCHAR(100),   -- CHANGE: Use token_name instead of token_symbol
    content_text TEXT NOT NULL,
    embedding_vector vector(1536),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_type, content_id)
);
-- Change the embeddings table to allow both integer and UUID content_ids
ALTER TABLE embeddings ALTER COLUMN content_id TYPE TEXT;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_embeddings_content_type ON embeddings(content_type);
CREATE INDEX IF NOT EXISTS idx_embeddings_content_id ON embeddings(content_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_token_symbol ON embeddings(token_symbol);
CREATE INDEX IF NOT EXISTS idx_embeddings_created_at ON embeddings(created_at);

-- Use IVFFlat index with smaller dimensions
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings USING ivfflat (embedding_vector vector_cosine_ops) WITH (lists = 100);
-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_hourly_ohlcv_token_symbol ON hourly_ohlcv(token_symbol);
CREATE INDEX IF NOT EXISTS idx_hourly_ohlcv_date_time ON hourly_ohlcv(date_time);
CREATE INDEX IF NOT EXISTS idx_daily_ohlcv_token_symbol ON daily_ohlcv(token_symbol);
CREATE INDEX IF NOT EXISTS idx_daily_ohlcv_date_time ON daily_ohlcv(date_time);
CREATE INDEX IF NOT EXISTS idx_trading_signals_token_symbol ON trading_signals(token_symbol);
CREATE INDEX IF NOT EXISTS idx_trading_signals_date_time ON trading_signals(date_time);
create unique index if not exists posts_post_link_unique on public.posts (post_link);

-- helpful query indexes
create index if not exists posts_token_ingested_at_idx on public.posts (token, ingested_at desc);
create index if not exists posts_sentiment_idx on public.posts (post_sentiment);
create index if not exists posts_interactions_idx on public.posts (interactions_total desc, interactions_24h desc);

-- Create index for ai_reports table
CREATE INDEX IF NOT EXISTS idx_ai_reports_token_symbol ON ai_reports(token_symbol);
CREATE INDEX IF NOT EXISTS idx_ai_reports_token_id ON ai_reports(token_id);
CREATE INDEX IF NOT EXISTS idx_ai_reports_created_at ON ai_reports(created_at);

-- Create index for fundamental_grade table
CREATE INDEX IF NOT EXISTS idx_fundamental_grade_token_symbol ON fundamental_grade(token_symbol);
CREATE INDEX IF NOT EXISTS idx_fundamental_grade_created_at ON fundamental_grade(created_at);

-- Create hourly_trading_signals table
CREATE TABLE IF NOT EXISTS hourly_trading_signals (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    token_id VARCHAR(50),
    token_name VARCHAR(100),
    token_symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    close_price DECIMAL(20, 8),
    signal VARCHAR(10),
    position VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(token_symbol, timestamp)
);

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_hourly_trading_signals_token_symbol ON hourly_trading_signals(token_symbol);
CREATE INDEX IF NOT EXISTS idx_hourly_trading_signals_timestamp ON hourly_trading_signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_hourly_trading_signals_created_at ON hourly_trading_signals(created_at);

-- Update the posts index to use token_name
create index if not exists posts_token_name_ingested_at_idx on public.posts (token_name, ingested_at desc);


