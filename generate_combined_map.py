#!/usr/bin/env python3
"""
Generate combined HTML map with selector to switch between all map types
"""
import json
import os
from datetime import datetime, timezone
from map_base import MapGeneratorBase, ZONE_COORD_MAP

def load_config():
    """Load map configurations from JSON"""
    config_path = os.path.join(os.path.dirname(__file__), "map_configs.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def filter_markets_for_type(map_type, config, markets):
    """Filter markets for a specific map type"""
    all_keywords = []
    for keywords_list in config["keywords"].values():
        all_keywords.extend(keywords_list)
    
    event_data = []
    
    for m in markets:
        q = m.get("question", "")
        q_lower = q.lower()
        vol = float(m.get("volume", 0) or 0)
        price = float(m.get("lastTradePrice", 0) or 0)
        end_date = m.get("endDate", "")[:10]
        
        # Check exclusion keywords
        if config["exclusion_keywords"]:
            if any(excl in q_lower for excl in config["exclusion_keywords"]):
                continue
        
        # Find matching category
        assigned_cat = None
        for cat, keywords in config["keywords"].items():
            if any(k in q_lower for k in keywords):
                assigned_cat = cat
                break
        
        # If no category match and no general keywords match, skip
        if assigned_cat is None and not any(k in q_lower for k in all_keywords):
            continue
        
        # Use first category if none assigned but keywords match
        if assigned_cat is None:
            assigned_cat = list(config["keywords"].keys())[0]
        
        # Find zones
        generator = MapGeneratorBase("Temp", "temp.html")
        found_zones = generator.find_zones_in_text(q)
        
        # Check default zone
        if not found_zones and config["default_zone"]:
            if config["default_zone_keywords"]:
                if any(k in q_lower for k in config["default_zone_keywords"]):
                    found_zones = {config["default_zone"]: None}
            else:
                found_zones = {config["default_zone"]: None}
        
        if not found_zones:
            continue
        
        # Check minimum zones requirement
        if len(found_zones) < config["min_zones"]:
            continue
        
        # Use first zone for marker location
        zone_name = list(found_zones.keys())[0]
        coords = ZONE_COORD_MAP[zone_name]
        
        parent_slug = m.get("slug", "")
        events = m.get("events", [])
        if events and len(events) > 0:
            parent_slug = events[0].get("slug", parent_slug)
        
        event_data.append({
            "id": m.get("id", ""),
            "q": q,
            "price": price,
            "date": end_date,
            "vol": vol,
            "lat": coords[0],
            "lng": coords[1],
            "zone": zone_name,
            "cat": assigned_cat,
            "slug": m.get("slug", ""),
            "url": f"https://polymarket.com/event/{parent_slug}",
        })
    
    return event_data

def generate_combined_html():
    """Generate single HTML file with all map types"""
    config_data = load_config()
    generator = MapGeneratorBase("Combined Map Generator", "combined_map.html")
    markets = generator.load_markets()
    
    if not markets:
        print("No markets loaded")
        return
    
    print("Filtering markets for all map types...")
    
    # Filter markets for each map type
    all_map_data = {}
    for map_type, config in config_data["maps"].items():
        print(f"  Processing {map_type}...")
        event_data = filter_markets_for_type(map_type, config, markets)
        all_map_data[map_type] = {
            "config": config,
            "events": event_data
        }
        print(f"    Found {len(event_data)} events")
    
    # Get base HTML components - include both Leaflet and Three.js
    html_head = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Combined Map Generator - Polymarket</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
        }}
        #map {{ 
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            height: 100vh !important;
            z-index: 1 !important;
            background: #0f172a !important;
            display: block !important;
            visibility: visible !important;
        }}
        .leaflet-container {{
            background: #0f172a !important;
            height: 100vh !important;
            width: 100% !important;
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            z-index: 1 !important;
        }}
        .leaflet-map-pane {{
            width: 100% !important;
            height: 100% !important;
        }}
        .leaflet-tile-pane {{
            z-index: 2 !important;
        }}
        .leaflet-overlay-pane {{
            z-index: 3 !important;
        }}
        .tooltip-overlay {{
            position: fixed;
            background: rgba(15, 23, 42, 0.98);
            border: 1px solid #475569;
            color: #f1f5f9;
            padding: 10px;
            border-radius: 6px;
            font-size: 13px;
            max-width: 800px;
            min-width: 600px;
            z-index: 10000;
            pointer-events: auto;
            display: none;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        }}
    </style>"""
    
    css = generator.get_common_css()
    analytics_code = generator.get_analytics_code()
    zone_coords_js = generator.get_zone_coords_js()
    
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    # Helper function to format volume
    def format_vol(vol):
        if vol >= 1000000:
            return f"${vol/1000000:.1f}M"
        elif vol >= 1000:
            return f"${vol/1000:.0f}K"
        else:
            return f"${int(vol)}"
    
    # Calculate totals for map types
    map_type_totals = {}
    for map_type, map_info in all_map_data.items():
        events = map_info["events"]
        total_events = len(events)
        total_volume = sum(e.get("vol", 0) for e in events)
        map_type_totals[map_type] = {"events": total_events, "volume": total_volume}
    
    # Generate map selector
    map_selector = '<select id="map-type-selector" onchange="switchMapType(this.value)" style="padding: 6px 10px; background: #1e293b; color: #e2e8f0; border: 1px solid #475569; border-radius: 6px; font-size: 0.85rem; font-weight: 600; cursor: pointer; margin-bottom: 12px;">\n'
    for map_type, map_info in all_map_data.items():
        config = map_info["config"]
        selected = 'selected' if map_type == 'conflict' else ''
        totals = map_type_totals[map_type]
        map_selector += f'        <option value="{map_type}" {selected}>{config["icon"]} {config["name"]} ({totals["events"]} events, {format_vol(totals["volume"])})</option>\n'
    map_selector += '    </select>'
    
    # Generate category filters for each map type (will be shown/hidden)
    category_filters_html = ""
    for map_type, map_info in all_map_data.items():
        config = map_info["config"]
        events = map_info["events"]
        category_checks = ""
        
        # Calculate totals for each category
        category_totals = {}
        for event in events:
            cat = event.get("cat", "")
            if cat:
                if cat not in category_totals:
                    category_totals[cat] = {"events": 0, "volume": 0}
                category_totals[cat]["events"] += 1
                category_totals[cat]["volume"] += event.get("vol", 0)
        
        for cat in config["keywords"].keys():
            safe_id = cat.replace(" ", "_").replace("&", "")
            totals = category_totals.get(cat, {"events": 0, "volume": 0})
            category_checks += f'<div class="filter-item"><input type="checkbox" id="{map_type}_{safe_id}" checked onchange="updateZoneCounts(); updateVisibility()"> <label for="{map_type}_{safe_id}">{cat} <span style="color: #94a3b8; font-size: 0.85rem;">({totals["events"]} events, {format_vol(totals["volume"])})</span></label></div>'
        
        # All categories start hidden, JavaScript will show the selected one
        category_filters_html += f'<div id="category-filters-{map_type}" class="category-filters" style="display: none;">\n{category_checks}\n</div>\n'
    
    # CSS
    combined_css = """
        #map {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            height: 100vh !important;
            z-index: 1 !important;
            background: #0f172a !important;
            display: block !important;
            visibility: visible !important;
        }
        .filter-box h1 {
            font-size: 0.85rem !important;
        }
        .filter-box .filter-item label {
            font-size: 0.8rem !important;
        }
        #map-type-selector {
            font-size: 0.85rem !important;
        }
        .map-icon {
            font-size: 24px;
            cursor: pointer;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
        }
        .line-tooltip {
            background: rgba(15, 23, 42, 0.98);
            border: 1px solid #475569;
            color: #f1f5f9;
            padding: 10px;
            border-radius: 6px;
            font-size: 13px;
            max-width: none;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            pointer-events: auto;
        }
        .leaflet-popup-content-wrapper, .leaflet-popup-tip {
            background: #0f172a !important;
            color: #f1f5f9 !important;
            border: 1px solid #475569;
        }
        .leaflet-popup-content { margin: 8px 12px; }
        .line-tooltip a { color: #38bdf8; text-decoration: none; font-weight: 500; }
        .line-tooltip a:hover { text-decoration: underline; color: #7dd3fc; }
        
        .snapshot-btn {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            margin-top: 8px;
            width: 100%;
            transition: background 0.2s;
        }
        .snapshot-btn:hover {
            background: #2563eb;
        }
        .tooltip-tabs {
            display: flex;
            gap: 4px;
            margin-bottom: 10px;
            border-bottom: 1px solid #475569;
            flex-wrap: wrap;
        }
        .tooltip-tab {
            padding: 6px 12px;
            background: #1e293b;
            color: #94a3b8;
            border: 1px solid #475569;
            border-bottom: none;
            border-radius: 4px 4px 0 0;
            cursor: pointer;
            font-size: 0.75rem;
            font-weight: 600;
            transition: all 0.2s;
            white-space: nowrap;
        }
        .tooltip-tab:hover {
            background: #334155;
            color: #cbd5e1;
        }
        .tooltip-tab.active {
            background: #0f172a;
            border-color: #475569;
            border-bottom-color: #0f172a;
        }
        .tooltip-tab-content {
            display: none;
            min-height: 400px;
            max-height: 500px;
            overflow-y: auto;
        }
        .tooltip-tab-content.active {
            display: block;
        }
        .line-popup {
            width: 600px !important;
            max-width: 600px !important;
            min-width: 600px !important;
        }
        .line-popup .leaflet-popup-content {
            width: 600px !important;
            max-width: 600px !important;
            min-width: 600px !important;
            min-height: 450px !important;
            max-height: 500px !important;
        }
        .line-popup .line-tooltip {
            width: 100% !important;
            min-height: 450px !important;
        }
        #zone-filters { max-height: 200px; overflow-y: auto; }
        .selected-zone-icon {
            z-index: 1000;
        }
        .map-icon {
            transition: opacity 0.3s;
        }
        .info-box {
            left: 50%;
            transform: translateX(-50%);
            max-width: 90%;
            width: auto;
            display: flex;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
            justify-content: center;
        }
        .info-box > h1 {
            margin: 0;
            white-space: nowrap;
        }
        .info-box > p {
            margin: 0;
            white-space: nowrap;
        }
        .info-box > div {
            margin: 0;
            padding: 0;
            border: none;
            background: transparent;
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: nowrap;
        }
        .info-box > div > div {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }
        #map-type-selector {
            width: 100%;
        }
        """
    
    css_with_combined = css.replace("    </style>", combined_css + "    </style>")
    
    # Embed all map data as JSON
    all_map_data_json = json.dumps(all_map_data, default=str)
    
    html_template = html_head + css_with_combined + analytics_code + f"""
</head>
<body>

<div id="map"></div>
<button id="mobile-filter-btn" style="display:none;" onclick="document.querySelector('.filter-box').classList.toggle('active')">
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"></line><line x1="4" y1="10" x2="4" y2="3"></line><line x1="12" y1="21" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="3"></line><line x1="20" y1="21" x2="20" y2="16"></line><line x1="20" y1="12" x2="20" y2="3"></line><line x1="1" y1="14" x2="7" y2="14"></line><line x1="9" y1="8" x2="15" y2="8"></line><line x1="17" y1="16" x2="23" y2="16"></line></svg>
    Filters
</button>

<div class="filter-box">
    <div class="close-filter" style="display:none;" onclick="document.querySelector('.filter-box').classList.remove('active')">&times;</div>
    <div style="font-size: 0.7rem; color: #64748b; padding: 6px; background: rgba(59, 130, 246, 0.1); border-radius: 6px; border-left: 3px solid #3b82f6; margin-bottom: 10px; display: flex; align-items: center; gap: 6px;">
        <span style="color: #94a3b8;">Last Updated:</span>
        <span style="color: #3b82f6; font-weight: 700;">{current_time} UTC</span>
    </div>
    <h1>Map Type</h1>
    {map_selector}
    
    <hr style="margin: 10px 0;">
    <h1>Categories</h1>
    {category_filters_html}
    
    <hr style="margin: 10px 0;">
    <h1 style="margin-bottom: 8px;">Zones</h1>
    <div id="zone-filters" style="max-height: 200px; overflow-y: auto;">
        ZONE_FILTERS_PLACEHOLDER
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
    const allMapData = ALL_MAP_DATA_PLACEHOLDER;
    let currentMapType = 'conflict';
    let map = null;
    
    // Initialize Leaflet Map
    function initMap() {{
        if (map) {{
            // Map already exists, just make sure it's visible
            const mapContainer = document.getElementById('map');
            if (mapContainer) {{
                mapContainer.style.display = 'block';
                mapContainer.style.visibility = 'visible';
                mapContainer.style.opacity = '1';
            }}
            if (map) {{
                setTimeout(() => {{
                    map.invalidateSize();
                }}, 100);
            }}
            return;
        }}
        
        const mapContainer = document.getElementById('map');
        if (!mapContainer) {{
            console.error('Map container not found');
            return;
        }}
        
        // Ensure container is visible and has dimensions
        mapContainer.style.display = 'block';
        mapContainer.style.visibility = 'visible';
        mapContainer.style.opacity = '1';
        mapContainer.style.position = 'fixed';
        mapContainer.style.top = '0';
        mapContainer.style.left = '0';
        mapContainer.style.width = '100%';
        mapContainer.style.height = '100vh';
        mapContainer.style.zIndex = '1';
        mapContainer.style.background = '#0f172a';
        
        // Wait a moment to ensure container is rendered
        setTimeout(() => {{
            try {{
                map = L.map('map', {{
                    zoomControl: true,
                    attributionControl: false,
                    minZoom: 2,
                    maxZoom: 18,
                    worldCopyJump: false,
                    dragging: true,
                    touchZoom: true,
                    doubleClickZoom: true,
                    scrollWheelZoom: true,
                    boxZoom: true,
                    keyboard: true
                }}).setView([20, 0], 2);

                // Add tile layer with error handling
                const tileLayer = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                    maxZoom: 18,
                    noWrap: true,
                    subdomains: 'abcd',
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                }});
                
                tileLayer.addTo(map);
                
                // Force map to recalculate size after a short delay
                setTimeout(() => {{
                    if (map) {{
                        map.invalidateSize();
                        console.log('Map size invalidated');
                    }}
                }}, 200);
                
                // Allow free map movement - no restrictions
                
                console.log('Map initialized successfully');
            }} catch (error) {{
                console.error('Error initializing map:', error);
                alert('Failed to initialize map. Error: ' + error.message);
            }}
        }}, 50);
    }}
    
    const markers = [];
    
    // Initialize map on page load
    window.addEventListener('load', function() {{
        const mapContainer = document.getElementById('map');
        
        // Ensure container is properly styled
        if (mapContainer) {{
            mapContainer.style.display = 'block';
            mapContainer.style.visibility = 'visible';
            mapContainer.style.opacity = '1';
            mapContainer.style.position = 'fixed';
            mapContainer.style.top = '0';
            mapContainer.style.left = '0';
            mapContainer.style.width = '100%';
            mapContainer.style.height = '100vh';
            mapContainer.style.zIndex = '1';
            mapContainer.style.background = '#0f172a';
        }}
        
        // Initialize map after a short delay to ensure DOM is ready
        setTimeout(() => {{
            initMap();
            
            // Initialize map type and show markers after map is ready
            setTimeout(() => {{
                if (map) {{
                    // Force map to recalculate size
                    map.invalidateSize();
                    // Try again after a short delay
                    setTimeout(() => {{
                        map.invalidateSize();
                        switchMapType('conflict');
                        updateZoneCounts();
                    }}, 200);
                }} else {{
                    console.error('Map not initialized');
                    // Retry initialization
                    setTimeout(() => {{
                        initMap();
                        if (map) {{
                            map.invalidateSize();
                            switchMapType('conflict');
                            updateZoneCounts();
                        }}
                    }}, 500);
                }}
            }}, 300);
        }}, 100);
    }});

    function getProbColor(p) {{
        if (p >= 0.70) return '#22c55e';
        if (p >= 0.40) return '#eab308';
        if (p >= 0.10) return '#f97316';
        return '#ef4444';
    }}
    
    {zone_coords_js}
    
    function switchMapType(mapType) {{
        currentMapType = mapType;
        const mapInfo = allMapData[mapType];
        if (!mapInfo) return;

        const config = mapInfo.config;

        // Clear any selected zone from previous map type
        document.querySelectorAll('.zone-radio').forEach(radio => {{
            radio.checked = false;
        }});

        // Show/hide category filters for current map type - hide all first
        document.querySelectorAll('.category-filters').forEach(div => {{
            div.style.display = 'none';
            div.style.visibility = 'hidden';
        }});
        // Show only the current map type's categories
        const currentCategoryFilters = document.getElementById(`category-filters-${{mapType}}`);
        if (currentCategoryFilters) {{
            currentCategoryFilters.style.display = 'block';
            currentCategoryFilters.style.visibility = 'visible';
        }} else {{
            console.warn('Category filters not found for:', mapType);
        }}

        // Update zone filters (this will regenerate zone list for new map type)
        updateZoneFilters(mapType);
        
        // Update visibility - this will show markers for all zones (no zone selected)
        updateVisibility();
    }}
    
    function updateZoneFilters(mapType) {{
        const mapInfo = allMapData[mapType];
        if (!mapInfo) return;
        
        const events = mapInfo.events;
        const all_zones = {{}};
        const zone_volumes = {{}};
        
        events.forEach(e => {{
            const zone = e.zone;
            all_zones[zone] = (all_zones[zone] || 0) + 1;
            zone_volumes[zone] = (zone_volumes[zone] || 0) + (e.vol || 0);
        }});
        
        function formatVol(vol) {{
            if (vol >= 1000000) return '$' + (vol / 1000000).toFixed(1) + 'M';
            if (vol >= 1000) return '$' + (vol / 1000).toFixed(0) + 'K';
            return '$' + Math.round(vol);
        }}
        
        const zoneFiltersDiv = document.getElementById('zone-filters');
        zoneFiltersDiv.innerHTML = '';
        
        const sortedZones = Object.keys(all_zones).sort((a, b) => zone_volumes[b] - zone_volumes[a]);
        sortedZones.forEach((z, idx) => {{
            const safe_id = z.replace(/ /g, '_').replace(/\\./g, '');
            const checked = ''; // Don't auto-select any zone
            const count = all_zones[z];
            const volume = zone_volumes[z] || 0;
            const radio = document.createElement('div');
            radio.className = 'filter-item';
            radio.innerHTML = `<input type="radio" name="zone" class="zone-radio" id="zone_${{safe_id}}" data-zone="${{z}}" ${{checked}} onchange="onZoneChange('${{z}}')" onclick="onZoneChange('${{z}}')"> <label for="zone_${{safe_id}}" onclick="document.getElementById('zone_${{safe_id}}').click();">${{z}} <span style="color: #94a3b8; font-size: 0.85rem;">(${{count}} events, ${{formatVol(volume)}})</span></label>`;
            zoneFiltersDiv.appendChild(radio);
        }});
    }}
    
    function onZoneChange(zoneName) {{
        // Ensure radio button is checked
        const safe_id = zoneName.replace(/ /g, '_').replace(/\\./g, '');
        const radio = document.getElementById(`zone_${{safe_id}}`);
        if (radio && !radio.checked) {{
            radio.checked = true;
        }}
        
        // Don't move the map - just update visibility and show tooltip
        updateVisibility();
        
        // After visibility updates, show tooltip for selected zone marker
        // Try multiple times with increasing delays to ensure marker is ready
        function tryOpenTooltip(attempt = 0) {{
            const selectedMarker = markers.find(m => m.zoneName === zoneName);
            if (selectedMarker && selectedMarker.tooltipHtml) {{
                selectedMarker.setPopupContent(selectedMarker.tooltipHtml);
                selectedMarker.openPopup(selectedMarker.getLatLng());
                console.log('Tooltip opened for zone:', zoneName);
            }} else if (attempt < 5) {{
                // Retry up to 5 times
                setTimeout(() => tryOpenTooltip(attempt + 1), 200);
            }} else {{
                console.warn('Could not find marker for zone:', zoneName);
            }}
        }}
        
        // Start trying to open tooltip after a short delay
        setTimeout(() => tryOpenTooltip(), 200);
    }}

    function updateZoneCounts() {{
        const mapInfo = allMapData[currentMapType];
        if (!mapInfo) return;
        
        const selectedCats = Array.from(document.querySelectorAll(`#category-filters-${{currentMapType}} input[type="checkbox"]`))
            .filter(i => i.checked)
            .map(i => i.id.replace(currentMapType + '_', '').replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase()));
        
        const events = mapInfo.events;
        const zoneCounts = {{}};
        const zoneVolumes = {{}};
        
        events.forEach(event => {{
            if (selectedCats.includes(event.cat)) {{
                const zone = event.zone;
                zoneCounts[zone] = (zoneCounts[zone] || 0) + 1;
                zoneVolumes[zone] = (zoneVolumes[zone] || 0) + (event.vol || 0);
            }}
        }});
        
        function formatVol(vol) {{
            if (vol >= 1000000) return '$' + (vol / 1000000).toFixed(1) + 'M';
            if (vol >= 1000) return '$' + (vol / 1000).toFixed(0) + 'K';
            return '$' + Math.round(vol);
        }}
        
        document.querySelectorAll('.zone-radio').forEach(radio => {{
            const zone = radio.getAttribute('data-zone');
            const count = zoneCounts[zone] || 0;
            const volume = zoneVolumes[zone] || 0;
            const label = document.querySelector(`label[for='${{radio.id}}']`);
            if (label) {{
                label.textContent = `${{zone}} (${{count}}) - ${{formatVol(volume)}}`;
            }}
        }});
    }}
    
    function updateVisibility() {{
        const mapInfo = allMapData[currentMapType];
        if (!mapInfo) return;
        
        const config = mapInfo.config;
        const events = mapInfo.events;
        
        const selectedCats = Array.from(document.querySelectorAll(`#category-filters-${{currentMapType}} input[type="checkbox"]`))
            .filter(i => i.checked)
            .map(i => i.id.replace(currentMapType + '_', '').replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase()));
        
        const selectedRadio = document.querySelector('.zone-radio:checked');
        const selectedZone = selectedRadio ? selectedRadio.getAttribute('data-zone') : null;

        // Remove all markers
        if (map) {{
            markers.forEach(marker => map.removeLayer(marker));
        }}
        markers.length = 0;

        // Group events by zone - show ALL zones that match selected categories
        const zoneEvents = {{}};
        events.forEach(event => {{
            const eventCat = event.cat;
            const eventZone = event.zone;
            
            // Show all zones that match selected categories
            if (selectedCats.includes(eventCat)) {{
                if (!zoneEvents[eventZone]) {{
                    zoneEvents[eventZone] = [];
                }}
                zoneEvents[eventZone].push(event);
            }}
        }});

        // Count total events for selected categories
        let totalCount = 0;
        Object.values(zoneEvents).forEach(zoneEventList => {{
            totalCount += zoneEventList.length;
        }});
        // Removed total events count display

        // Always show all markers for selected categories (simplified - no zone selection required)
        if (!selectedZone) {{
            // Show all markers for all zones matching selected categories
            Object.keys(zoneEvents).forEach(zone => {{
                const events = zoneEvents[zone];
                if (events.length === 0) return;
                
                const coords = ZONE_COORDS[zone];
                if (!coords) return;
                
                // Get color from config
                const color = config.color || '#3b82f6';
                const [lat, lng] = coords;
                
                let marker = null;
                
                // Build tooltip first (needed for both modes)
                const eventsByCat = {{}};
                events.forEach(e => {{
                    if (!eventsByCat[e.cat]) eventsByCat[e.cat] = [];
                    eventsByCat[e.cat].push(e);
                }});
                
                let tooltipHtml = `<div class="line-tooltip"><div style="font-weight:700; color:white; margin-bottom:6px; border-bottom:1px solid #475569; padding-bottom:4px;">${{zone}}</div>`;
                
                function getBaseTopic(slug, q) {{
                    if (!slug) return q;
                    let base = slug.replace(/-\\d+$/, '');
                    const preps = "on|by|before|in|at|during|through|after";
                    const months = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december";
                    base = base.replace(new RegExp(`-(${{preps}})-(${{months}}|\\\\d{{1,2}}|\\\\d{{4}})(-(\\\\d{{1,2}}|\\\\d{{4}}))?(-.*)?$`, "i"), '');
                    base = base.replace(new RegExp(`-(${{months}})(-(\\\\d{{1,2}}|\\\\d{{4}}))?(-(\\\\d{{4}}))?$`, "i"), '');
                    base = base.replace(new RegExp(`-(\\\\d{{1,2}})-(${{months}})(-.*)?$`, "i"), '');
                    base = base.replace(/-(2024|2025|2026|2027|2028)$/, '');
                    base = base.replace(/^will-/, '').replace(/-?any-?$/, '').replace(/-?daily-?$/, '').replace(/-?weekly-?$/, '');
                    return base.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                }}
                
                tooltipHtml += `<button class="snapshot-btn" onclick="captureTooltipSnapshot(this)" title="Save tooltip as image">📷 Save as Image</button>`;
                
                const sortedCats = Object.keys(eventsByCat).sort();
                const tooltipId = `tooltip-${{zone.replace(/[^a-zA-Z0-9]/g, '-')}}-${{Date.now()}}`;
                
                // Collect all events for Top Volume tab
                const allEvents = [];
                Object.values(eventsByCat).forEach(catEvents => {{
                    allEvents.push(...catEvents);
                }});
                const topVolumeEvents = [...allEvents].sort((a, b) => (b.vol || 0) - (a.vol || 0)).slice(0, 50); // Top 50 by volume
                
                tooltipHtml += `<div class="tooltip-tabs" id="${{tooltipId}}-tabs">`;
                // Add Top Volume tab first
                tooltipHtml += `<div class="tooltip-tab active" onclick="switchTooltipTab('${{tooltipId}}', -1)" id="${{tooltipId}}-tab-topvol">💰 Top Volume</div>`;
                sortedCats.forEach((cat, idx) => {{
                    const tabId = `${{tooltipId}}-tab-${{idx}}`;
                    tooltipHtml += `<div class="tooltip-tab" onclick="switchTooltipTab('${{tooltipId}}', ${{idx}})" id="${{tabId}}">${{cat}}</div>`;
                }});
                tooltipHtml += `</div>`;
                
                // Top Volume tab content (first, active by default)
                tooltipHtml += `<div class="tooltip-tab-content active" id="${{tooltipId}}-content-topvol">`;
                topVolumeEvents.forEach(event => {{
                    const eventColor = getProbColor(event.price);
                    let volStr;
                    if (event.vol >= 1000000) {{
                        volStr = (event.vol / 1000000).toFixed(1) + 'M';
                    }} else if (event.vol >= 1000) {{
                        volStr = (event.vol / 1000).toFixed(1) + 'k';
                    }} else {{
                        volStr = Math.round(event.vol).toString();
                    }}
                    const polyLink = event.url || `https://polymarket.com/event/${{event.slug}}`;
                    tooltipHtml += `<div style="margin-bottom:4px; font-size: 0.8rem; padding: 4px; border-left: 2px solid ${{eventColor}};">
                        <span style="font-weight:700; color:#94a3b8;">[Vol: <strong style="font-weight:900;">$${{volStr}}</strong>]</span> 
                        <span style="color:#64748b; font-size:0.75rem;">[${{event.cat}}]</span>
                        <a href="${{polyLink}}" target="_blank" style="margin-left:5px; margin-right:5px; display:block; margin-top:2px;">${{event.q}}</a>
                        <span style="color:${{eventColor}}; font-weight:800;">${{Math.round(event.price * 100)}}%</span>
                    </div>`;
                }});
                tooltipHtml += `</div>`;
                
                sortedCats.forEach((cat, idx) => {{
                    const contentId = `${{tooltipId}}-content-${{idx}}`;
                    tooltipHtml += `<div class="tooltip-tab-content" id="${{contentId}}">`;
                    
                    const topics = {{}};
                    eventsByCat[cat].forEach(event => {{
                        const topic = getBaseTopic(event.slug, event.q);
                        if (!topics[topic]) topics[topic] = [];
                        topics[topic].push(event);
                    }});
                    
                    Object.keys(topics).forEach(topic => {{
                        tooltipHtml += `<div style="font-weight:700; color:#cbd5e1; margin-top:4px; margin-bottom:2px;">${{topic}}</div>`;
                        topics[topic].forEach(event => {{
                            const eventColor = getProbColor(event.price);
                            let volStr;
                            if (event.vol >= 1000000) {{
                                volStr = (event.vol / 1000000).toFixed(1) + 'M';
                            }} else if (event.vol >= 1000) {{
                                volStr = (event.vol / 1000).toFixed(1) + 'k';
                            }} else {{
                                volStr = Math.round(event.vol).toString();
                            }}
                            const polyLink = event.url || `https://polymarket.com/event/${{event.slug}}`;
                            tooltipHtml += `<div style="margin-bottom:2px; font-size: 0.8rem; padding-left: 10px;">
                                <span style="font-weight:700; color:#94a3b8;">[Vol: <strong style="font-weight:900;">$${{volStr}}</strong>]</span> 
                                <a href="${{polyLink}}" target="_blank" style="margin-left:5px; margin-right:5px;">${{event.q}}</a>
                                <span style="color:${{eventColor}}; font-weight:800;">${{Math.round(event.price * 100)}}%</span>
                            </div>`;
                        }});
                    }});
                    
                    tooltipHtml += `</div>`;
                }});
                
                tooltipHtml += `</div>`;
                
                // Now create marker with tooltip
                if (map) {{
                    // Create Leaflet marker
                    const iconSize = 20;
                    const icon = L.divIcon({{
                        className: 'map-icon',
                        html: `<span style="color: ${{color}}; font-size: ${{iconSize}}px; font-weight: bold; opacity: 0.6;">${{config.icon}}</span>`,
                        iconSize: [iconSize, iconSize],
                        iconAnchor: [iconSize/2, iconSize/2]
                    }});
                    marker = L.marker([lat, lng], {{ icon: icon }}).addTo(map);
                    marker.zoneName = zone;
                    marker.tooltipHtml = tooltipHtml;
                    marker.lat = lat;
                    marker.lng = lng;
                    
                    // Add Leaflet popup handlers
                    marker.bindPopup("", {{
                        closeButton: false,
                        autoClose: false,
                        className: 'line-popup',
                        minWidth: 600,
                        maxWidth: 600,
                        offset: [0, -10]
                    }});
                    
                    let popupTimeout;
                    let isPopupHovered = false;
                    
                    marker.on('mouseover', function(e) {{
                        clearTimeout(popupTimeout);
                        isPopupHovered = false;
                        this.setPopupContent(this.tooltipHtml);
                        this.openPopup(e.latlng);
                        
                        // Add event listeners to popup element to keep it open when hovering
                        setTimeout(() => {{
                            const popup = this.getPopup();
                            if (popup && popup.getElement()) {{
                                const popupElement = popup.getElement();
                                popupElement.addEventListener('mouseenter', function() {{
                                    clearTimeout(popupTimeout);
                                    isPopupHovered = true;
                                }});
                                popupElement.addEventListener('mouseleave', function() {{
                                    isPopupHovered = false;
                                    popupTimeout = setTimeout(() => {{
                                        if (!isPopupHovered) {{
                                            marker.closePopup();
                                        }}
                                    }}, 300);
                                }});
                            }}
                        }}, 100);
                    }});
                    
                    marker.on('mouseout', function(e) {{
                        // Only close if not hovering over popup
                        popupTimeout = setTimeout(() => {{
                            if (!isPopupHovered) {{
                                this.closePopup();
                            }}
                        }}, 500);
                    }});
                    
                    marker.on('click', function(e) {{
                        // Open tooltip immediately before updating visibility
                        if (this.tooltipHtml) {{
                            this.setPopupContent(this.tooltipHtml);
                            this.openPopup(e.latlng);
                        }}
                        
                        const safe_id = zone.replace(/ /g, '_').replace(/\\./g, '');
                        const radio = document.getElementById(`zone_${{safe_id}}`);
                        if (radio) {{
                            radio.checked = true;
                            updateVisibility();
                            
                            // After visibility updates, ensure tooltip is still open
                            setTimeout(() => {{
                                let selectedMarker = markers.find(m => m.zoneName === zone);
                                if (selectedMarker && selectedMarker.tooltipHtml) {{
                                    selectedMarker.setPopupContent(selectedMarker.tooltipHtml);
                                    selectedMarker.openPopup(selectedMarker.getLatLng());
                                }} else {{
                                    // Retry if marker not found yet
                                    setTimeout(() => {{
                                        selectedMarker = markers.find(m => m.zoneName === zone);
                                        if (selectedMarker && selectedMarker.tooltipHtml) {{
                                            selectedMarker.setPopupContent(selectedMarker.tooltipHtml);
                                            selectedMarker.openPopup(selectedMarker.getLatLng());
                                        }}
                                    }}, 200);
                                }}
                            }}, 200);
                        }}
                    }});
                }}
                
                if (marker) {{
                    markers.push(marker);
                }}
            }});
            return;
        }}

        // Don't move the map - keep it static

        let visibleCount = 0;
        
        // Create markers grouped by zone - show all zones
        for (const zone in zoneEvents) {{
            const events = zoneEvents[zone];
            const coords = ZONE_COORDS[zone] || [events[0].lat, events[0].lng];
            
            // Group events by category
            const eventsByCat = {{}};
            events.forEach(event => {{
                if (!eventsByCat[event.cat]) eventsByCat[event.cat] = [];
                eventsByCat[event.cat].push(event);
            }});
            
            // Get max probability for color
            const maxProb = Math.max(...events.map(e => e.price));
            const color = getProbColor(maxProb);
            
            // Highlight selected zone with larger marker (if zone is selected)
            const isSelected = selectedZone && zone === selectedZone;
            const [lat, lng] = coords;
            
            // Build tooltip HTML BEFORE creating marker
            function getBaseTopic(slug, q) {{
                if (!slug) return q;
                let base = slug.replace(/-\\d+$/, '');
                const preps = "on|by|before|in|at|during|through|after";
                const months = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december";
                
                base = base.replace(new RegExp(`-(${{preps}})-(${{months}}|\\\\d{{1,2}}|\\\\d{{4}})(-(\\\\d{{1,2}}|\\\\d{{4}}))?(-.*)?$`, "i"), '');
                base = base.replace(new RegExp(`-(${{months}})(-(\\\\d{{1,2}}|\\\\d{{4}}))?(-(\\\\d{{4}}))?$`, "i"), '');
                base = base.replace(new RegExp(`-(\\\\d{{1,2}})-(${{months}})(-.*)?$`, "i"), '');
                base = base.replace(/-(2024|2025|2026|2027|2028)$/, '');
                base = base.replace(/^will-/, '').replace(/-?any-?$/, '').replace(/-?daily-?$/, '').replace(/-?weekly-?$/, '');
                return base.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
            }}
            
            let tooltipHtml = `<div class="line-tooltip"><div style="font-weight:700; color:white; margin-bottom:6px; border-bottom:1px solid #475569; padding-bottom:4px;">${{zone}}</div>`;
            
            tooltipHtml += `<button class="snapshot-btn" onclick="captureTooltipSnapshot(this)" title="Save tooltip as image">📷 Save as Image</button>`;
            
            const sortedCats = Object.keys(eventsByCat).sort();
            const tooltipId = `tooltip-${{zone.replace(/[^a-zA-Z0-9]/g, '-')}}-${{Date.now()}}`;
            
            // Collect all events for Top Volume tab
            const allEvents = [];
            Object.values(eventsByCat).forEach(catEvents => {{
                allEvents.push(...catEvents);
            }});
            const topVolumeEvents = [...allEvents].sort((a, b) => (b.vol || 0) - (a.vol || 0)).slice(0, 50); // Top 50 by volume
            
            // Create tabs
            tooltipHtml += `<div class="tooltip-tabs" id="${{tooltipId}}-tabs">`;
            // Add Top Volume tab first
            tooltipHtml += `<div class="tooltip-tab active" onclick="switchTooltipTab('${{tooltipId}}', -1)" id="${{tooltipId}}-tab-topvol">💰 Top Volume</div>`;
            sortedCats.forEach((cat, idx) => {{
                const tabId = `${{tooltipId}}-tab-${{idx}}`;
                tooltipHtml += `<div class="tooltip-tab" onclick="switchTooltipTab('${{tooltipId}}', ${{idx}})" id="${{tabId}}">${{cat}}</div>`;
            }});
            tooltipHtml += `</div>`;
            
            // Top Volume tab content (first, active by default)
            tooltipHtml += `<div class="tooltip-tab-content active" id="${{tooltipId}}-content-topvol">`;
            topVolumeEvents.forEach(event => {{
                const eventColor = getProbColor(event.price);
                let volStr;
                if (event.vol >= 1000000) {{
                    volStr = (event.vol / 1000000).toFixed(1) + 'M';
                }} else if (event.vol >= 1000) {{
                    volStr = (event.vol / 1000).toFixed(1) + 'k';
                }} else {{
                    volStr = Math.round(event.vol).toString();
                }}
                const polyLink = event.url || `https://polymarket.com/event/${{event.slug}}`;
                tooltipHtml += `<div style="margin-bottom:4px; font-size: 0.8rem; padding: 4px; border-left: 2px solid ${{eventColor}};">
                    <span style="font-weight:700; color:#94a3b8;">[Vol: <strong style="font-weight:900;">$${{volStr}}</strong>]</span> 
                    <span style="color:#64748b; font-size:0.75rem;">[${{event.cat}}]</span>
                    <a href="${{polyLink}}" target="_blank" style="margin-left:5px; margin-right:5px; display:block; margin-top:2px;">${{event.q}}</a>
                    <span style="color:${{eventColor}}; font-weight:800;">${{Math.round(event.price * 100)}}%</span>
                </div>`;
            }});
            tooltipHtml += `</div>`;
            
            // Create tab contents
            sortedCats.forEach((cat, idx) => {{
                const contentId = `${{tooltipId}}-content-${{idx}}`;
                tooltipHtml += `<div class="tooltip-tab-content" id="${{contentId}}">`;
                
                const topics = {{}};
                eventsByCat[cat].forEach(event => {{
                    const topic = getBaseTopic(event.slug, event.q);
                    if (!topics[topic]) topics[topic] = [];
                    topics[topic].push(event);
                }});
                
                Object.keys(topics).forEach(topic => {{
                    tooltipHtml += `<div style="font-weight:700; color:#cbd5e1; margin-top:4px; margin-bottom:2px;">${{topic}}</div>`;
                    topics[topic].forEach(event => {{
                        const eventColor = getProbColor(event.price);
                        let volStr;
                        if (event.vol >= 1000000) {{
                            volStr = (event.vol / 1000000).toFixed(1) + 'M';
                        }} else if (event.vol >= 1000) {{
                            volStr = (event.vol / 1000).toFixed(1) + 'k';
                        }} else {{
                            volStr = Math.round(event.vol).toString();
                        }}
                        const polyLink = event.url || `https://polymarket.com/event/${{event.slug}}`;
                        tooltipHtml += `<div style="margin-bottom:2px; font-size: 0.8rem; padding-left: 10px;">
                            <span style="font-weight:700; color:#94a3b8;">[Vol: <strong style="font-weight:900;">$${{volStr}}</strong>]</span> 
                            <a href="${{polyLink}}" target="_blank" style="margin-left:5px; margin-right:5px;">${{event.q}}</a>
                            <span style="color:${{eventColor}}; font-weight:800;">${{Math.round(event.price * 100)}}%</span>
                        </div>`;
                    }});
                }});
                
                tooltipHtml += `</div>`;
            }});
            
            tooltipHtml += `</div>`;
            
            let marker;
            if (map) {{
                const iconSize = isSelected ? 36 : 28;
                const iconAnchor = isSelected ? 18 : 14;
                const iconStyle = isSelected 
                    ? `color: ${{color}}; font-size: ${{iconSize}}px; font-weight: bold; filter: drop-shadow(0 0 8px ${{color}}) drop-shadow(0 0 12px rgba(255,255,255,0.3));`
                    : `color: ${{color}}; font-size: ${{iconSize}}px; font-weight: bold; opacity: 0.6;`;
                const icon = L.divIcon({{
                    className: isSelected ? 'map-icon selected-zone-icon' : 'map-icon',
                    html: `<span style="${{iconStyle}}">${{config.icon}}</span>`,
                    iconSize: [iconSize, iconSize],
                    iconAnchor: [iconAnchor, iconSize]
                }});
                marker = L.marker([lat, lng], {{ icon: icon }}).addTo(map);
                marker.zoneName = zone;
                marker.tooltipHtml = tooltipHtml;
                marker.lat = lat;
                marker.lng = lng;
                
                // Add Leaflet popup handlers
                marker.bindPopup("", {{
                    closeButton: false,
                    autoClose: false,
                    className: 'line-popup',
                    minWidth: 400,
                    maxWidth: 2000,
                    offset: [0, -10]
                }});
                
                let popupTimeout;
                let isPopupHovered = false;
                
                marker.on('mouseover', function(e) {{
                    clearTimeout(popupTimeout);
                    isPopupHovered = false;
                    this.setPopupContent(this.tooltipHtml);
                    this.openPopup(e.latlng);
                    
                    // Store timeout and hover state on marker for access from tab switching
                    marker._popupTimeout = popupTimeout;
                    marker._isPopupHovered = isPopupHovered;
                    
                    // Add event listeners to popup element to keep it open when hovering
                    setTimeout(() => {{
                        const popup = this.getPopup();
                        if (popup && popup.getElement()) {{
                            const popupElement = popup.getElement();
                            popupElement.addEventListener('mouseenter', function() {{
                                clearTimeout(marker._popupTimeout);
                                marker._isPopupHovered = true;
                            }});
                            popupElement.addEventListener('mouseleave', function() {{
                                marker._isPopupHovered = false;
                                marker._popupTimeout = setTimeout(() => {{
                                    if (!marker._isPopupHovered) {{
                                        marker.closePopup();
                                    }}
                                }}, 500);
                            }});
                            
                            // Prevent closing when clicking on tabs
                            const tabs = popupElement.querySelectorAll('.tooltip-tab');
                            tabs.forEach(tab => {{
                                tab.addEventListener('click', function(e) {{
                                    clearTimeout(marker._popupTimeout);
                                    marker._isPopupHovered = true;
                                    e.stopPropagation();
                                }});
                                tab.addEventListener('mouseenter', function() {{
                                    clearTimeout(marker._popupTimeout);
                                    marker._isPopupHovered = true;
                                }});
                            }});
                        }}
                    }}, 100);
                }});
                
                marker.on('mouseout', function(e) {{
                    // Only close if not hovering over popup
                    this._popupTimeout = setTimeout(() => {{
                        if (!this._isPopupHovered) {{
                            this.closePopup();
                        }}
                    }}, 500);
                }});
                
                marker.on('click', function(e) {{
                    // Open tooltip immediately before updating visibility
                    if (this.tooltipHtml) {{
                        this.setPopupContent(this.tooltipHtml);
                        this.openPopup(e.latlng);
                    }}
                    
                    const safe_id = zone.replace(/ /g, '_').replace(/\\./g, '');
                    const radio = document.getElementById(`zone_${{safe_id}}`);
                    if (radio) {{
                        radio.checked = true;
                        updateVisibility();
                        
                        // After visibility updates, ensure tooltip is still open
                        setTimeout(() => {{
                            let selectedMarker = markers.find(m => m.zoneName === zone);
                            if (selectedMarker && selectedMarker.tooltipHtml) {{
                                selectedMarker.setPopupContent(selectedMarker.tooltipHtml);
                                selectedMarker.openPopup(selectedMarker.getLatLng());
                            }} else {{
                                // Retry if marker not found yet
                                setTimeout(() => {{
                                    selectedMarker = markers.find(m => m.zoneName === zone);
                                    if (selectedMarker && selectedMarker.tooltipHtml) {{
                                        selectedMarker.setPopupContent(selectedMarker.tooltipHtml);
                                        selectedMarker.openPopup(selectedMarker.getLatLng());
                                    }}
                                }}, 200);
                            }}
                        }}, 200);
                    }}
                }});
            }}
            
            if (isSelected) {{
                selectedZoneCount += events.length;
            }}
            visibleCount += events.length;
            
            // Make marker interactive
            if (marker) {{
                marker.userData = {{ zone: zone, events: events }};
                markers.push(marker);
            }}
        }}
        
        // Removed total events count display
    }}
    
    function switchTooltipTab(tooltipId, tabIndex) {{
        const tabsContainer = document.getElementById(`${{tooltipId}}-tabs`);
        if (!tabsContainer) return;

        // Find the marker that owns this tooltip and prevent it from closing
        const marker = markers.find(m => {{
            if (!m.tooltipHtml) return false;
            return m.tooltipHtml.includes(tooltipId);
        }});
        
        // Clear any pending close timeouts
        if (marker && marker._popupTimeout) {{
            clearTimeout(marker._popupTimeout);
            marker._popupTimeout = null;
        }}
        if (marker) {{
            marker._isPopupHovered = true;
        }}

        const tabs = tabsContainer.querySelectorAll('.tooltip-tab');
        
        // Handle Top Volume tab (tabIndex === -1)
        if (tabIndex === -1) {{
            tabs.forEach((tab, idx) => {{
                if (idx === 0) {{ // Top Volume is first tab
                    tab.classList.add('active');
                }} else {{
                    tab.classList.remove('active');
                }}
            }});
            
            // Show Top Volume content
            const topVolContent = document.getElementById(`${{tooltipId}}-content-topvol`);
            const allContents = [];
            let idx = 0;
            while (true) {{
                const content = document.getElementById(`${{tooltipId}}-content-${{idx}}`);
                if (!content) break;
                allContents.push(content);
                idx++;
            }}
            
            if (topVolContent) {{
                topVolContent.classList.add('active');
            }}
            allContents.forEach(content => {{
                content.classList.remove('active');
            }});
        }} else {{
            // Handle category tabs
            tabs.forEach((tab, idx) => {{
                if (idx === tabIndex + 1) {{ // +1 because Top Volume is at index 0
                    tab.classList.add('active');
                }} else {{
                    tab.classList.remove('active');
                }}
            }});
            
            const allContents = [];
            const topVolContent = document.getElementById(`${{tooltipId}}-content-topvol`);
            if (topVolContent) {{
                topVolContent.classList.remove('active');
            }}
            let idx = 0;
            while (true) {{
                const content = document.getElementById(`${{tooltipId}}-content-${{idx}}`);
                if (!content) break;
                allContents.push(content);
                idx++;
            }}

            allContents.forEach((content, idx) => {{
                if (idx === tabIndex) {{
                    content.classList.add('active');
                }} else {{
                    content.classList.remove('active');
                }}
            }});
        }}
        
        // Reset hover state after a short delay to allow normal mouseout behavior
        if (marker) {{
            setTimeout(() => {{
                if (marker) {{
                    marker._isPopupHovered = false;
                }}
            }}, 100);
        }}
    }}
    
    function captureTooltipSnapshot(button) {{
        const tooltipElement = button.closest('.line-tooltip');
        if (!tooltipElement) {{
            console.error('Tooltip element not found');
            return;
        }}
        
        const originalDisplay = button.style.display;
        button.style.display = 'none';
        
        const headerText = tooltipElement.querySelector('div').textContent || 'tooltip';
        const filename = headerText.replace(/\\s+/g, '_').replace(/[^a-zA-Z0-9_]/g, '') + '_' + new Date().toISOString().slice(0, 10) + '.png';
        
        if (typeof html2canvas !== 'undefined') {{
            html2canvas(tooltipElement, {{
                backgroundColor: '#0f172a',
                scale: 2,
                logging: false,
                useCORS: true
            }}).then(canvas => {{
                canvas.toBlob(function(blob) {{
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = filename;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    URL.revokeObjectURL(url);
                    
                    button.style.display = originalDisplay;
                    
                    const originalText = button.textContent;
                    button.textContent = '✓ Saved!';
                    button.style.background = '#22c55e';
                    setTimeout(() => {{
                        button.textContent = originalText;
                        button.style.background = '';
                    }}, 1500);
                }}, 'image/png');
            }}).catch(err => {{
                console.error('Error capturing tooltip:', err);
                button.style.display = originalDisplay;
                alert('Failed to capture tooltip. Please try again.');
            }});
        }} else {{
            button.style.display = originalDisplay;
            alert('html2canvas library not loaded. Please refresh the page.');
        }}
    }}
    
    // Already initialized above
</script>
</body>
</html>
"""
    
    final_html = html_template.replace("ALL_MAP_DATA_PLACEHOLDER", all_map_data_json)
    
    output_path = os.path.join(os.path.dirname(__file__), "market_report.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"Done! Generated market_report.html with all map types")

if __name__ == "__main__":
    generate_combined_html()
