#!/usr/bin/env python3
"""
Generate market inventory report - shows all markets with zones and mapping status
"""
import json
from datetime import datetime, timezone
from map_base import MapGeneratorBase, ZONE_COORD_MAP

# Import filtering logic from all map generators
from generate_map_conflict import CAT_KEYWORDS, all_keywords
from generate_map_sport import SPORT_KEYWORDS, all_sport_keywords, EXCLUSION_KEYWORDS
from generate_map_finance import FINANCE_KEYWORDS, all_finance_keywords
from generate_map_elections import ELECTION_KEYWORDS, all_election_keywords, EXCLUSION_KEYWORDS as ELECTION_EXCLUSION_KEYWORDS
from generate_map_technology import TECH_KEYWORDS, all_tech_keywords


class MarketInventoryGenerator(MapGeneratorBase):
    """Generate inventory of all markets with zones and mapping status"""
    
    def __init__(self):
        super().__init__("Market Inventory Generator", "market_inventory.html")
    
    def analyze_markets(self):
        """Analyze all markets and categorize them"""
        markets_data = []
        conflict_market_ids = set()
        sport_market_ids = set()
        finance_market_ids = set()
        election_market_ids = set()
        tech_market_ids = set()
        
        print("Analyzing all markets...")
        
        # First pass: identify all mapped markets
        for m in self.markets:
            q = m.get("question", "")
            q_lower = q.lower()
            m_id = m.get("id", "")
            
            # Check if conflict market
            assigned_cat = "Other"
            for cat, keywords in CAT_KEYWORDS.items():
                if any(k in q_lower for k in keywords):
                    assigned_cat = cat
                    break
            
            is_conflict = False
            if assigned_cat != "Other" or any(k in q_lower for k in all_keywords):
                found_zones = self.find_zones_in_text(q)
                if len(found_zones) >= 2:
                    is_conflict = True
                    conflict_market_ids.add(m_id)
            
            # Check if sport market
            is_sport = False
            if not any(excl in q_lower for excl in EXCLUSION_KEYWORDS):
                assigned_sport_cat = "Other Sports"
                for cat, keywords in SPORT_KEYWORDS.items():
                    if any(k in q_lower for k in keywords):
                        assigned_sport_cat = cat
                        break
                
                if assigned_sport_cat != "Other Sports" or any(k in q_lower for k in all_sport_keywords):
                    found_zones = self.find_zones_in_text(q)
                    if len(found_zones) >= 1:
                        is_sport = True
                        sport_market_ids.add(m_id)
            
            # Check if finance market
            is_finance = False
            if not any(excl in q_lower for excl in EXCLUSION_KEYWORDS):
                assigned_finance_cat = "Other Financial"
                for cat, keywords in FINANCE_KEYWORDS.items():
                    if any(k in q_lower for k in keywords):
                        assigned_finance_cat = cat
                        break
                
                if assigned_finance_cat != "Other Financial" or any(k in q_lower for k in all_finance_keywords):
                    found_zones = self.find_zones_in_text(q)
                    # For Fed events, default to US if no zone found
                    if len(found_zones) >= 1 or any(k in q_lower for k in ["fed", "federal reserve", "fomc", "jerome powell"]):
                        is_finance = True
                        finance_market_ids.add(m_id)
            
            # Check if election/politics market
            is_election = False
            if not any(excl in q_lower for excl in ELECTION_EXCLUSION_KEYWORDS):
                assigned_election_cat = "Voting"
                for cat, keywords in ELECTION_KEYWORDS.items():
                    if any(k in q_lower for k in keywords):
                        assigned_election_cat = cat
                        break
                
                if assigned_election_cat != "Voting" or any(k in q_lower for k in all_election_keywords):
                    found_zones = self.find_zones_in_text(q)
                    # For US political events, default to US if no zone found
                    if len(found_zones) >= 1 or any(k in q_lower for k in ["president", "presidential", "senate", "congress", "supreme court"]):
                        is_election = True
                        election_market_ids.add(m_id)
            
            # Check if technology market
            is_tech = False
            if not any(excl in q_lower for excl in EXCLUSION_KEYWORDS):
                assigned_tech_cat = "Other Technology"
                for cat, keywords in TECH_KEYWORDS.items():
                    if any(k in q_lower for k in keywords):
                        assigned_tech_cat = cat
                        break
                
                if assigned_tech_cat != "Other Technology" or any(k in q_lower for k in all_tech_keywords):
                    found_zones = self.find_zones_in_text(q)
                    # For major US tech companies, default to US if no zone found
                    if len(found_zones) >= 1 or any(k in q_lower for k in ["apple", "google", "microsoft", "meta", "amazon", "nvidia", "tesla", "openai"]):
                        is_tech = True
                        tech_market_ids.add(m_id)
        
        # Second pass: collect all market data
        for m in self.markets:
            q = m.get("question", "")
            q_lower = q.lower()
            m_id = m.get("id", "")
            vol = float(m.get("volume", 0) or 0)
            price = float(m.get("lastTradePrice", 0) or 0)
            end_date = m.get("endDate", "")[:10]
            
            found_zones = self.find_zones_in_text(q)
            zone_names = list(found_zones.keys())
            
            # Skip markets with no zones
            if not zone_names:
                continue
            
            parent_slug = m.get("slug", "")
            events = m.get("events", [])
            if events and len(events) > 0:
                parent_slug = events[0].get("slug", parent_slug)
            
            mapped_to = []
            if m_id in conflict_market_ids:
                mapped_to.append("Conflict")
            if m_id in sport_market_ids:
                mapped_to.append("Sport")
            if m_id in finance_market_ids:
                mapped_to.append("Finance")
            if m_id in election_market_ids:
                mapped_to.append("Elections")
            if m_id in tech_market_ids:
                mapped_to.append("Technology")
            
            markets_data.append({
                "id": m_id,
                "question": q,
                "zones": zone_names,
                "volume": vol,
                "price": price,
                "date": end_date,
                "slug": parent_slug,
                "url": f"https://polymarket.com/event/{parent_slug}",
                "mapped_to": mapped_to,
                "is_mapped": len(mapped_to) > 0
            })
        
        print(f"Found {len(markets_data)} markets with zones")
        print(f"  - {len(conflict_market_ids)} mapped to conflicts")
        print(f"  - {len(sport_market_ids)} mapped to sports")
        print(f"  - {len(finance_market_ids)} mapped to finance")
        print(f"  - {len(election_market_ids)} mapped to elections")
        print(f"  - {len(tech_market_ids)} mapped to technology")
        print(f"  - {len([m for m in markets_data if not m['is_mapped']])} unmapped")
        
        return markets_data
    
    def generate_html(self, markets_data):
        """Generate HTML inventory report"""
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        # Group markets by zone
        zones_dict = {}
        for m in markets_data:
            for zone in m["zones"]:
                if zone not in zones_dict:
                    zones_dict[zone] = []
                zones_dict[zone].append(m)
        
        # Sort zones by market count
        sorted_zones = sorted(zones_dict.items(), key=lambda x: len(x[1]), reverse=True)
        num_zones = len(sorted_zones)
        
        # Generate zone sections
        zones_html = ""
        for zone, zone_markets in sorted_zones:
            mapped_count = sum(1 for m in zone_markets if m["is_mapped"])
            unmapped_count = len(zone_markets) - mapped_count
            
            zones_html += f"""
            <div class="zone-section">
                <h2 class="zone-header">
                    <span class="zone-name">{zone}</span>
                    <span class="zone-count">({len(zone_markets)} markets, {mapped_count} mapped, {unmapped_count} unmapped)</span>
                </h2>
                <div class="markets-list">
            """
            
            # Sort markets: mapped first, then by volume
            sorted_markets = sorted(zone_markets, key=lambda x: (not x["is_mapped"], -x["volume"]))
            
            for m in sorted_markets:
                status_badges = ""
                if "Conflict" in m["mapped_to"]:
                    status_badges += '<span class="badge badge-conflict">Conflict</span>'
                if "Sport" in m["mapped_to"]:
                    status_badges += '<span class="badge badge-sport">Sport</span>'
                if "Finance" in m["mapped_to"]:
                    status_badges += '<span class="badge badge-finance">Finance</span>'
                if not m["is_mapped"]:
                    status_badges += '<span class="badge badge-unmapped">Unmapped</span>'
                
                vol_str = f"${m['volume']/1000:.1f}K" if m['volume'] >= 1000 else f"${m['volume']:.0f}"
                price_pct = int(m['price'] * 100)
                
                zones_html += f"""
                    <div class="market-item {'mapped' if m['is_mapped'] else 'unmapped'}">
                        <div class="market-header">
                            <a href="{m['url']}" target="_blank" class="market-link">{m['question']}</a>
                            <div class="market-badges">{status_badges}</div>
                        </div>
                        <div class="market-details">
                            <span class="detail-item">Volume: {vol_str}</span>
                            <span class="detail-item">Price: {price_pct}%</span>
                            <span class="detail-item">Date: {m['date']}</span>
                            <span class="detail-item">Zones: {', '.join(m['zones'])}</span>
                        </div>
                    </div>
                """
            
            zones_html += """
                </div>
            </div>
            """
        
        html_head = self.get_common_html_head()
        analytics_code = self.get_analytics_code()
        
        html_content = html_head + """
    <style>
        body { 
            margin: 0; 
            padding: 20px; 
            background-color: #0f172a; 
            color: #e2e8f0; 
            font-family: 'Inter', -apple-system, sans-serif; 
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: rgba(15, 23, 42, 0.95);
            padding: 30px;
            border-radius: 12px;
            border: 1px solid #334155;
            margin-bottom: 30px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
        }
        .header h1 {
            margin: 0 0 10px 0;
            font-size: 2rem;
            color: white;
        }
        .header p {
            margin: 5px 0;
            color: #94a3b8;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .stat-box {
            background: rgba(59, 130, 246, 0.1);
            padding: 15px 20px;
            border-radius: 8px;
            border-left: 3px solid #3b82f6;
            flex: 1;
            min-width: 200px;
        }
        .stat-box h3 {
            margin: 0 0 5px 0;
            font-size: 0.9rem;
            color: #94a3b8;
        }
        .stat-box .stat-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: #3b82f6;
        }
        .zone-section {
            background: rgba(15, 23, 42, 0.95);
            padding: 25px;
            border-radius: 12px;
            border: 1px solid #334155;
            margin-bottom: 25px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
        }
        .zone-header {
            margin: 0 0 20px 0;
            padding-bottom: 15px;
            border-bottom: 2px solid #334155;
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        .zone-name {
            font-size: 1.5rem;
            font-weight: 700;
            color: white;
        }
        .zone-count {
            font-size: 1rem;
            color: #94a3b8;
            font-weight: 400;
        }
        .markets-list {
            display: grid;
            gap: 15px;
        }
        .market-item {
            background: rgba(30, 41, 59, 0.5);
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #334155;
            transition: all 0.2s;
        }
        .market-item:hover {
            border-color: #475569;
            background: rgba(30, 41, 59, 0.7);
        }
        .market-item.unmapped {
            border-left: 4px solid #ef4444;
        }
        .market-item.mapped {
            border-left: 4px solid #22c55e;
        }
        .market-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 15px;
            margin-bottom: 10px;
            flex-wrap: wrap;
        }
        .market-link {
            color: #e2e8f0;
            text-decoration: none;
            font-weight: 600;
            font-size: 1rem;
            flex: 1;
            min-width: 300px;
        }
        .market-link:hover {
            color: #3b82f6;
            text-decoration: underline;
        }
        .market-badges {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .badge {
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            white-space: nowrap;
        }
        .badge-conflict {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            border: 1px solid #ef4444;
        }
        .badge-sport {
            background: rgba(34, 197, 94, 0.2);
            color: #22c55e;
            border: 1px solid #22c55e;
        }
        .badge-finance {
            background: rgba(251, 191, 36, 0.2);
            color: #fbbf24;
            border: 1px solid #fbbf24;
        }
        .badge-unmapped {
            background: rgba(148, 163, 184, 0.2);
            color: #94a3b8;
            border: 1px solid #94a3b8;
        }
        .market-details {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            font-size: 0.85rem;
            color: #94a3b8;
        }
        .detail-item {
            white-space: nowrap;
        }
        .nav-links {
            display: flex;
            gap: 15px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .nav-link {
            padding: 10px 20px;
            background: rgba(59, 130, 246, 0.1);
            color: #3b82f6;
            text-decoration: none;
            border-radius: 6px;
            border: 1px solid #3b82f6;
            font-weight: 600;
            transition: all 0.2s;
        }
        .nav-link:hover {
            background: rgba(59, 130, 246, 0.2);
        }
        @media (max-width: 768px) {
            .header h1 { font-size: 1.5rem; }
            .zone-name { font-size: 1.2rem; }
            .market-header { flex-direction: column; }
            .market-link { min-width: auto; }
        }
    </style>
""" + analytics_code + """
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Market Inventory Report</h1>
            <p>All Polymarket markets with geographic zones</p>
            <div style="margin-top: 12px; padding: 8px; background: rgba(59, 130, 246, 0.1); border-radius: 6px; border-left: 3px solid #3b82f6;">
                <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 2px;">Last Updated</div>
                <div style="color: #3b82f6; font-weight: 700; font-size: 0.95rem;">""" + current_time + """</div>
            </div>
            <div class="stats">
                <div class="stat-box">
                    <h3>Total Markets</h3>
                    <div class="stat-value">""" + str(len(markets_data)) + """</div>
                </div>
                <div class="stat-box">
                    <h3>Mapped Markets</h3>
                    <div class="stat-value">""" + str(sum(1 for m in markets_data if m["is_mapped"])) + """</div>
                </div>
                <div class="stat-box">
                    <h3>Unmapped Markets</h3>
                    <div class="stat-value">""" + str(sum(1 for m in markets_data if not m["is_mapped"])) + """</div>
                </div>
                <div class="stat-box">
                    <h3>Zones Covered</h3>
                    <div class="stat-value">""" + str(num_zones) + """</div>
                </div>
            </div>
            <div class="nav-links">
                <a href="market_report.html" class="nav-link">⚔️ Conflict Map</a>
                <a href="sport_report.html" class="nav-link">⚽ Sport Map</a>
                <a href="finance_report.html" class="nav-link">💰 Finance Map</a>
            </div>
        </div>
        """ + zones_html + """
    </div>
</body>
</html>
"""
        
        return html_content


def main():
    generator = MarketInventoryGenerator()
    generator.run()


if __name__ == "__main__":
    # Override run method to use analyze_markets instead of filter_markets
    original_run = MarketInventoryGenerator.run
    
    def custom_run(self):
        print("=" * 60)
        print(self.title)
        print("=" * 60)
        print(f"Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
        
        # Step 1: Load markets
        markets = self.load_markets()
        if not markets:
            return
        
        # Step 2: Analyze markets
        markets_data = self.analyze_markets()
        if not markets_data:
            print(f"Error: No markets found")
            return
        
        # Step 3: Generate HTML
        print("\nGenerating HTML report...")
        html_content = self.generate_html(markets_data)
        
        # Step 4: Save HTML
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"\nDone! Generated {self.output_file} with {len(markets_data)} markets")
        print(f"Completed at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    MarketInventoryGenerator.run = custom_run
    main()
