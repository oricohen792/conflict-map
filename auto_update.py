import time
import subprocess
import os
from datetime import datetime, timezone

# Configuration
PRICE_REFRESH_INTERVAL = 300  # 5 minutes (in seconds)
FETCH_INTERVAL = 3600  # 1 hour (in seconds)

def log(message):
    # Use UTC for consistency
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def run_script(script_name):
    """Run a Python script and return True if successful"""
    try:
        log(f"Running {script_name}...")
        result = subprocess.run(
            ["python", script_name],
            cwd=os.path.dirname(__file__) or ".",
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        if result.returncode == 0:
            log(f"✓ {script_name} completed successfully")
            return True
        else:
            log(f"✗ {script_name} failed with code {result.returncode}")
            if result.stderr:
                log(f"  Error: {result.stderr[:200]}")
            return False
    except Exception as e:
        log(f"✗ Error running {script_name}: {str(e)}")
        return False

def main():
    log("========================================")
    log("Auto-update service started")
    log(f"Price refresh every {PRICE_REFRESH_INTERVAL}s ({PRICE_REFRESH_INTERVAL//60} min)")
    log(f"Full market fetch every {FETCH_INTERVAL}s ({FETCH_INTERVAL//3600} hour)")
    log("========================================")
    
    # Initial full fetch
    log("Performing initial full data fetch...")
    run_script("fetch_polymarket.py")
    run_script("cluster_markets.py")
    
    last_fetch_time = time.time()
    
    while True:
        try:
            current_time = time.time()
            
            # Check if it's time for a full fetch
            if current_time - last_fetch_time >= FETCH_INTERVAL:
                log("--- Full Market Fetch ---")
                if run_script("fetch_polymarket.py"):
                    run_script("cluster_markets.py")
                last_fetch_time = current_time
            else:
                # Just refresh prices
                log("--- Price Refresh ---")
                run_script("refresh_prices.py")
            
            # Wait for next cycle
            log(f"Next price refresh in {PRICE_REFRESH_INTERVAL}s")
            time.sleep(PRICE_REFRESH_INTERVAL)
            
        except KeyboardInterrupt:
            log("Shutting down auto-update service...")
            break
        except Exception as e:
            log(f"Error in main loop: {str(e)}")
            time.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    main()
