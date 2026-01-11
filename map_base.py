#!/usr/bin/env python3
"""
Base class for map generators - shared functionality
"""
import json
from datetime import datetime, timezone

# Google Analytics 4 Configuration
GA4_TRACKING_ID = "G-SW0C4Y2FC5"

# Zone/Location Dictionary with Canonical Names (includes countries, cities, and regions)
ZONE_MAP = {
    "United States": ["united states", "usa", "u.s.", "us", "america", "biden", "trump"],
    "China": ["china", "beijing", "xi"],
    "Taiwan": ["taiwan", "taipei"],
    "Russia": ["russia", "moscow", "putin"],
    "Ukraine": ["ukraine", "kiev", "kyiv", "zelensky"],
    "Israel": ["israel", "idf", "netanyahu"],
    "Jerusalem": ["jerusalem"],
    "Tel Aviv": ["tel aviv", "tel-aviv"],
    "Iran": ["iran", "tehran"],
    "Palestine": ["palestine", "hamas", "west bank"],
    "Gaza": ["gaza", "gaza strip", "gaza city"],
    "Rafah": ["rafah"],
    "Lebanon": ["lebanon", "beirut", "hezbollah"],
    "Yemen": ["yemen", "houthi"],
    "Syria": ["syria", "damascus"],
    "Iraq": ["iraq", "baghdad"],
    "North Korea": ["north korea", "pyongyang", "dprk", "kim jong un"],
    "South Korea": ["south korea", "seoul"],
    "Japan": ["japan", "tokyo"],
    "Mexico": ["mexico", "mexico city"],
    "Canada": ["canada", "ottawa"],
    "UK": ["uk", "united kingdom", "britain", "london"],
    "France": ["france", "paris", "macron"],
    "Germany": ["germany", "berlin"],
    "EU": ["eu", "european union", "brussels"],
    "India": ["india", "new delhi", "modi"],
    "Pakistan": ["pakistan", "islamabad"],
    "Venezuela": ["venezuela", "caracas", "maduro"],
    "Brazil": ["brazil", "brasilia"],
    "Sudan": ["sudan", "khartoum"]
}

ZONE_COORD_MAP = {
    "United States": [38.9072, -77.0369], "China": [39.9042, 116.4074], "Taiwan": [25.0330, 121.5654],
    "Russia": [55.7558, 37.6173], "Ukraine": [50.4501, 30.5234], "Israel": [31.7683, 35.2137],
    "Jerusalem": [31.7683, 35.2137], "Tel Aviv": [32.0853, 34.7818],
    "Iran": [35.6892, 51.3890], "Palestine": [31.9522, 35.2332], "Gaza": [31.3547, 34.3088],
    "Rafah": [31.2879, 34.2515], "Lebanon": [33.8938, 35.5018],
    "Yemen": [15.5527, 48.5164], "Syria": [33.5138, 36.2765], "Iraq": [33.3152, 44.3661],
    "North Korea": [39.0392, 125.7625], "South Korea": [37.5665, 126.9780], "Japan": [35.6762, 139.6503],
    "Mexico": [19.4326, -99.1332], "Canada": [45.4215, -75.6972], "UK": [51.5074, -0.1278],
    "France": [48.8566, 2.3522], "Germany": [52.5200, 13.4050], "EU": [50.8503, 4.3517],
    "India": [28.6139, 77.2090], "Pakistan": [33.6844, 73.0479], "Venezuela": [10.4806, -66.9036],
    "Brazil": [-15.8267, -47.9218], "Sudan": [15.5007, 32.5599]
}

DATA_FILE = "polymarket_data.json"


