import pandas as pd
from datetime import datetime
import requests

def get_current_month_date():
    """
    Get current month and date in M/D format (e.g., 9/1 for September 1st)
    """
    now = datetime.now()
    return f"{now.month}/{now.day}"

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
        
        # Dynamic target date based on current month and date
        target_date = get_current_month_date()
        print(f"Looking for column: '{target_date}'")
        
        # Check if the target column exists
        if target_date in df.columns:
            print(f"\nFound target column: {target_date}")
            
            # Get all tokens from the target date column (skip NaN values)
            tokens = df[target_date].dropna().tolist()
            tokens = [str(token).strip() for token in tokens if str(token).strip()]
            
            print(f"Found {len(tokens)} tokens in {target_date} column")
            print(f"Tokens: {', '.join(tokens)}")
            
            return tokens
        else:
            print(f"Column '{target_date}' not found!")
            print("Available columns:", df.columns.tolist())
            
            # Try to find the most recent date column
            date_columns = [col for col in df.columns if '/' in str(col)]
            if date_columns:
                # Sort by month/day (convert to datetime for proper sorting)
                def parse_date(col):
                    try:
                        if '/' in str(col):
                            month, day = str(col).split('/')
                            return int(month), int(day)
                        return 0, 0
                    except:
                        return 0, 0
                
                sorted_columns = sorted(date_columns, key=parse_date, reverse=True)
                latest_column = sorted_columns[0]
                print(f"\nLatest available date column: {latest_column}")
                
                # Use the latest available column
                tokens = df[latest_column].dropna().tolist()
                tokens = [str(token).strip() for token in tokens if str(token).strip()]
                
                print(f"Using {latest_column} column instead")
                print(f"Found {len(tokens)} tokens in {latest_column} column")
                print(f"Tokens: {', '.join(tokens)}")
                
                return tokens
            else:
                print("No date columns found!")
                return []
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def main():
    """
    Main function to fetch tokens for current date.
    """
    current_date = get_current_month_date()
    
    print("="*60)
    print(f"FETCHING TOKENS FROM {current_date} COLUMN")
    print("="*60)
    
    # Fetch tokens for current date
    tokens = fetch_tokens_from_public_sheet()
    
    if tokens:
        print("\n" + "="*50)
        print(f"ALL TOKENS FOUND ({len(tokens)} total):")
        print("="*50)
        for i, token in enumerate(tokens, 1):
            print(f"{i:2d}. {token}")
    else:
        print(f"\nNo tokens found.")
    
    print("\n" + "="*60)
    print("Script completed!")

if __name__ == "__main__":
    main()