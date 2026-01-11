#!/usr/bin/env python3
"""
Local test script to simulate the GitHub Actions workflow logic
"""
import os
import subprocess
from datetime import datetime, timezone

def check_update_type():
    """Simulate the workflow decision logic"""
    current_time = int(datetime.now(timezone.utc).timestamp())
    markets_verified_file = ".markets_verified_time"
    
    print("=== Checking if full update needed ===")
    
    if os.path.exists(markets_verified_file):
        with open(markets_verified_file, "r", encoding="utf-8") as f:
            verified_timestamp = f.read().strip()
        
        print(f"Found .markets_verified_time: {verified_timestamp}")
        
        try:
            dt = datetime.strptime(verified_timestamp, '%Y-%m-%d %H:%M:%S')
            dt = dt.replace(tzinfo=timezone.utc)
            verified_unix = int(dt.timestamp())
            
            if verified_unix > 0:
                time_since_verified = current_time - verified_unix
                minutes_since = time_since_verified // 60
                
                print(f"Time since last verification: {minutes_since} minutes ({time_since_verified} seconds)")
                
                if time_since_verified < 3600:
                    print("Decision: PRICE REFRESH (< 60 minutes)")
                    return "price"
                else:
                    print("Decision: FULL UPDATE (>= 60 minutes)")
                    return "full"
            else:
                print("Decision: FULL UPDATE (invalid timestamp)")
                return "full"
        except Exception as e:
            print(f"Error parsing timestamp: {e}")
            print("Decision: FULL UPDATE (parse error)")
            return "full"
    else:
        print("No .markets_verified_time file found")
        print("Decision: FULL UPDATE (file missing)")
        return "full"

def run_full_update():
    """Run full update steps"""
    print("\n=== Running Full Update ===")
    
    # Update timestamp BEFORE processing
    update_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with open(".markets_verified_time", "w", encoding="utf-8") as f:
        f.write(update_time)
    print(f"Updated .markets_verified_time to: {update_time}")
    
    # Run fetch_polymarket.py
    print("\nStep 1: Fetching all markets...")
    result = subprocess.run(["python", "fetch_polymarket.py"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    if result.returncode != 0:
        print(f"ERROR: fetch_polymarket.py failed with code {result.returncode}")
        return False
    
    # Run cluster_markets.py
    print("\nStep 2: Processing markets and generating HTML...")
    result = subprocess.run(["python", "cluster_markets.py"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    if result.returncode != 0:
        print(f"ERROR: cluster_markets.py failed with code {result.returncode}")
        return False
    
    print("\n[SUCCESS] Full update completed successfully!")
    return True

def run_price_refresh():
    """Run price refresh steps"""
    print("\n=== Running Price Refresh ===")
    
    result = subprocess.run(["python", "refresh_prices.py"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    if result.returncode != 0:
        print(f"ERROR: refresh_prices.py failed with code {result.returncode}")
        return False
    
    print("\n[SUCCESS] Price refresh completed successfully!")
    return True

def verify_html():
    """Verify HTML file exists and has content"""
    print("\n=== Verifying HTML Update ===")
    
    if not os.path.exists("market_report.html"):
        print("[ERROR] market_report.html not found!")
        return False
    
    size = os.path.getsize("market_report.html")
    if size == 0:
        print("[ERROR] market_report.html is empty!")
        return False
    
    print(f"[OK] HTML file size: {size} bytes")
    
    with open("market_report.html", "r", encoding="utf-8") as f:
        content = f.read()
    
    if "Global Conflict Map" not in content:
        print("[ERROR] HTML missing expected title!")
        return False
    print("[OK] HTML contains expected title")
    
    if "linesData" not in content:
        print("[ERROR] HTML missing market data (linesData)!")
        return False
    print("[OK] HTML contains market data")
    
    if "leaflet" not in content.lower():
        print("[ERROR] HTML missing Leaflet map library!")
        return False
    print("[OK] HTML contains Leaflet map")
    
    print("=== HTML Verification Complete ===")
    return True

def main():
    print("GitHub Actions Workflow - Local Test")
    print("=" * 50)
    
    # Check what type of update is needed
    update_type = check_update_type()
    
    # Run the appropriate update
    if update_type == "full":
        success = run_full_update()
    else:
        success = run_price_refresh()
    
    if not success:
        print("\n[ERROR] Update failed!")
        return 1
    
    # Verify HTML
    if not verify_html():
        print("\n[ERROR] HTML verification failed!")
        return 1
    
    print("\n" + "=" * 50)
    print("[SUCCESS] All steps completed successfully!")
    return 0

if __name__ == "__main__":
    exit(main())
