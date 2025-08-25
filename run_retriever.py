#!/usr/bin/env python3
"""
Run Comprehensive Token Analysis
This script runs the semantic retriever to find the most investable coin
and displays comprehensive analysis.
"""

import asyncio
from retriever import TokenRetriever

async def main():
    """Main function to run the comprehensive token analysis"""
    try:
        print("🎯 Starting Most Investable Token Analysis")
        print("=" * 60)
        
        # Initialize and run the retriever
        retriever = TokenRetriever()
        success = await retriever.run_comprehensive_analysis()
        
        if success:
            print("\n✅ Analysis completed successfully!")
        else:
            print("\n⚠️ Analysis completed with some issues")
            
    except Exception as e:
        print(f"❌ Failed to run token analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
