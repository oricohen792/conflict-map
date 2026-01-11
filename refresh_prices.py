import json
import requests
import os
from datetime import datetime

def refresh_prices():
    manifest_file = "conflict_manifest.json"
    if not os.path.exists(manifest_file):
        print("Error: conflict_manifest.json not found. Run cluster_markets.py first.")
        return

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    if not manifest:
        print("No markets in manifest.")
        return

    # Extract IDs
    market_ids = [m["id"] for m in manifest if m["id"]]
    
    print(f"Refreshing prices for {len(market_ids)} markets...")

    # Fetch updated data from API using IDs
    chunk_size = 50
    updated_data = {}
    
    for i in range(0, len(market_ids), chunk_size):
        chunk = market_ids[i:i + chunk_size]
        url = f"https://gamma-api.polymarket.com/markets?id={'&id='.join(chunk)}"
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            for m in resp.json():
                updated_data[m["id"]] = m
        except Exception as e:
            print(f"Error fetching batch: {e}")

    # Track Changes
    price_changes = []
    updated_manifest = []
    current_time = datetime.now().strftime("%H:%M")
    
    for entry in manifest:
        m_id = entry.get("id")
        if m_id in updated_data:
            latest = updated_data[m_id]
            new_price = float(latest.get("lastTradePrice", entry["price"]) or 0)
            
            # Change detection (>= 1% shift)
            diff = new_price - entry["price"]
            if abs(diff) >= 0.01: 
                symbol = "↑" if diff > 0 else "↓"
                price_changes.append({
                    "time": current_time,
                    "type": "CHG",
                    "q": entry["q"],
                    "change": f"{symbol} {abs(int(diff*100))}%"
                })
            
            entry["price"] = new_price
            entry["vol"] = float(latest.get("volume", entry["vol"]) or 0)
            # Update timestamp for this market
            entry["updated"] = current_time
        updated_manifest.append(entry)

    # Update Change Log
    if price_changes:
        change_log = []
        if os.path.exists("recent_changes.json"):
            with open("recent_changes.json", "r", encoding="utf-8") as f:
                change_log = json.load(f)
        
        change_log = (price_changes + change_log)[:20]
        with open("recent_changes.json", "w", encoding="utf-8") as f:
            json.dump(change_log, f, indent=2)

    # Save updated manifest
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(updated_manifest, f, indent=2)

    # Regenerate HTML
    import cluster_markets
    html_content = cluster_markets.generate_map_html(updated_manifest)
    with open("market_report.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("Done! Refreshed prices and updated market_report.html")

if __name__ == "__main__":
    refresh_prices()
