-- Create resistance_support table for storing historical resistance and support levels
CREATE TABLE IF NOT EXISTS resistance_support (
    id BIGSERIAL PRIMARY KEY,
    token_symbol VARCHAR(20) NOT NULL,
    token_id INTEGER,
    token_name VARCHAR(100),
    date TIMESTAMP WITH TIME ZONE,
    historical_levels JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Add unique constraint to prevent duplicate entries for same token and date
    CONSTRAINT unique_token_date UNIQUE (token_symbol, date)
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_resistance_support_token_symbol ON resistance_support(token_symbol);
CREATE INDEX IF NOT EXISTS idx_resistance_support_token_id ON resistance_support(token_id);
CREATE INDEX IF NOT EXISTS idx_resistance_support_date ON resistance_support(date);
CREATE INDEX IF NOT EXISTS idx_resistance_support_created_at ON resistance_support(created_at);

-- Create GIN index for JSONB queries on historical_levels
CREATE INDEX IF NOT EXISTS idx_resistance_support_historical_levels ON resistance_support USING GIN (historical_levels);

-- Add comments for documentation
COMMENT ON TABLE resistance_support IS 'Stores historical resistance and support levels for cryptocurrency tokens';
COMMENT ON COLUMN resistance_support.token_symbol IS 'Token symbol (e.g., BTC, ETH)';
COMMENT ON COLUMN resistance_support.token_id IS 'TokenMetrics API token ID';
COMMENT ON COLUMN resistance_support.token_name IS 'Full token name (e.g., Bitcoin, Ethereum)';
COMMENT ON COLUMN resistance_support.date IS 'Date when the resistance/support data was calculated';
COMMENT ON COLUMN resistance_support.historical_levels IS 'JSON array of historical resistance and support levels with dates and prices';
COMMENT ON COLUMN resistance_support.created_at IS 'Timestamp when this record was created';
COMMENT ON COLUMN resistance_support.updated_at IS 'Timestamp when this record was last updated';

-- Create trigger to automatically update updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_resistance_support_updated_at 
    BEFORE UPDATE ON resistance_support 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for testing (optional)
-- INSERT INTO resistance_support (token_symbol, token_id, token_name, date, historical_levels) VALUES
-- ('BTC', 3375, 'Bitcoin', '2025-01-27T00:00:00Z', '[
--     {"date": "2017-11-05", "level": 7630},
--     {"date": "2017-12-10", "level": 12368},
--     {"date": "2021-01-29", "level": 38710.69632264}
-- ]');
