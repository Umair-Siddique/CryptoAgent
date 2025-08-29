import asyncio
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import requests
from dataclasses import dataclass

# Fix the import path - use relative imports properly
import sys
import os
from pathlib import Path

# Get the current file's directory
current_dir = Path(__file__).parent
# Get the parent directory (where apis folder is located)
parent_dir = current_dir.parent
# Add the apis directory to Python path
sys.path.insert(0, str(parent_dir / 'apis'))

try:
    from token_metrics import TokenMetricsAPI
    from tm_grade import TMGradeAPI
    print("✅ Successfully imported API modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Current directory: {current_dir}")
    print(f"Parent directory: {parent_dir}")
    print(f"APIs directory: {parent_dir / 'apis'}")
    print(f"Python path: {sys.path}")
    raise

@dataclass
class TokenData:
    """Data structure for token information"""
    name: str
    symbol: str
    token_id: Optional[int] = None
    tm_grade: Optional[str] = None
    tm_grade_24h_change: Optional[str] = None
    quant_grade: Optional[str] = None
    tm_grade_signal: Optional[str] = None
    momentum: Optional[str] = None
    composite_score: Optional[float] = None  # Added for enhanced ranking

class TopTokenPipeline:
    """
    Enhanced pipeline to process ALL tokens from Google Sheets through TokenMetrics API
    and rank by TM Grade to get top 10 tokens using multiple methods.
    """
    
    def __init__(self):
        """Initialize the pipeline with required APIs"""
        try:
            self.token_metrics_api = TokenMetricsAPI()
            self.tm_grade_api = TMGradeAPI()
            print("✅ APIs initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing APIs: {e}")
            raise
    
    def fetch_tokens_from_sheet(self) -> List[str]:
        """
        Fetch tokens from the public Google Sheet for 8/26
        """
        print("\n🔄 Step 1: Fetching tokens from Google Sheets...")
        
        sheet_url = "https://docs.google.com/spreadsheets/d/1BBu8h0joeIyPJuyIqK3anFAoomT2oSQkAfU92qVKYzo/edit?usp=sharing"
        csv_url = sheet_url.replace('/edit?usp=sharing', '/export?format=csv&gid=0')
        
        try:
            df = pd.read_csv(csv_url)
            print(f"✅ Successfully loaded data with {len(df)} rows and {len(df.columns)} columns")
            
            # Target the 8/26 column specifically
            target_date = "8/26"
            if target_date in df.columns:
                tokens = df[target_date].dropna().tolist()
                tokens = [str(token).strip() for token in tokens if str(token).strip()]
                print(f"✅ Found {len(tokens)} tokens in {target_date} column")
                return tokens
            else:
                print(f"❌ Column {target_date} not found!")
                print("Available columns:", df.columns.tolist())
                return []
                
        except Exception as e:
            print(f"❌ Error fetching data: {e}")
            return []
    
    async def get_token_ids(self, tokens: List[str]) -> List[TokenData]:
        """
        Get token IDs from TokenMetrics API by processing 3 tokens at a time
        """
        print(f"\n🔄 Step 2: Getting token IDs for {len(tokens)} tokens...")
        
        token_data_list = []
        batch_size = 3
        
        for i in range(0, len(tokens), batch_size):
            batch = tokens[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}: {batch}")
            
            try:
                # Create comma-separated string for API call
                token_names = ",".join(batch)
                
                # Make API call to get token IDs
                response = await self.token_metrics_api._make_paid_request(
                    f"/v2/tokens?token_name={token_names}"
                )
                
                if response and response.get("success"):
                    data = response.get("data", [])
                    print(f"✅ Got {len(data)} token IDs for batch")
                    
                    for token_info in data:
                        token_data = TokenData(
                            name=token_info.get("TOKEN_NAME", ""),
                            symbol=token_info.get("TOKEN_SYMBOL", ""),
                            token_id=token_info.get("TOKEN_ID")
                        )
                        token_data_list.append(token_data)
                        
                else:
                    print(f"❌ Failed to get token IDs for batch: {batch}")
                    # Add tokens without IDs for tracking
                    for token_name in batch:
                        token_data = TokenData(name=token_name, symbol="")
                        token_data_list.append(token_data)
                
                # Rate limiting - wait between batches
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Error processing batch {batch}: {e}")
                # Add tokens without IDs for tracking
                for token_name in batch:
                    token_data = TokenData(name=token_name, symbol="")
                    token_data_list.append(token_data)
        
        print(f"✅ Completed token ID lookup. Got {len([t for t in token_data_list if t.token_id])} IDs")
        return token_data_list
    
    async def get_tm_grades(self, token_data_list: List[TokenData]) -> List[TokenData]:
        """
        Get TM grades for tokens by processing 4 tokens at a time
        """
        print(f"\n Step 3: Getting TM grades for {len(token_data_list)} tokens...")
        
        # Filter tokens that have IDs
        tokens_with_ids = [t for t in token_data_list if t.token_id]
        print(f"Processing {len(tokens_with_ids)} tokens with valid IDs")
        
        batch_size = 4  # Process 4 tokens at a time for TM grade API
        
        for i in range(0, len(tokens_with_ids), batch_size):
            batch = tokens_with_ids[i:i + batch_size]
            print(f"Processing TM grade batch {i//batch_size + 1}: {[t.name for t in batch]}")
            
            try:
                # Create comma-separated string of token IDs
                token_ids = ",".join([str(t.token_id) for t in batch])
                
                # Make API call to get TM grades
                response = await self.tm_grade_api._make_paid_request(
                    f"/v2/tm-grade?token_id={token_ids}"
                )
                
                if response and response.get("success"):
                    data = response.get("data", [])
                    print(f"✅ Got TM grades for {len(data)} tokens")
                    
                    # Update token data with TM grade information
                    for grade_info in data:
                        token_id = grade_info.get("TOKEN_ID")
                        for token_data in token_data_list:
                            if token_data.token_id == token_id:
                                token_data.tm_grade = grade_info.get("TM_GRADE")
                                token_data.tm_grade_24h_change = grade_info.get("TM_GRADE_24h_PCT_CHANGE")
                                token_data.quant_grade = grade_info.get("QUANT_GRADE")
                                token_data.tm_grade_signal = grade_info.get("TM_GRADE_SIGNAL")
                                token_data.momentum = grade_info.get("MOMENTUM")
                                break
                else:
                    print(f"❌ Failed to get TM grades for batch: {[t.name for t in batch]}")
                
                # Rate limiting - wait between batches
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Error processing TM grade batch: {e}")
        
        print(f"✅ Completed TM grade lookup for {len(tokens_with_ids)} tokens")
        return token_data_list
    
    async def get_llm_top_10_selection(self, token_data_list: List[TokenData]) -> List[TokenData]:
        """
        Use LLM to select top 10 tokens from all available tokens with TM grade data
        """
        print(f"\n🤖 Step 4: Using LLM to select top 10 tokens from {len(token_data_list)} tokens...")
        
        # Filter tokens that have TM grades
        tokens_with_grades = [t for t in token_data_list if t.tm_grade and t.token_id]
        
        if not tokens_with_grades:
            print("❌ No tokens with TM grades found")
            return []
        
        print(f"Processing {len(tokens_with_grades)} tokens with complete data for LLM analysis")
        
        # Prepare data for LLM
        formatted_data = []
        for token in tokens_with_grades:
            formatted_data.append({
                "name": token.name,
                "symbol": token.symbol,
                "token_id": token.token_id,
                "tm_grade": token.tm_grade,
                "tm_grade_24h_change": token.tm_grade_24h_change,
                "tm_grade_signal": token.tm_grade_signal,
                "momentum": token.momentum,
                "quant_grade": token.quant_grade
            })
        
        # Create LLM prompt for top 10 selection
        llm_prompt = f"""
        Analyze these {len(formatted_data)} crypto tokens and select the TOP 10 for trading opportunities.

        CRITERIA TO CONSIDER:
        - TM Grade (0-100, higher is better) - Primary factor
        - 24h momentum trends (positive is better)
        - Trading signals (Strong Buy > Buy > Hold > Sell)
        - Market momentum (Gaining > Holding > Losing)
        - Quantitative grade (higher is better)

        TASK:
        Select exactly 10 tokens that represent the best trading opportunities, considering all factors above.

        TOKEN DATA:
        {json.dumps(formatted_data, indent=2)}

        Return ONLY a JSON response with this exact format:
        {{
            "top_10_tokens": [
                {{
                    "rank": 1,
                    "token_id": <token_id>,
                    "name": "<token_name>",
                    "symbol": "<token_symbol>",
                    "tm_grade": "<tm_grade>",
                    "tm_grade_24h_change": "<24h_change>",
                    "tm_grade_signal": "<signal>",
                    "momentum": "<momentum>",
                    "quant_grade": "<quant_grade>",
                    "reasoning": "<brief_reason_why_this_token_was_selected>"
                }},
                ... (repeat for all 10 tokens)
            ]
        }}

        IMPORTANT: Return ONLY the JSON, no other text or explanations.
        """
        
        print(f"✅ Prepared LLM prompt with {len(formatted_data)} tokens")
        print(" Sending to LLM for top 10 selection...")
        
        # TODO: Replace this with actual LLM API call
        # For now, we'll use a placeholder that simulates LLM response
        # In production, you would call OpenAI, Anthropic, or other LLM API here
        
        print("⚠️  LLM API integration needed - currently using placeholder selection")
        print("📋 LLM Prompt prepared and ready to use:")
        print("=" * 70)
        print(llm_prompt)
        print("=" * 70)
        
        # Placeholder: return top 10 by TM grade until LLM is integrated
        sorted_tokens = sorted(tokens_with_grades, key=lambda x: float(x.tm_grade), reverse=True)
        top_10 = sorted_tokens[:10]
        
        print(f"✅ LLM selection completed (placeholder)")
        print(f"Top TM Grade: {top_10[0].tm_grade} ({top_10[0].name})")
        print(f"Lowest TM Grade in top 10: {top_10[-1].tm_grade} ({top_10[-1].name})")
        
        return top_10

    async def run_pipeline(self, use_llm_selection: bool = True):
        """
        Run the complete pipeline with LLM-based token selection
        """
        print("🚀 Starting Enhanced Top Token Pipeline with LLM Selection...")
        print("=" * 70)
        
        start_time = time.time()
        
        try:
            # Step 1: Fetch tokens from Google Sheets
            tokens = self.fetch_tokens_from_sheet()
            if not tokens:
                print("❌ No tokens found, pipeline stopped")
                return
            
            print(f"📊 Total tokens to process: {len(tokens)}")
            
            # Step 2: Get token IDs
            token_data_list = await self.get_token_ids(tokens)
            
            # Step 3: Get TM grades
            token_data_list = await self.get_tm_grades(token_data_list)
            
            # Step 4: Use LLM to select top 10 tokens
            top_tokens = await self.get_llm_top_10_selection(token_data_list)
            
            # Display results in terminal only
            print("\n" + "=" * 70)
            print(" TOP 10 TOKENS SELECTED BY LLM")
            print("=" * 70)
            
            for i, token in enumerate(top_tokens, 1):
                print(f"{i:2d}. {token.name} ({token.symbol})")
                print(f"    Token ID: {token.token_id}")
                print(f"    TM Grade: {token.tm_grade}")
                print(f"    24h Change: {token.tm_grade_24h_change}")
                print(f"    Signal: {token.tm_grade_signal}")
                print(f"    Momentum: {token.momentum}")
                print()
            
            elapsed_time = time.time() - start_time
            print(f"\n⏱️  Pipeline completed in {elapsed_time:.2f} seconds")
            print("📋 Results displayed in terminal only - no files generated")
            
        except Exception as e:
            print(f"❌ Pipeline failed: {e}")
            raise

async def main():
    """Main function to run the pipeline"""
    pipeline = TopTokenPipeline()
    
    # Run pipeline with LLM selection
    await pipeline.run_pipeline(use_llm_selection=True)

if __name__ == "__main__":
    asyncio.run(main())
