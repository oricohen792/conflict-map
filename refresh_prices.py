import json
import requests
import os
import time
from datetime import datetime, timezone

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
    start_time = time.time()

    # Fetch updated data from API using IDs
    # Note: API seems to limit response size, so fetch individually or in very small batches
    updated_data = {}
    success = True
    error_msg = None
    
    # Fetch markets individually to ensure we get all of them
    print(f"  Fetching {len(market_ids)} markets from API...")
    for idx, market_id in enumerate(market_ids):
        if (idx + 1) % 20 == 0:
            print(f"  Progress: {idx + 1}/{len(market_ids)} markets fetched...")
        
        try:
            url = f"https://gamma-api.polymarket.com/markets?id={market_id}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            api_response = resp.json()
            
            if api_response:
                m = api_response[0]
                market_id_str = str(m.get("id") or m.get("_id", ""))
                if market_id_str:
                    updated_data[str(market_id)] = m
                    updated_data[market_id_str] = m
        except Exception as e:
            # Don't fail completely if one market fails
            print(f"  Warning: Failed to fetch market {market_id}: {e}")
            error_msg = f"Some markets failed to fetch: {str(e)}"
    
    print(f"  Total markets fetched from API: {len(updated_data)}")

    # Update manifest with new prices and track changes
    updated_manifest = []
    # Use UTC for all timestamps to ensure consistency across timezones
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    price_changes = []  # Track markets with price changes
    markets_updated = 0
    markets_no_change = 0
    markets_not_found = 0
    missing_market_ids = []  # Track which markets weren't found
    
    for entry in manifest:
        m_id = entry.get("id")
        # Normalize ID to string for lookup
        m_id_str = str(m_id) if m_id else None
        old_price = entry.get("price", 0)
        
        # Try both string and original format
        market_data = updated_data.get(m_id_str) or updated_data.get(m_id)
        
        if market_data:
            latest = market_data
            # Try different possible field names for price
            new_price = float(
                latest.get("lastTradePrice") or 
                latest.get("price") or 
                latest.get("lastPrice") or
                entry["price"] or 0
            )
            old_vol = entry.get("vol", 0)
            new_vol = float(latest.get("volume") or latest.get("vol") or entry["vol"] or 0)
            
            # Track price changes (lower threshold to catch any changes)
            price_diff = abs(new_price - old_price)
            if price_diff > 0.0001:  # Consider changes > 0.01% significant (0.0001 = 0.01%)
                price_changes.append({
                    "id": m_id,
                    "question": entry.get("q", "Unknown"),
                    "old_price": old_price,
                    "new_price": new_price,
                    "change": new_price - old_price,
                    "change_pct": ((new_price - old_price) / old_price * 100) if old_price > 0 else 0,
                    "vol_change": new_vol - old_vol
                })
                markets_updated += 1
            else:
                markets_no_change += 1
            
            entry["price"] = new_price
            entry["vol"] = new_vol
            # Update timestamp for this market (full date-time)
            entry["updated"] = current_time
        else:
            markets_not_found += 1
            missing_market_ids.append({"id": m_id, "question": entry.get("q", "Unknown")[:50]})
            # Keep old price if market not found in API response
        updated_manifest.append(entry)

    # Save updated manifest
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(updated_manifest, f, indent=2)

    # Update the last_update_timestamp file BEFORE generating HTML
    # This ensures the HTML shows the correct timestamp
    with open(".last_update_timestamp", "w", encoding="utf-8") as f:
        f.write(current_time)

    # Regenerate HTML (this will now read the updated timestamp)
    import cluster_markets
    html_content = cluster_markets.generate_map_html(updated_manifest)
    with open("market_report.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # Report results
    elapsed_time = time.time() - start_time
    print(f"\n=== Price Refresh Results ===")
    print(f"Total markets processed: {len(market_ids)}")
    print(f"Markets with price changes: {markets_updated}")
    print(f"Markets with no price change: {markets_no_change}")
    print(f"Markets not found in API: {markets_not_found}")
    print(f"Time elapsed: {elapsed_time:.2f} seconds")
    
    if missing_market_ids and len(missing_market_ids) <= 10:
        print(f"\n=== Markets Not Found in API (showing first 10) ===")
        for missing in missing_market_ids[:10]:
            print(f"  ID {missing['id']}: {missing['question']}")
    elif missing_market_ids:
        print(f"\n[INFO] {len(missing_market_ids)} markets not found in API (may be closed/expired)")
    
    if price_changes:
        print(f"\n=== Top 10 Price Changes ===")
        # Sort by absolute change percentage
        sorted_changes = sorted(price_changes, key=lambda x: abs(x["change_pct"]), reverse=True)
        for i, change in enumerate(sorted_changes[:10], 1):
            direction = "+" if change["change"] > 0 else "-"
            print(f"{i}. {change['question'][:60]}")
            print(f"   Price: {change['old_price']:.3f} -> {change['new_price']:.3f} ({direction}{abs(change['change']):.3f}, {change['change_pct']:+.2f}%)")
            print(f"   Volume change: {change['vol_change']:+,.0f}")
    else:
        print("\n[WARNING] No significant price changes detected (all prices within 0.1% of previous values)")
    
    if success:
        print(f"\n[DONE] Refreshed prices and updated market_report.html")
    else:
        print(f"\n[DONE] Refreshed prices and updated market_report.html (Error: {error_msg})")

if __name__ == "__main__":
    refresh_prices()
