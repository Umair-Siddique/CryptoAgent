-- Create new_positions table for storing LLM trading recommendations
CREATE TABLE IF NOT EXISTS new_positions (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    entry_price DECIMAL(20, 8) NOT NULL,
    size_usd DECIMAL(10, 2) NOT NULL,
    stop_loss DECIMAL(20, 8) NOT NULL,
    target_1 DECIMAL(20, 8) NOT NULL,
    target_2 DECIMAL(20, 8) NOT NULL,
    rationale TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'closed', 'cancelled')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Add unique constraint to prevent duplicate entries for same symbol at same time
    CONSTRAINT unique_symbol_created UNIQUE (symbol, created_at)
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_new_positions_symbol ON new_positions(symbol);
CREATE INDEX IF NOT EXISTS idx_new_positions_status ON new_positions(status);
CREATE INDEX IF NOT EXISTS idx_new_positions_created_at ON new_positions(created_at);
CREATE INDEX IF NOT EXISTS idx_new_positions_symbol_status ON new_positions(symbol, status);

-- Create GIN index for text search on rationale
CREATE INDEX IF NOT EXISTS idx_new_positions_rationale ON new_positions USING GIN (to_tsvector('english', rationale));

-- Add comments for documentation
COMMENT ON TABLE new_positions IS 'Stores LLM-generated trading recommendations for new positions';
COMMENT ON COLUMN new_positions.symbol IS 'Token symbol (e.g., BTC, ETH)';
COMMENT ON COLUMN new_positions.entry_price IS 'Recommended entry price for the position';
COMMENT ON COLUMN new_positions.size_usd IS 'Position size in USD';
COMMENT ON COLUMN new_positions.stop_loss IS 'Stop loss price for the position';
COMMENT ON COLUMN new_positions.target_1 IS 'First profit target price';
COMMENT ON COLUMN new_positions.target_2 IS 'Second profit target price';
COMMENT ON COLUMN new_positions.rationale IS 'Detailed rationale for the trading recommendation';
COMMENT ON COLUMN new_positions.status IS 'Position status: active, closed, or cancelled';
COMMENT ON COLUMN new_positions.created_at IS 'Timestamp when this recommendation was created';
COMMENT ON COLUMN new_positions.updated_at IS 'Timestamp when this record was last updated';

-- Create trigger to automatically update updated_at column
CREATE OR REPLACE FUNCTION update_new_positions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_new_positions_updated_at 
    BEFORE UPDATE ON new_positions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_new_positions_updated_at();

-- Insert sample data for testing (optional)
-- INSERT INTO new_positions (symbol, entry_price, size_usd, stop_loss, target_1, target_2, rationale) VALUES
-- ('BTC', 45000.00, 25.00, 40000.00, 50000.00, 55000.00, 'Sample Bitcoin position based on strong fundamentals and technical analysis');
