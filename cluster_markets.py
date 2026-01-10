import json
import os
import requests
import numpy as np
from datetime import datetime

def fetch_and_load_markets():
    markets_file = "active_markets.jsonl"
    if not os.path.exists(markets_file):
        print(f"Error: {markets_file} not found. Run fetch_polymarket.py first.")
        return []
    
    markets = []
    with open(markets_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                markets.append(json.loads(line))
            except:
                continue
    return markets

def main():
    print("Loading markets...")
    markets = fetch_and_load_markets()
    if not markets:
        return
    
    print(f"Loaded {len(markets)} markets.")
    
    # Category Keywords
    CAT_KEYWORDS = {
        "Military": ["war", "conflict", "invasion", "invade", "attack", "strike", "missile", "bomb", "blast", "military", "army", "navy", "nuclear", "weapon", "killed", "assassination", "escalation", "idf"],
        "Trade": ["trade", "tariff", "tax", "sanction", "ban", "embargo", "economic", "trade war"],
        "Drugs & Border": ["drug", "fentanyl", "cocaine", "cartel", "smuggling", "trafficking", "border"],
        "Diplomatic": ["ceasefire", "peace", "treaty", "relation", "summit", "deal", "agreement", "talks", "truce", "diplomatic"]
    }
    
    # Combined list for initial check
    all_keywords = []
    for k in CAT_KEYWORDS.values():
        all_keywords.extend(k)

    # 2. Country/Location Dictionary with Canonical Names
    COUNTRY_MAP = {
        "United States": ["united states", "usa", "u.s.", "us", "america", "biden", "trump"],
        "China": ["china", "beijing", "xi"],
        "Taiwan": ["taiwan", "taipei"],
        "Russia": ["russia", "moscow", "putin"],
        "Ukraine": ["ukraine", "kiev", "kyiv", "zelensky"],
        "Israel": ["israel", "jerusalem", "tel aviv", "idf", "netanyahu"],
        "Iran": ["iran", "tehran"],
        "Palestine": ["palestine", "gaza", "hamas", "rafah"],
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
    
    # Flatten for lookup
    COUNTRIES = {}
    for canonical, aliases in COUNTRY_MAP.items():
        # Coordinates for the canonical country (using the first alias as key for coordinates)
        # We need a fixed coord for each canonical name.
        # Let's use a separate coord map.
        pass

    COORD_MAP = {
        "United States": [38.9072, -77.0369], "China": [39.9042, 116.4074], "Taiwan": [25.0330, 121.5654],
        "Russia": [55.7558, 37.6173], "Ukraine": [50.4501, 30.5234], "Israel": [31.7683, 35.2137],
        "Iran": [35.6892, 51.3890], "Palestine": [31.9522, 35.2332], "Lebanon": [33.8938, 35.5018],
        "Yemen": [15.5527, 48.5164], "Syria": [33.5138, 36.2765], "Iraq": [33.3152, 44.3661],
        "North Korea": [39.0392, 125.7625], "South Korea": [37.5665, 126.9780], "Japan": [35.6762, 139.6503],
        "Mexico": [19.4326, -99.1332], "Canada": [45.4215, -75.6972], "UK": [51.5074, -0.1278],
        "France": [48.8566, 2.3522], "Germany": [52.5200, 13.4050], "EU": [50.8503, 4.3517],
        "India": [28.6139, 77.2090], "Pakistan": [33.6844, 73.0479], "Venezuela": [10.4806, -66.9036],
        "Brazil": [-15.8267, -47.9218], "Sudan": [15.5007, 32.5599]
    }

    line_data = []

    print("Filtering and categorizing conflict bets...")

    for m in markets:
        q = m.get("question", "")
        q_lower = q.lower()
        vol = float(m.get("volume", 0) or 0)
        price = float(m.get("lastTradePrice", 0) or 0)
        end_date = m.get("endDate", "")[:10]
        
        assigned_cat = "Other"
        for cat, keywords in CAT_KEYWORDS.items():
            if any(k in q_lower for k in keywords):
                assigned_cat = cat
                break
        
        if assigned_cat == "Other" and not any(k in q_lower for k in all_keywords):
            continue
            
        found_canonical = {}
        for canonical, aliases in COUNTRY_MAP.items():
            for alias in aliases:
                if len(alias) <= 3:
                    pattern = f" {alias} "
                    if pattern in f" {q_lower} " or q_lower.startswith(f"{alias} ") or q_lower.endswith(f" {alias}"):
                         found_canonical[canonical] = COORD_MAP[canonical]
                         break
                else:
                    if alias in q_lower:
                         found_canonical[canonical] = COORD_MAP[canonical]
                         break
        
        unique_names = list(found_canonical.keys())
        unique_coords = list(found_canonical.values())
        
        if len(unique_names) >= 2:
            # Sort country names to match JavaScript grouping
            sorted_names = sorted(unique_names[:2])
            src_name = sorted_names[0]
            tgt_name = sorted_names[1]
            # Use canonical coordinates from COORD_MAP to ensure consistency
            src_coords = COORD_MAP[src_name]
            tgt_coords = COORD_MAP[tgt_name]
            
            # Extract parent event slug if this is a child market
            parent_slug = m.get("slug", "")
            events = m.get("events", [])
            if events and len(events) > 0:
                parent_slug = events[0].get("slug", parent_slug)
            
            line_data.append({
                "id": m.get("id", ""),
                "unique_id": f"L{len(line_data)}", 
                "q": q,
                "price": price,
                "date": end_date,
                "vol": vol,
                "src_lat": src_coords[0],
                "src_lng": src_coords[1],
                "tgt_lat": tgt_coords[0],
                "tgt_lng": tgt_coords[1],
                "cat": assigned_cat,
                "updated": datetime.now().strftime("%H:%M"), 
                "countries": sorted([src_name, tgt_name]),
                "slug": m.get("slug", ""),
                "url": f"https://polymarket.com/event/{parent_slug}",
                "clobTokenIds": m.get("clobTokenIds", "")
            })

    print(f"Found {len(line_data)} conflict bets between countries.")
    
    # Track New Markets
    new_changes = []
    old_ids = set()
    if os.path.exists("conflict_manifest.json"):
        with open("conflict_manifest.json", "r", encoding="utf-8") as f:
            old_data = json.load(f)
            old_ids = {m["id"] for m in old_data if "id" in m}
    
    for l in line_data:
        if l["id"] not in old_ids:
            new_changes.append({
                "time": datetime.now().strftime("%H:%M"),
                "type": "NEW",
                "q": l["q"],
                "change": f"{int(l['price']*100)}%"
            })

    # Update Change Log
    change_log = []
    if os.path.exists("recent_changes.json"):
        with open("recent_changes.json", "r", encoding="utf-8") as f:
            change_log = json.load(f)
    
    change_log = (new_changes + change_log)[:20]
    with open("recent_changes.json", "w", encoding="utf-8") as f:
        json.dump(change_log, f, indent=2)

    # Save manifest for fast updates
    with open("conflict_manifest.json", "w", encoding="utf-8") as f:
        json.dump(line_data, f, indent=2)
    print("Saved manifest to conflict_manifest.json")
    
    html_content = generate_map_html(line_data)
    with open("market_report.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("Done! Saved to market_report.html")

def generate_map_html(lines):
    json_lines = json.dumps(lines)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Global Conflict Map - Polymarket</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
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
        
        .line-tooltip {
            background: rgba(15, 23, 42, 0.98);
            border: 1px solid #475569;
            color: #f1f5f9;
            padding: 10px;
            border-radius: 6px;
            font-size: 13px;
            white-space: nowrap;
            max-width: none;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            pointer-events: auto;
        }

        /* Mobile Optimization */
        @media (max-width: 768px) {
            .info-box, .legend { display: none; } 
            
            /* Mobile Filter Toggle Button */
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
                transform: translateY(110%); /* Hidden by default */
                transition: transform 0.3s ease-in-out;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                margin: 0;
                box-sizing: border-box;
            }
            
            .filter-box.active {
                transform: translateY(0); /* Visible */
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
            
            #country-filters { max-height: 50vh !important; }
            
            .leaflet-control-zoom { display: none; }
            .leaflet-bottom.leaflet-right { display: none; }
        }
        .line-tooltip {
            border: 1px solid #475569;
            background: #0f172a !important;
            color: #f1f5f9 !important;
        }
        .leaflet-popup-content-wrapper, .leaflet-popup-tip {
            background: #0f172a !important;
            color: #f1f5f9 !important;
            border: 1px solid #475569;
        }
        .leaflet-popup-content { margin: 8px 12px; }
        .line-tooltip a { color: #38bdf8; text-decoration: none; font-weight: 500; }
        .line-tooltip a:hover { text-decoration: underline; color: #7dd3fc; }
        .legend-item { display: flex; align-items: center; margin-bottom: 6px; font-size: 0.8rem; }
        .legend-color { width: 24px; height: 3px; border-radius: 2px; margin-right: 12px; }
        hr { border: 0; border-top: 1px solid #334155; margin: 12px 0; }
    </style>
</head>
<body>

<div id="map"></div>
<button id="mobile-filter-btn" style="display:none;" onclick="document.querySelector('.filter-box').classList.toggle('active')">
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"></line><line x1="4" y1="10" x2="4" y2="3"></line><line x1="12" y1="21" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="3"></line><line x1="20" y1="21" x2="20" y2="16"></line><line x1="20" y1="12" x2="20" y2="3"></line><line x1="1" y1="14" x2="7" y2="14"></line><line x1="9" y1="8" x2="15" y2="8"></line><line x1="17" y1="16" x2="23" y2="16"></line></svg>
    Filters
</button>

<button id="mobile-filter-btn" style="display:none;" onclick="document.querySelector('.filter-box').classList.toggle('active')">
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"></line><line x1="4" y1="10" x2="4" y2="3"></line><line x1="12" y1="21" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="3"></line><line x1="20" y1="21" x2="20" y2="16"></line><line x1="20" y1="12" x2="20" y2="3"></line><line x1="1" y1="14" x2="7" y2="14"></line><line x1="9" y1="8" x2="15" y2="8"></line><line x1="17" y1="16" x2="23" y2="16"></line></svg>
    Filters
</button>

<div class="filter-box">
    <div class="close-filter" style="display:none;" onclick="document.querySelector('.filter-box').classList.remove('active')">&times;</div>
    <h1>Select Conflicts</h1>
    <div class="filter-item"><input type="checkbox" id="Military" checked onchange="updateCountryCounts(); updateVisibility()"> <label for="Military">Military</label></div>
    <div class="filter-item"><input type="checkbox" id="Trade" checked onchange="updateCountryCounts(); updateVisibility()"> <label for="Trade">Trade</label></div>
    <div class="filter-item"><input type="checkbox" id="Drugs & Border" checked onchange="updateCountryCounts(); updateVisibility()"> <label for="Drugs & Border">Drugs & Border</label></div>
    <div class="filter-item"><input type="checkbox" id="Diplomatic" checked onchange="updateCountryCounts(); updateVisibility()"> <label for="Diplomatic">Diplomatic</label></div>
    
    <hr style="margin: 10px 0;">
    <h1 style="margin-bottom: 8px;">Choose Country</h1>
    <div id="country-filters" style="max-height: 200px; overflow-y: auto;">
        COUNTRY_FILTERS_PLACEHOLDER
    </div>
</div>

<div class="info-box">
    <h1 style="font-size: 1.2rem;">Conflict Prediction Map</h1>
    <p id="stats-text">Loading...</p>
    <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #334155; font-size: 0.75rem; color: #64748b;">
        <div style="margin-bottom: 4px; color: #e2e8f0; font-weight: 600;">Last Updated: LAST_UPDATE_PLACEHOLDER</div>
        Arcs are offset by date. Arrows indicate directed action.
    </div>
</div>

<div class="legend">
    <h1>Market Odds</h1>
    <div class="legend-item"><div class="legend-color" style="background:#22c55e"></div>High ( > 70%)</div>
    <div class="legend-item"><div class="legend-color" style="background:#eab308"></div>Medium (40-70%)</div>
    <div class="legend-item"><div class="legend-color" style="background:#f97316"></div>Low (10-40%)</div>
    <div class="legend-item"><div class="legend-color" style="background:#ef4444"></div>Remote ( < 10%)</div>
</div>

</div>


<script>
    const map = L.map('map', {
        zoomControl: false,
        attributionControl: false
    }).setView([32, 35], 5); 

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 20 }).addTo(map);

    const linesData = JSON_LINES_PLACEHOLDER;
    const layers = {}; 
    const markers = [];

    function getProbColor(p) {
        if (p >= 0.70) return '#22c55e';
        if (p >= 0.40) return '#eab308';
        if (p >= 0.10) return '#f97316';
        return '#ef4444';
    }
    
    // Country coordinates for map focusing
    const COUNTRY_COORDS = {
        "Brazil": [-15.8267, -47.9218],
        "Canada": [45.4215, -75.6972],
        "China": [39.9042, 116.4074],
        "EU": [50.8503, 4.3517],
        "India": [28.6139, 77.209],
        "Iran": [35.6892, 51.389],
        "Iraq": [33.3152, 44.3661],
        "Israel": [31.7683, 35.2137],
        "Japan": [35.6762, 139.6503],
        "Lebanon": [33.8938, 35.5018],
        "Mexico": [19.4326, -99.1332],
        "North Korea": [39.0392, 125.7625],
        "Pakistan": [33.6844, 73.0479],
        "Palestine": [31.9522, 35.2332],
        "Russia": [55.7558, 37.6173],
        "South Korea": [37.5665, 126.978],
        "Syria": [33.5138, 36.2765],
        "Taiwan": [25.033, 121.5654],
        "UK": [51.5074, -0.1278],
        "Ukraine": [50.4501, 30.5234],
        "United States": [38.9072, -77.0369],
        "Venezuela": [10.4806, -66.9036],
        "Yemen": [15.5527, 48.5164]
    };
    
    function onCountryChange(countryName) {
        // Focus map on selected country
        const coords = COUNTRY_COORDS[countryName];
        if (coords) {
            map.setView(coords, 5, { animate: true, duration: 0.5 });
        }
        updateVisibility();
    }

    function addArrowhead(map, latlngs, color, layerGroup) {
        if (latlngs.length < 2) return;
        const p1 = latlngs[latlngs.length - 2];
        const p2 = latlngs[latlngs.length - 1];
        const angle = Math.atan2(p2[0] - p1[0], p2[1] - p1[1]) * 180 / Math.PI;
        const arrowSvg = `<svg viewBox="0 0 10 10" width="12" height="12" style="transform: rotate(${90 - angle}deg)"><path d="M 0 0 L 10 5 L 0 10 z" fill="${color}" /></svg>`;
        const icon = L.divIcon({ className: 'custom-arrowhead', html: arrowSvg, iconSize: [12, 12], iconAnchor: [6, 6] });
        L.marker(p2, { icon: icon, interactive: false }).addTo(layerGroup);
    }

    function updateCountryCounts() {
        const selectedCats = Array.from(document.querySelectorAll('.filter-box input[type="checkbox"]:not(.country-radio)')).filter(i => i.checked).map(i => i.id);
        
        // Count markets and total volume per country for selected categories
        const countryCounts = {};
        const countryVolumes = {};
        linesData.forEach(market => {
            if (selectedCats.includes(market.cat)) {
                market.countries.forEach(country => {
                    countryCounts[country] = (countryCounts[country] || 0) + 1;
                    countryVolumes[country] = (countryVolumes[country] || 0) + (market.vol || 0);
                });
            }
        });
        
        // Format volume display
        function formatVol(vol) {
            if (vol >= 1000000) return '$' + (vol / 1000000).toFixed(1) + 'M';
            if (vol >= 1000) return '$' + (vol / 1000).toFixed(0) + 'K';
            return '$' + Math.round(vol);
        }
        
        // Update each country label
        document.querySelectorAll('.country-radio').forEach(radio => {
            const country = radio.getAttribute('data-country');
            const count = countryCounts[country] || 0;
            const volume = countryVolumes[country] || 0;
            const label = document.querySelector(`label[for='${radio.id}']`);
            if (label) {
                label.textContent = `${country} (${count}) - ${formatVol(volume)}`;
            }
        });
    }

    function updateVisibility() {
        const selectedCats = Array.from(document.querySelectorAll('.filter-box input[type="checkbox"]:not(.country-radio)')).filter(i => i.checked).map(i => i.id);
        const selectedRadio = document.querySelector('.country-radio:checked');
        const selectedCountries = selectedRadio ? [selectedRadio.getAttribute('data-country')] : [];

        let visibleCount = 0;
        for (const pairKey in groupLayers) {
            const group = marketGroups[pairKey];
            
            // Check if this arc's endpoints match the selected country filters
            const arcEndpoints = group.pair; // These are the two countries this arc connects
            const arcMatchesFilter = arcEndpoints.some(country => selectedCountries.includes(country));
            
            if (!arcMatchesFilter) {
                // If neither endpoint matches selected countries, hide this arc entirely
                const layerGroup = groupLayers[pairKey];
                if (map.hasLayer(layerGroup)) map.removeLayer(layerGroup);
                continue;
            }
            
            const visibleMarkets = group.markets.filter(m => 
                selectedCats.includes(m.cat) && m.countries.some(c => selectedCountries.includes(c))
            );

            // Sort by date ascending
            visibleMarkets.sort((a, b) => a.date.localeCompare(b.date));

            const layerGroup = groupLayers[pairKey];
            if (visibleMarkets.length > 0) {
                if (!map.hasLayer(layerGroup)) map.addLayer(layerGroup);
                visibleCount += visibleMarkets.length;
                
                // Update line color based on max probability of VISIBLE markets
                const maxProb = Math.max(...visibleMarkets.map(m => m.price));
                const newColor = getProbColor(maxProb);
                group.polyline.setStyle({ color: newColor });
                group.hitbox.setStyle({ color: 'transparent' }); 

                let tooltipHtml = `<div class="line-tooltip"><div style="font-weight:700; color:white; margin-bottom:6px; border-bottom:1px solid #475569; padding-bottom:4px;">${group.pair[0]} & ${group.pair[1]}</div>`;
                // Group by category
                const groups = {};
                visibleMarkets.forEach(m => {
                    if (!groups[m.cat]) groups[m.cat] = [];
                    groups[m.cat].push(m);
                });

                function getBaseTopic(slug, q) {
                    if (!slug) return q;
                    let base = slug.replace(/-\d+$/, '');
                    const preps = "on|by|before|in|at|during|through|after";
                    const months = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december";
                    
                    // Match prepositions followed by months or dates or years
                    base = base.replace(new RegExp(`-(${preps})-(${months}|\\d{1,2}|\\d{4})(-(\\d{1,2}|\\d{4}))?(-.*)?$`, "i"), '');
                    
                    // Catch trailing dates like -jan-10, -2025, -jan-2025, -10-jan
                    base = base.replace(new RegExp(`-(${months})(-(\\d{1,2}|\\d{4}))?(-(\\d{4}))?$`, "i"), '');
                    base = base.replace(new RegExp(`-(\\d{1,2})-(${months})(-.*)?$`, "i"), '');
                    base = base.replace(/-(2024|2025|2026|2027|2028)$/, '');
                    
                    // Final cleanup
                    base = base.replace(/^will-/, '').replace(/-?any-?$/, '').replace(/-?daily-?$/, '').replace(/-?weekly-?$/, '');
                    return base.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                }

                Object.keys(groups).sort().forEach((cat, idx) => {
                    if (idx > 0) tooltipHtml += `<div style="color:#475569; margin: 6px 0;">----------------------------------------------------------------------------------------------------</div>`;
                    tooltipHtml += `<div style="font-weight:800; color:#fbbf24; margin-bottom:6px; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em;">${cat}</div>`;
                    
                    // Group by topic within category
                    const topics = {};
                    groups[cat].forEach(m => {
                        const topic = getBaseTopic(m.slug, m.q);
                        if (!topics[topic]) topics[topic] = [];
                        topics[topic].push(m);
                    });

                    Object.keys(topics).forEach(topic => {
                        tooltipHtml += `<div style="font-weight:700; color:#cbd5e1; margin-top:4px; margin-bottom:2px;">${topic}</div>`;
                        topics[topic].forEach(m => {
                            const color = getProbColor(m.price);
                            const volStr = m.vol >= 1000 ? (m.vol / 1000).toFixed(1) + 'k' : Math.round(m.vol);
                            const polyLink = m.url || `https://polymarket.com/event/${m.slug}`;
                            tooltipHtml += `<div style="margin-bottom:2px; font-size: 0.8rem; padding-left: 10px;">
                                <span style="font-weight:700; color:#94a3b8;">[${m.date}]</span> 
                                <span style="font-weight:700; color:#64748b; margin-left:2px;">[${m.updated}]</span> 
                                <span style="font-weight:700; color:#94a3b8;">[Vol: $${volStr}]</span> 
                                <a href="${polyLink}" target="_blank" style="margin-left:5px; margin-right:5px;">${m.q}</a>
                                <span style="color:${color}; font-weight:800;">${Math.round(m.price * 100)}%</span>
                            </div>`;
                        });
                    });
                });
                tooltipHtml += `</div>`;
                group.content = tooltipHtml;
            } else {
                if (map.hasLayer(layerGroup)) map.removeLayer(layerGroup);
            }
        }
        document.getElementById('stats-text').innerText = `Visualizing ${visibleCount} conflict bets.`;
    }

    function setAllCountries(val) {
        document.querySelectorAll('.country-check').forEach(i => i.checked = val);
        updateVisibility();
    }

    const groupLayers = {}; 
    const marketGroups = {};

    try {
        linesData.forEach(l => {
            const pair = l.countries.sort();
            const pairKey = pair.join("-");
            if (!marketGroups[pairKey]) {
                // Use COUNTRY_COORDS to get canonical coordinates for each country
                const srcCoords = COUNTRY_COORDS[pair[0]] || [l.src_lat, l.src_lng];
                const tgtCoords = COUNTRY_COORDS[pair[1]] || [l.tgt_lat, l.tgt_lng];
                
                marketGroups[pairKey] = {
                    pair: pair,
                    src_coords: srcCoords,
                    tgt_coords: tgtCoords,
                    markets: []
                };
            }
            marketGroups[pairKey].markets.push(l);
        });

        for (const pairKey in marketGroups) {
            const group = marketGroups[pairKey];
            const itemGroup = L.layerGroup(); // Not added to map yet, updateVisibility will handle it
            groupLayers[pairKey] = itemGroup;

            const lat1 = group.src_coords[0], lng1 = group.src_coords[1];
            const lat2 = group.tgt_coords[0], lng2 = group.tgt_coords[1];
            
            const offsetX = (lng2 - lng1) / 2, offsetY = (lat2 - lat1) / 2;
            const baseDist = Math.sqrt(Math.pow(lng2-lng1, 2) + Math.pow(lat2-lat1, 2));
            const hump = (baseDist * 0.2); 
            const cpLat = lat1 + offsetY + (hump * (lat2 > lat1 ? 1 : -1));
            const cpLng = lng1 + offsetX + (hump * (lng2 > lng1 ? -0.5 : 0.5));
            
            const latlngs = [];
            for (let t = 0; t <= 1; t += 0.05) {
                const lat = (1-t)*(1-t)*lat1 + 2*(1-t)*t*cpLat + t*t*lat2;
                const lng = (1-t)*(1-t)*lng1 + 2*(1-t)*t*cpLng + t*t*lng2;
                latlngs.push([lat, lng]);
            }

            const maxProb = Math.max(...group.markets.map(m => m.price));
            const color = getProbColor(maxProb);
            
            const polyline = L.polyline(latlngs, { 
                color: color, 
                weight: 4, 
                opacity: 0.9, 
                lineCap: 'round',
                interactive: false
            }).addTo(itemGroup);
            
            const hitbox = L.polyline(latlngs, {
                color: 'transparent',
                weight: 25,
                opacity: 0,
                lineCap: 'round',
                interactive: true
            }).addTo(itemGroup);
            
            group.polyline = polyline;
            group.hitbox = hitbox;

            hitbox.bindPopup("", { 
                closeButton: false,
                autoClose: false,
                className: 'line-popup',
                minWidth: 400,
                maxWidth: 2000,
                offset: [0, -10]
            });

            let popupTimeout;
            hitbox.on('mouseover', function(e) {
                clearTimeout(popupTimeout);
                if (group.content) {
                    this.setPopupContent(group.content);
                    this.openPopup(e.latlng);
                }
            });

            hitbox.on('mouseout', function(e) {
                popupTimeout = setTimeout(() => {
                    this.closePopup();
                }, 400); 
            });
            
            hitbox.on('popupopen', function(e) {
                const popupEl = e.popup.getElement();
                if (popupEl) {
                    popupEl.addEventListener('mouseenter', () => clearTimeout(popupTimeout));
                    popupEl.addEventListener('mouseleave', () => {
                        popupTimeout = setTimeout(() => {
                            this.closePopup();
                        }, 400);
                    });
                }
            });
            
            L.circleMarker([lat1, lng1], { radius: 3, color: '#94a3b8', fill: true, fillOpacity: 0.6, interactive: false }).addTo(itemGroup);
            L.circleMarker([lat2, lng2], { radius: 3, color: '#94a3b8', fill: true, fillOpacity: 0.6, interactive: false }).addTo(itemGroup);
        }
        updateCountryCounts();
        updateVisibility();
    } catch (err) { console.error(err); }
</script>
</body>
</html>
"""
    # Load country filters with counts
    all_countries = {}
    for l in lines:
        for c in l["countries"]:
            all_countries[c] = all_countries.get(c, 0) + 1
    
    country_checks = ""
    for c in sorted(all_countries.keys(), key=lambda x: all_countries[x], reverse=True):
        safe_id = c.replace(" ", "_").replace(".", "")
        checked = "checked" if c == "Israel" else ""
        count = all_countries[c]
        country_checks += f"<div class='filter-item'><input type='radio' name='country' class='country-radio' id='{safe_id}' data-country='{c}' {checked} onchange='onCountryChange(\"{c}\")'> <label for='{safe_id}'>{c} ({count})</label></div>"

    return html_template.replace("JSON_LINES_PLACEHOLDER", json_lines).replace("LAST_UPDATE_PLACEHOLDER", now_str).replace("COUNTRY_FILTERS_PLACEHOLDER", country_checks)

if __name__ == "__main__":
    main()
