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

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_hourly_ohlcv_token_symbol ON hourly_ohlcv(token_symbol);
CREATE INDEX IF NOT EXISTS idx_hourly_ohlcv_date_time ON hourly_ohlcv(date_time);
CREATE INDEX IF NOT EXISTS idx_daily_ohlcv_token_symbol ON daily_ohlcv(token_symbol);
CREATE INDEX IF NOT EXISTS idx_daily_ohlcv_date_time ON daily_ohlcv(date_time);
CREATE INDEX IF NOT EXISTS idx_trading_signals_token_symbol ON trading_signals(token_symbol);
CREATE INDEX IF NOT EXISTS idx_trading_signals_date_time ON trading_signals(date_time);
CREATE INDEX IF NOT EXISTS idx_posts_token ON posts(token);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);

-- Create index for ai_reports table
CREATE INDEX IF NOT EXISTS idx_ai_reports_token_symbol ON ai_reports(token_symbol);
CREATE INDEX IF NOT EXISTS idx_ai_reports_token_id ON ai_reports(token_id);
CREATE INDEX IF NOT EXISTS idx_ai_reports_created_at ON ai_reports(created_at);

-- Create index for fundamental_grade table
CREATE INDEX IF NOT EXISTS idx_fundamental_grade_token_symbol ON fundamental_grade(token_symbol);
CREATE INDEX IF NOT EXISTS idx_fundamental_grade_created_at ON fundamental_grade(created_at);
