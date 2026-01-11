# Conflict Map Generator

Single Python script to fetch Polymarket data, filter conflict markets, and generate HTML map.

## Usage

### Manual Generation
```bash
python generate_map.py
```

This will:
1. Fetch all active markets from Polymarket API
2. Filter for conflict-related markets (military, trade, diplomatic, etc.)
3. Generate `market_report.html` with interactive map

### Automated Updates (Every 30 Minutes)

Run the auto-updater script:
```bash
python auto_update.py
```

This will:
1. Generate the report
2. Commit changes to git
3. Push to GitHub
4. Repeat every 30 minutes

**To stop:** Press `Ctrl+C`

## Files

- `generate_map.py` - Main script to generate the map
- `auto_update.py` - Automated script that runs every 30 minutes
- `market_report.html` - Generated HTML report (committed to git)

## Requirements

```bash
pip install requests
```

## GitHub Pages

The map is available at:
```
https://oricohen792.github.io/conflict-map/market_report.html
```

## Workflow

1. **Manual:** Run `python generate_map.py` locally, then commit/push manually
2. **Automated:** Run `python auto_update.py` and leave it running - it will update every 30 minutes automatically
