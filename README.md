# Global Conflict Map

A real-time interactive map visualizing global conflict predictions from Polymarket prediction markets.

## 🌍 Live Demo
[View Live Map](https://your-username.github.io/your-repo-name/market_report.html)

## Features

- **Interactive Map**: Click on any country to see its conflict markets
- **Real-time Updates**: 
  - Prices refresh every 5 minutes
  - Full market data updates every hour
- **Smart Filtering**: Filter by category (Military, Diplomatic, Trade, Drugs & Border)
- **Dynamic Counts**: See market count and total volume for each country
- **Clickable Markets**: Click any market to view details on Polymarket
- **Color-coded Arcs**: Visual representation of probability (Green=High, Yellow=Medium, Red=Low)

## Technology Stack

- **Backend**: Python (data fetching & processing)
- **Frontend**: Leaflet.js for interactive mapping
- **Data Source**: Polymarket API
- **Automation**: GitHub Actions (scheduled updates)

## Setup

### Prerequisites
- Python 3.8+
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/conflict-map.git
cd conflict-map
```

2. Install dependencies:
```bash
pip install requests numpy
```

3. Run initial data fetch:
```bash
python fetch_polymarket.py
python cluster_markets.py
```

4. Open `market_report.html` in your browser

### Automated Updates

Run the auto-update service:
```bash
python auto_update.py
```

This will:
- Refresh prices every 5 minutes
- Fetch all markets every hour
- Regenerate the HTML automatically

## Project Structure

```
conflict-map/
├── fetch_polymarket.py      # Fetch all markets from Polymarket
├── cluster_markets.py        # Process data and generate HTML
├── refresh_prices.py         # Quick price updates
├── auto_update.py           # Automated update service
├── market_report.html       # Generated interactive map
├── conflict_manifest.json   # Processed conflict markets
├── recent_changes.json      # Price change tracking
└── DEPLOYMENT.md           # Deployment guide
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions including:
- GitHub Pages + GitHub Actions (recommended)
- Netlify
- Your own VPS
- Vercel

## How It Works

1. **Data Collection**: Fetches 24,000+ markets from Polymarket API
2. **Filtering**: Identifies markets involving potential conflicts between countries
3. **Categorization**: Classifies into Military, Diplomatic, Trade, and Border conflicts
4. **Visualization**: Generates interactive map with arcs between countries
5. **Real-time Updates**: Continuously updates prices and discovers new markets

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

MIT License - feel free to use and modify

## Acknowledgments

- Data from [Polymarket](https://polymarket.com)
- Maps powered by [Leaflet.js](https://leafletjs.com)
- Tiles from [CARTO](https://carto.com)

---

Built with ❤️ for tracking global conflict predictions
