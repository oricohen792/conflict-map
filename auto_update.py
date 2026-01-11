#!/usr/bin/env python3
"""
Automated script to generate conflict map report, commit, and push every 30 minutes
"""
import subprocess
import sys
import os
import time
import json
from datetime import datetime, timezone, timedelta

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "polymarket_data.json")

def run_command(command, description):
    """Run a shell command and return success status"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=SCRIPT_DIR
        )
        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

def should_fetch_data(skip_fetch=False):
    """Check if we should fetch new data - defaults to True (always fetch)"""
    if skip_fetch:
        return False
    return True  # Default: always fetch data on every loop

def generate_and_push(skip_fetch=False):
    """Generate reports, commit, and push to git"""
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"Starting automated update at {current_time} UTC")
    print(f"{'='*60}")
    
    # Step 1: Fetch data (default: always fetch)
    if should_fetch_data(skip_fetch):
        print("\n[1/3] Fetching Polymarket data...")
        success = run_command(
            "python fetch_polymarket_data.py",
            "Fetching Data"
        )
        if not success:
            print("Failed to fetch data. Checking if existing data can be used...")
            if not os.path.exists(DATA_FILE):
                print("No data available. Skipping generation.")
                return False
            print("Using existing data file.")
    else:
        print("\n[1/3] Skipping data fetch (using existing data)")
    
    # Step 2: Generate combined map with all types
    print("\n[2/3] Generating market report with all map types...")
    success = run_command(
        "python generate_combined_map.py",
        "Generating Market Report"
    )
    if not success:
        print("Failed to generate market report. Continuing...")
    
    # Step 3: Check if there are changes (only HTML files)
    print("\n[3/3] Checking for changes in HTML files...")
    result = subprocess.run(
        "git status --porcelain market_report.html",
        shell=True,
        capture_output=True,
        text=True,
        cwd=SCRIPT_DIR
    )
    
    if not result.stdout.strip():
        print("No changes detected in HTML files. Skipping commit.")
        return True
    
    # Step 4: Commit changes (only HTML files)
    print("\n[4/4] Committing and pushing HTML changes...")
    commit_message = f"Auto-update maps - {current_time} UTC"
    
    success = run_command(
        "git add market_report.html",
        "Staging HTML Changes"
    )
    if not success:
        return False
    
    success = run_command(
        f'git commit -m "{commit_message}"',
        "Committing Changes"
    )
    if not success:
        return False
    
    success = run_command(
        "git push origin main",
        "Pushing to GitHub"
    )
    if not success:
        return False
    
    print(f"\n{'='*60}")
    print(f"Successfully updated and pushed at {current_time} UTC")
    print(f"{'='*60}")
    return True

def main():
    """Main loop - run every 30 minutes"""
    # Check for command line arguments
    skip_fetch = "--skip-fetch" in sys.argv or "-s" in sys.argv
    
    print("="*60)
    print("Polymarket Maps Auto-Updater")
    print("="*60)
    print("This script will generate maps, commit, and push every 30 minutes.")
    print("Data will be fetched on every loop by default.")
    if skip_fetch:
        print("SKIP FETCH MODE: Will use existing data without fetching.")
    print("Generates: Combined map with all types (Conflict, Sport, Finance, Elections, Technology, Political Leadership)")
    print("Only HTML files will be committed.")
    print("Press Ctrl+C to stop.")
    print("="*60)
    
    # Run immediately on start
    generate_and_push(skip_fetch=skip_fetch)
    
    # Then run every 30 minutes
    while True:
        try:
            print(f"\nWaiting 30 minutes until next update...")
            next_update = datetime.now(timezone.utc) + timedelta(minutes=30)
            print(f"Next update at: {next_update.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            time.sleep(30 * 60)  # 30 minutes = 1800 seconds
            generate_and_push(skip_fetch=skip_fetch)
        except KeyboardInterrupt:
            print("\n\nStopped by user. Exiting...")
            break
        except Exception as e:
            print(f"\nError in main loop: {e}")
            print("Continuing in 30 minutes...")
            time.sleep(30 * 60)

if __name__ == "__main__":
    main()
