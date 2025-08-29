#!/usr/bin/env python3
"""
Enhanced runner script for the Top Token Pipeline - runs enhanced ranking automatically
"""

import asyncio
import sys
import os
import glob

# Add the parent directory to the path to import APIs
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from token_pipeline import TopTokenPipeline

def cleanup_old_files():
    """Remove old result files to avoid confusion"""
    old_files = [
        "top_10_tokens_results.json",  # Old simple pipeline output
        "top_10_tokens_simple_tm_grade_results.json",  # Old simple method output
        "top_10_tokens_enhanced_composite_results.json",  # Old enhanced method output
        "all_tokens_data.json"  # Old all tokens data file
    ]
    
    for old_file in old_files:
        if os.path.exists(old_file):
            try:
                os.remove(old_file)
                print(f"️  Removed old file: {old_file}")
            except Exception as e:
                print(f"⚠️  Could not remove {old_file}: {e}")

async def main():
    """Run the pipeline with LLM-based token selection automatically"""
    try:
        print(" Enhanced Top Token Pipeline - Running LLM Selection")
        print("=" * 60)
        print("✅ Processing ALL tokens and using LLM for top 10 selection")
        print("✅ No file generation - results displayed in terminal only")
        print("✅ LLM integration ready for token ranking")
        
        # Clean up old files first
        cleanup_old_files()
        
        pipeline = TopTokenPipeline()
        
        # Run with LLM selection automatically (no user input needed)
        await pipeline.run_pipeline(use_llm_selection=True)
        
        print("\n" + "=" * 60)
        print(" Pipeline completed successfully!")
        print("📋 Top 10 tokens displayed in terminal above")
        print("💡 To integrate LLM: update the get_llm_top_10_selection method")
        
    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
