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
CREATE TABLE IF NOT EXISTS posts (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    token VARCHAR(20),
    post_title TEXT,
    post_link VARCHAR(500) UNIQUE,
    post_sentiment DECIMAL(10, 4),
    creator_followers INTEGER,
    interactions_24h INTEGER,
    interactions_total INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_hourly_ohlcv_token_symbol ON hourly_ohlcv(token_symbol);
CREATE INDEX IF NOT EXISTS idx_hourly_ohlcv_date_time ON hourly_ohlcv(date_time);
CREATE INDEX IF NOT EXISTS idx_daily_ohlcv_token_symbol ON daily_ohlcv(token_symbol);
CREATE INDEX IF NOT EXISTS idx_daily_ohlcv_date_time ON daily_ohlcv(date_time);
CREATE INDEX IF NOT EXISTS idx_trading_signals_token_symbol ON trading_signals(token_symbol);
CREATE INDEX IF NOT EXISTS idx_trading_signals_date_time ON trading_signals(date_time);
CREATE INDEX IF NOT EXISTS idx_posts_token ON posts(token);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);