class MapGeneratorBase:
    """Base class for map generators"""
    
    def __init__(self, title, output_file):
        self.title = title
        self.output_file = output_file
        self.markets = None
    
    def load_markets(self):
        """Load markets from saved JSON file"""
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            markets = data.get("markets", [])
            print(f"Loaded {len(markets)} markets from {DATA_FILE}")
            self.markets = markets
            return markets
        except FileNotFoundError:
            print(f"Error: {DATA_FILE} not found. Please run fetch_polymarket_data.py first.")
            return None
        except Exception as e:
            print(f"Error loading data: {e}")
            return None
    
    def find_zones_in_text(self, text):
        """Find zones mentioned in text, returns dict of zone_name -> coords"""
        found_zones = {}
        text_lower = text.lower()
        
        for canonical, aliases in ZONE_MAP.items():
            for alias in aliases:
                if len(alias) <= 3:
                    pattern = f" {alias} "
                    if pattern in f" {text_lower} " or text_lower.startswith(f"{alias} ") or text_lower.endswith(f" {alias}"):
                        found_zones[canonical] = ZONE_COORD_MAP[canonical]
                        break
                else:
                    if alias in text_lower:
                        found_zones[canonical] = ZONE_COORD_MAP[canonical]
                        break
        
        return found_zones
    
    def get_analytics_code(self, tracking_id=None):
        """Generate Google Analytics 4 tracking code"""
        if tracking_id is None:
            tracking_id = GA4_TRACKING_ID
        if not tracking_id:
            return ""
        return f"""
    <!-- Google Analytics 4 -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={tracking_id}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{tracking_id}');
    </script>
"""
    
    def get_common_html_head(self):
        """Get common HTML head section"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>""" + self.title + """ - Polymarket</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>"""
    
    def get_common_css(self):
        """Get common CSS styles"""
        return """
    <style>
        body { margin: 0; padding: 0; background-color: #0f172a; color: #e2e8f0; font-family: 'Inter', -apple-system, sans-serif; }
        #map { height: 100vh; width: 100%; background: #0f172a; cursor: crosshair; }
        .leaflet-container { background: #0f172a !important; }
        
        .info-box {
            position: absolute; bottom: 30px; left: 30px; z-index: 1000;
            background: rgba(15, 23, 42, 0.95); padding: 20px; border-radius: 12px;
            border: 1px solid #334155; max-width: 380px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(4px);
        }
        
        .legend {
            position: absolute; top: 30px; right: 30px; z-index: 1000;
            background: rgba(15, 23, 42, 0.95); padding: 15px; border-radius: 12px;
            border: 1px solid #334155; width: 220px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(4px);
        }

        .filter-box {
            position: absolute; top: 30px; left: 30px; z-index: 1000;
            background: rgba(15, 23, 42, 0.95); padding: 15px; border-radius: 12px;
            border: 1px solid #334155; width: 280px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(4px);
        }

        h1 { margin: 0 0 8px 0; font-size: 1rem; font-weight: 700; color: white; letter-spacing: -0.025em; }
        p { margin: 0; font-size: 0.85rem; line-height: 1.4; color: #94a3b8; }
        
        .filter-item { display: flex; align-items: center; margin-bottom: 8px; font-size: 0.9rem; cursor: pointer; }
        .filter-item input { margin-right: 10px; cursor: pointer; }
        
        .legend-item { display: flex; align-items: center; margin-bottom: 6px; font-size: 0.8rem; }
        .legend-color { width: 24px; height: 3px; border-radius: 2px; margin-right: 12px; }
        hr { border: 0; border-top: 1px solid #334155; margin: 12px 0; }

        @media (max-width: 768px) {
            .info-box, .legend { display: none; } 
            
            #mobile-filter-btn {
                display: flex !important;
                position: absolute;
                bottom: 20px;
                right: 20px;
                z-index: 1001;
                background: #3b82f6;
                color: white;
                padding: 12px 20px;
                border-radius: 50px;
                font-weight: bold;
                box-shadow: 0 4px 12px rgba(0,0,0,0.5);
                cursor: pointer;
                border: none;
                align-items: center;
                gap: 8px;
            }

            .filter-box {
                top: auto; 
                bottom: 0px; 
                left: 0; 
                right: 0; 
                width: 100%;
                border-radius: 20px 20px 0 0;
                max-height: 80vh;
                transform: translateY(110%);
                transition: transform 0.3s ease-in-out;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                margin: 0;
                box-sizing: border-box;
            }
            
            .filter-box.active {
                transform: translateY(0);
            }
            
            .close-filter {
                display: block !important;
                text-align: right;
                padding-bottom: 10px;
                color: #94a3b8;
                font-size: 1.5rem;
                cursor: pointer;
            }

            h1 { font-size: 1.1rem; }
            .filter-item { padding: 12px 0; border-bottom: 1px solid #334155; }
            .filter-item input { transform: scale(1.2); margin-right: 15px; }
            
            .leaflet-control-zoom { display: none; }
            .leaflet-bottom.leaflet-right { display: none; }
        }
    </style>"""
    
    def get_zone_coords_js(self):
        """Get JavaScript ZONE_COORDS object"""
        coords_js = "    const ZONE_COORDS = {\n"
        for zone, coords in ZONE_COORD_MAP.items():
            coords_js += f'        "{zone}": [{coords[0]}, {coords[1]}],\n'
        coords_js = coords_js.rstrip(",\n") + "\n    };"
        return coords_js
    
    def calculate_market_stats(self):
        """Calculate statistics about all markets with zones"""
        from generate_map_conflict import CAT_KEYWORDS, all_keywords
        from generate_map_sport import SPORT_KEYWORDS, all_sport_keywords, EXCLUSION_KEYWORDS
        from generate_map_finance import FINANCE_KEYWORDS, all_finance_keywords
        from generate_map_elections import ELECTION_KEYWORDS, all_election_keywords
        from generate_map_technology import TECH_KEYWORDS, all_tech_keywords
        
        conflict_ids = set()
        sport_ids = set()
        finance_ids = set()
        election_ids = set()
        tech_ids = set()
        markets_with_zones = 0
        
        for m in self.markets:
            q = m.get("question", "")
            q_lower = q.lower()
            m_id = m.get("id", "")
            
            found_zones = self.find_zones_in_text(q)
            if not found_zones:
                # Check for default zones (US for elections/fed)
                if any(k in q_lower for k in ["president", "presidential", "senate", "congress", "supreme court"]):
                    found_zones = {"United States": None}
                elif any(k in q_lower for k in ["fed", "federal reserve", "fomc", "jerome powell"]):
                    found_zones = {"United States": None}
                else:
                    continue
            
            markets_with_zones += 1
            
            # Check conflict
            assigned_cat = "Other"
            for cat, keywords in CAT_KEYWORDS.items():
                if any(k in q_lower for k in keywords):
                    assigned_cat = cat
                    break
            if assigned_cat != "Other" or any(k in q_lower for k in all_keywords):
                if len(found_zones) >= 2:
                    conflict_ids.add(m_id)
            
            # Check sport
            if not any(excl in q_lower for excl in EXCLUSION_KEYWORDS):
                assigned_sport_cat = "Other Sports"
                for cat, keywords in SPORT_KEYWORDS.items():
                    if any(k in q_lower for k in keywords):
                        assigned_sport_cat = cat
                        break
                if assigned_sport_cat != "Other Sports" or any(k in q_lower for k in all_sport_keywords):
                    if len(found_zones) >= 1:
                        sport_ids.add(m_id)
            
            # Check finance
            if not any(excl in q_lower for excl in EXCLUSION_KEYWORDS):
                assigned_finance_cat = "Other Financial"
                for cat, keywords in FINANCE_KEYWORDS.items():
                    if any(k in q_lower for k in keywords):
                        assigned_finance_cat = cat
                        break
                if assigned_finance_cat != "Other Financial" or any(k in q_lower for k in all_finance_keywords):
                    if len(found_zones) >= 1 or any(k in q_lower for k in ["fed", "federal reserve", "fomc", "jerome powell"]):
                        finance_ids.add(m_id)
            
            # Check elections
            if not any(excl in q_lower for excl in EXCLUSION_KEYWORDS):
                assigned_election_cat = "Voting"
                for cat, keywords in ELECTION_KEYWORDS.items():
                    if any(k in q_lower for k in keywords):
                        assigned_election_cat = cat
                        break
                if assigned_election_cat != "Voting" or any(k in q_lower for k in all_election_keywords):
                    if len(found_zones) >= 1 or any(k in q_lower for k in ["president", "presidential", "senate", "congress", "supreme court"]):
                        election_ids.add(m_id)
            
            # Check technology
            if not any(excl in q_lower for excl in EXCLUSION_KEYWORDS):
                assigned_tech_cat = "Other Technology"
                for cat, keywords in TECH_KEYWORDS.items():
                    if any(k in q_lower for k in keywords):
                        assigned_tech_cat = cat
                        break
                if assigned_tech_cat != "Other Technology" or any(k in q_lower for k in all_tech_keywords):
                    if len(found_zones) >= 1 or any(k in q_lower for k in ["apple", "google", "microsoft", "meta", "amazon", "nvidia", "tesla", "openai"]):
                        tech_ids.add(m_id)
        
        mapped_count = len(conflict_ids) + len(sport_ids) + len(finance_ids) + len(election_ids) + len(tech_ids)
        unmapped_count = markets_with_zones - mapped_count
        
        return {
            "total": markets_with_zones,
            "conflicts": len(conflict_ids),
            "sports": len(sport_ids),
            "finance": len(finance_ids),
            "elections": len(election_ids),
            "technology": len(tech_ids),
            "unmapped": unmapped_count
        }
    
    def filter_markets(self):
        """Filter markets - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement filter_markets")
    
    def generate_html(self, filtered_data):
        """Generate HTML - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement generate_html")
    
    def run(self):
        """Main execution flow"""
        print("=" * 60)
        print(self.title)
        print("=" * 60)
        print(f"Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
        
        # Step 1: Load markets
        markets = self.load_markets()
        if not markets:
            return
        
        # Step 2: Filter markets
        filtered_data = self.filter_markets()
        if not filtered_data:
            print(f"Error: No markets found")
            return
        
        # Step 3: Generate HTML
        print("\nGenerating HTML map...")
        html_content = self.generate_html(filtered_data)
        
        # Step 4: Save HTML
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"\nDone! Generated {self.output_file} with {len(filtered_data)} markets")
        print(f"Completed at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
