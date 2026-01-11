#!/usr/bin/env python3
"""
Automated script to generate conflict map report, commit, and push every 30 minutes
"""
import subprocess
import sys
import time
from datetime import datetime, timezone

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
            cwd="c:\\dev\\mempool"
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

def generate_and_push():
    """Generate report, commit, and push to git"""
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"Starting automated update at {current_time} UTC")
    print(f"{'='*60}")
    
    # Step 1: Generate report
    print("\n[1/3] Generating conflict map report...")
    success = run_command(
        "python generate_map.py",
        "Generating Report"
    )
    if not success:
        print("Failed to generate report. Skipping commit/push.")
        return False
    
    # Step 2: Check if there are changes
    print("\n[2/3] Checking for changes...")
    result = subprocess.run(
        "git status --porcelain market_report.html",
        shell=True,
        capture_output=True,
        text=True,
        cwd="c:\\dev\\mempool"
    )
    
    if not result.stdout.strip():
        print("No changes detected in market_report.html. Skipping commit.")
        return True
    
    # Step 3: Commit changes
    print("\n[3/3] Committing and pushing changes...")
    commit_message = f"Auto-update conflict map - {current_time} UTC"
    
    success = run_command(
        "git add market_report.html",
        "Staging Changes"
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
    print("="*60)
    print("Conflict Map Auto-Updater")
    print("="*60)
    print("This script will generate the report, commit, and push")
    print("every 30 minutes. Press Ctrl+C to stop.")
    print("="*60)
    
    # Run immediately on start
    generate_and_push()
    
    # Then run every 30 minutes
    while True:
        try:
            print(f"\nWaiting 30 minutes until next update...")
            print(f"Next update at: {(datetime.now(timezone.utc).timestamp() + 1800):.0f}")
            time.sleep(30 * 60)  # 30 minutes = 1800 seconds
            generate_and_push()
        except KeyboardInterrupt:
            print("\n\nStopped by user. Exiting...")
            break
        except Exception as e:
            print(f"\nError in main loop: {e}")
            print("Continuing in 30 minutes...")
            time.sleep(30 * 60)

if __name__ == "__main__":
    main()
