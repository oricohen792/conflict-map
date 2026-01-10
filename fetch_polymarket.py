import requests
import json
import time
import os

def fetch_active_markets():
    url = "https://gamma-api.polymarket.com/markets"
    filename = "active_markets.jsonl"
    
    # Clear existing file
    if os.path.exists(filename):
        os.remove(filename)
    
    # Pagination parameters
    params = {
        "active": "true",
        "closed": "false",
        "limit": 100,
        "offset": 0
    }
    
    print(f"Starting to fetch active markets. Saving to {filename}...")
    
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
            
            # Save batch to file immediately
            with open(filename, "a", encoding='utf-8') as f:
                for market in data:
                    f.write(json.dumps(market) + "\n")
                    question = market.get("question", "Unknown Question")
                    # optional: print minimal info to keep console clean, or detailed
                    # print(f"Fetched: {question}")
            
            total_fetched += batch_size
            print(f"Fetched and saved batch of {batch_size}. Total: {total_fetched}")
            
            # Update offset for next page
            params["offset"] += batch_size
            
            # Respect rate limits
            time.sleep(0.1)

    except Exception as e:
        print(f"Error occurred: {e}")
    
if __name__ == "__main__":
    fetch_active_markets()

