# Conflict Map Deployment Guide

This guide explains how to deploy your Global Conflict Map to the internet with automatic updates.

## Option 1: GitHub Pages + GitHub Actions (Recommended - Free)

### Step 1: Prepare Repository
1. Create a new GitHub repository
2. Add these files to `.gitignore`:
```
active_markets.jsonl
__pycache__/
*.pyc
```

### Step 2: Create GitHub Actions Workflow
Create `.github/workflows/update-map.yml`:

```yaml
name: Update Conflict Map

on:
  schedule:
    - cron: '*/5 * * * *'  # Every 5 minutes (price refresh)
    - cron: '0 * * * *'    # Every hour (full update)
  workflow_dispatch:  # Allow manual trigger

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install requests numpy
      
      - name: Determine update type
        id: update_type
        run: |
          MINUTE=$(date +%M)
          if [ "$MINUTE" = "00" ]; then
            echo "type=full" >> $GITHUB_OUTPUT
          else
            echo "type=price" >> $GITHUB_OUTPUT
          fi
      
      - name: Full market fetch (hourly)
        if: steps.update_type.outputs.type == 'full'
        run: |
          python fetch_polymarket.py
          python cluster_markets.py
      
      - name: Price refresh only
        if: steps.update_type.outputs.type == 'price'
        run: |
          python refresh_prices.py
      
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./
          publish_branch: gh-pages
          keep_files: true
```

### Step 3: Enable GitHub Pages
1. Go to repository Settings → Pages
2. Source: Deploy from branch `gh-pages`
3. Save

Your map will be at: `https://[username].github.io/[repo-name]/market_report.html`

---

## Option 2: Netlify (Easy, Free Tier)

### Step 1: Create `netlify.toml`
```toml
[build]
  command = "python cluster_markets.py"
  publish = "."

[[plugins]]
  package = "@netlify/plugin-nextjs"
```

### Step 2: Deploy
1. Go to [netlify.com](https://netlify.com)
2. "Add new site" → "Import from Git"
3. Connect your repository
4. Deploy

### Step 3: Scheduled Updates
Use Netlify Build Hooks + external cron service (like cron-job.org):
1. Netlify: Settings → Build & deploy → Build hooks → Add build hook
2. Copy webhook URL
3. Use [cron-job.org](https://cron-job.org) to call webhook every 5 minutes

---

## Option 3: Your Own Server (VPS - Full Control)

### Requirements
- Linux VPS (Ubuntu/Debian recommended)
- Python 3.8+
- Web server (nginx/apache)

### Step 1: Setup Server
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip nginx -y
pip3 install requests numpy

# Create directory
mkdir -p /var/www/conflict-map
cd /var/www/conflict-map
```

### Step 2: Upload Files
Upload all your Python files and run initial setup:
```bash
python3 fetch_polymarket.py
python3 cluster_markets.py
```

### Step 3: Setup Systemd Service
Create `/etc/systemd/system/conflict-map.service`:
```ini
[Unit]
Description=Conflict Map Auto-Update Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/conflict-map
ExecStart=/usr/bin/python3 /var/www/conflict-map/auto_update.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable conflict-map
sudo systemctl start conflict-map
```

### Step 4: Configure Nginx
Create `/etc/nginx/sites-available/conflict-map`:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    root /var/www/conflict-map;
    index market_report.html;
    
    location / {
        try_files $uri $uri/ =404;
    }
    
    # Cache static files
    location ~* \.(html|json)$ {
        expires 1m;
        add_header Cache-Control "public, must-revalidate";
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/conflict-map /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Option 4: Vercel (Serverless - Free Tier)

### Step 1: Install Vercel CLI
```bash
npm install -g vercel
```

### Step 2: Create `vercel.json`
```json
{
  "builds": [
    {
      "src": "cluster_markets.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/market_report.html"
    }
  ]
}
```

### Step 3: Deploy
```bash
vercel --prod
```

---

## Recommended Setup for Your Use Case

For automatic updates with minimal cost:

**Best Option: GitHub Pages + GitHub Actions**
- ✅ Free
- ✅ Automatic updates (5 min + hourly)
- ✅ Reliable
- ✅ Easy to maintain
- ✅ Git version control

## Current File Structure
```
mempool/
├── fetch_polymarket.py      # Fetch all markets
├── cluster_markets.py        # Generate HTML
├── refresh_prices.py         # Update prices only
├── auto_update.py           # Auto-update service (now 5min/1hour)
├── market_report.html       # Generated map
├── conflict_manifest.json   # Market data
└── active_markets.jsonl     # Full market data
```

## Next Steps
1. Choose deployment option
2. Push code to GitHub
3. Configure automated builds
4. Share the URL!

Let me know which option you prefer and I can help set it up!
