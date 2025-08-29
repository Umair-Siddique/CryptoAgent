import pandas as pd
from datetime import datetime
import requests

def fetch_tokens_from_public_sheet():
    """
    Fetch tokens from public Google Sheet using pandas.
    """
    # Google Sheets URL (convert to CSV export format)
    sheet_url = "https://docs.google.com/spreadsheets/d/1BBu8h0joeIyPJuyIqK3anFAoomT2oSQkAfU92qVKYzo/edit?usp=sharing"
    
    # Convert to CSV export URL
    csv_url = sheet_url.replace('/edit?usp=sharing', '/export?format=csv&gid=0')
    
    try:
        # Fetch data from the CSV export
        print("Fetching data from Google Sheets...")
        df = pd.read_csv(csv_url)
        
        print(f"Successfully loaded data with {len(df)} rows and {len(df.columns)} columns")
        print(f"Columns: {list(df.columns)}")
        
        # Directly target the 8/26 column
        target_date = "8/26"
        
        if target_date in df.columns:
            print(f"\nFound target column: {target_date}")
            
            # Get all tokens from the 8/26 column (skip NaN values)
            tokens = df[target_date].dropna().tolist()
            tokens = [str(token).strip() for token in tokens if str(token).strip()]
            
            print(f"Found {len(tokens)} tokens in {target_date} column")
            print(f"Tokens: {', '.join(tokens)}")
            
            return tokens
        else:
            print(f"Column {target_date} not found!")
            print("Available columns:", df.columns.tolist())
            return []
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def main():
    """
    Main function to fetch tokens for 8/26.
    """
    print("="*60)
    print("FETCHING TOKENS FROM 8/26 COLUMN")
    print("="*60)
    
    # Fetch tokens for 8/26
    tokens = fetch_tokens_from_public_sheet()
    
    if tokens:
        print("\n" + "="*50)
        print(f"ALL TOKENS FROM 8/26 COLUMN ({len(tokens)} total):")
        print("="*50)
        for i, token in enumerate(tokens, 1):
            print(f"{i:2d}. {token}")
    else:
        print("\nNo tokens found in 8/26 column.")
    
    print("\n" + "="*60)
    print("Script completed!")

if __name__ == "__main__":
    main()