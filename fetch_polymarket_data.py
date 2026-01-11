#!/usr/bin/env python3
"""
Fetch Polymarket data and save to JSON file
"""
import json
import requests
import time
from datetime import datetime, timezone

DATA_FILE = "polymarket_data.json"

def fetch_markets():
    """Fetch all active markets from Polymarket API"""
    url = "https://gamma-api.polymarket.com/markets"
    markets = []
    
    params = {
        "active": "true",
        "closed": "false",
        "limit": 100,
        "offset": 0
    }
    
    print("Fetching markets from Polymarket API...")
    total_fetched = 0
    
    try:
        while True:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not isinstance(data, list):
                print(f"Unexpected response format: {type(data)}")
                break

            batch_size = len(data)
            if batch_size == 0:
                print("No more markets found.")
                break
            
            markets.extend(data)
            total_fetched += batch_size
            print(f"Fetched batch of {batch_size}. Total: {total_fetched}")
            
            params["offset"] += batch_size
            time.sleep(0.1)  # Rate limiting

    except Exception as e:
        print(f"Error occurred: {e}")
    
    print(f"Total markets fetched: {len(markets)}")
    return markets

def main():
    print("=" * 60)
    print("Polymarket Data Fetcher")
    print("=" * 60)
    print(f"Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
    
    # Fetch markets
    markets = fetch_markets()
    if not markets:
        print("Error: No markets fetched")
        return
    
    # Save to JSON file
    output_data = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_markets": len(markets),
        "markets": markets
    }
    
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nDone! Saved {len(markets)} markets to {DATA_FILE}")
    print(f"Completed at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")

if __name__ == "__main__":
    main()
