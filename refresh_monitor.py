import json
import os
from datetime import datetime
from typing import Optional

REFRESH_LOG_FILE = "refresh_log.json"
MAX_LOG_ENTRIES = 100  # Keep last 100 refresh events

def log_refresh(refresh_type: str, duration_seconds: Optional[float] = None, 
                markets_count: Optional[int] = None, success: bool = True, 
                error: Optional[str] = None):
    """
    Log a refresh event to the refresh log file.
    
    Args:
        refresh_type: 'full' or 'price'
        duration_seconds: How long the refresh took
        markets_count: Number of markets processed
        success: Whether the refresh succeeded
        error: Error message if failed
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": refresh_type,
        "success": success,
        "duration_seconds": duration_seconds,
        "markets_count": markets_count,
        "error": error
    }
    
    # Load existing log
    log_entries = []
    if os.path.exists(REFRESH_LOG_FILE):
        try:
            with open(REFRESH_LOG_FILE, "r", encoding="utf-8") as f:
                log_entries = json.load(f)
        except:
            log_entries = []
    
    # Add new entry
    log_entries.append(log_entry)
    
    # Keep only last MAX_LOG_ENTRIES entries
    log_entries = log_entries[-MAX_LOG_ENTRIES:]
    
    # Save log
    with open(REFRESH_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log_entries, f, indent=2)
    
    # Print summary
    status = "✓" if success else "✗"
    duration_str = f" ({duration_seconds:.1f}s)" if duration_seconds else ""
    markets_str = f" - {markets_count} markets" if markets_count else ""
    error_str = f" - ERROR: {error}" if error else ""
    print(f"[Refresh Monitor] {status} {refresh_type.upper()}{duration_str}{markets_str}{error_str}")

def get_refresh_stats():
    """Get statistics about recent refreshes."""
    if not os.path.exists(REFRESH_LOG_FILE):
        return None
    
    try:
        with open(REFRESH_LOG_FILE, "r", encoding="utf-8") as f:
            log_entries = json.load(f)
    except:
        return None
    
    if not log_entries:
        return None
    
    # Calculate stats
    full_refreshes = [e for e in log_entries if e.get("type") == "full"]
    price_refreshes = [e for e in log_entries if e.get("type") == "price"]
    
    successful_full = [e for e in full_refreshes if e.get("success")]
    successful_price = [e for e in price_refreshes if e.get("success")]
    
    stats = {
        "total_refreshes": len(log_entries),
        "full_refreshes": len(full_refreshes),
        "price_refreshes": len(price_refreshes),
        "last_full_refresh": successful_full[-1] if successful_full else None,
        "last_price_refresh": successful_price[-1] if successful_price else None,
        "avg_full_duration": None,
        "avg_price_duration": None,
        "recent_entries": log_entries[-10:]  # Last 10 entries
    }
    
    # Calculate average durations
    full_durations = [e.get("duration_seconds") for e in successful_full if e.get("duration_seconds")]
    price_durations = [e.get("duration_seconds") for e in successful_price if e.get("duration_seconds")]
    
    if full_durations:
        stats["avg_full_duration"] = sum(full_durations) / len(full_durations)
    if price_durations:
        stats["avg_price_duration"] = sum(price_durations) / len(price_durations)
    
    return stats

if __name__ == "__main__":
    # Print current stats
    stats = get_refresh_stats()
    if stats:
        print("\n=== Refresh Monitor Stats ===")
        print(f"Total refreshes: {stats['total_refreshes']}")
        print(f"Full refreshes: {stats['full_refreshes']}")
        print(f"Price refreshes: {stats['price_refreshes']}")
        if stats['last_full_refresh']:
            last = stats['last_full_refresh']
            print(f"\nLast full refresh: {last['timestamp']} ({last.get('duration_seconds', 'N/A')}s)")
        if stats['last_price_refresh']:
            last = stats['last_price_refresh']
            print(f"Last price refresh: {last['timestamp']} ({last.get('duration_seconds', 'N/A')}s)")
        if stats['avg_full_duration']:
            print(f"Avg full duration: {stats['avg_full_duration']:.1f}s")
        if stats['avg_price_duration']:
            print(f"Avg price duration: {stats['avg_price_duration']:.1f}s")
        print("\n=== Recent Entries ===")
        for entry in stats['recent_entries']:
            status = "✓" if entry.get('success') else "✗"
            print(f"{status} {entry['timestamp']} - {entry['type']} ({entry.get('duration_seconds', 'N/A')}s)")
    else:
        print("No refresh log found.")
