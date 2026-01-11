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
    
    # Calculate statistics
    stats = generator.calculate_market_stats()
    
    # Get base HTML components
    html_head = generator.get_common_html_head()
    css = generator.get_common_css()
    analytics_code = generator.get_analytics_code()
    zone_coords_js = generator.get_zone_coords_js()
    
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    # Generate map selector
    map_selector = '<select id="map-type-selector" onchange="switchMapType(this.value)" style="padding: 8px 12px; background: #1e293b; color: #e2e8f0; border: 1px solid #475569; border-radius: 6px; font-size: 1rem; font-weight: 600; cursor: pointer; margin-bottom: 12px;">\n'
    for map_type, map_info in all_map_data.items():
        config = map_info["config"]
        selected = 'selected' if map_type == 'conflict' else ''
        map_selector += f'        <option value="{map_type}" {selected}>{config["icon"]} {config["name"]}</option>\n'
    map_selector += '    </select>'
    
    # Generate category filters for each map type (will be shown/hidden)
    category_filters_html = ""
    for map_type, map_info in all_map_data.items():
        config = map_info["config"]
        category_checks = ""
        for cat in config["keywords"].keys():
            safe_id = cat.replace(" ", "_").replace("&", "")
            category_checks += f"<div class='filter-item'><input type='checkbox' id='{map_type}_{safe_id}' checked onchange='updateZoneCounts(); updateVisibility()'> <label for='{map_type}_{safe_id}'>{cat}</label></div>"
        
        category_filters_html += f'<div id="category-filters-{map_type}" class="category-filters" style="display: none;">\n{category_checks}\n</div>\n'
    
    # CSS
    combined_css = """
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
            max-height: 400px;
            overflow-y: auto;
        }
        .tooltip-tab-content.active {
            display: block;
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
    <h1>Select Map Type</h1>
    {map_selector}
    
    <hr style="margin: 10px 0;">
    <h1>Select Categories</h1>
    {category_filters_html}
    
    <hr style="margin: 10px 0;">
    <h1 style="margin-bottom: 8px;">Choose Zone</h1>
    <div id="zone-filters" style="max-height: 200px; overflow-y: auto;">
        ZONE_FILTERS_PLACEHOLDER
    </div>
</div>

<div class="info-box">
    <h1 id="map-title" style="font-size: 1.2rem;">Loading...</h1>
    <p id="stats-text">Loading...</p>
    <div style="font-size: 0.75rem; color: #64748b; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
        <div style="padding: 8px; background: rgba(59, 130, 246, 0.1); border-radius: 6px; border-left: 3px solid #3b82f6; display: flex; align-items: center; gap: 8px;">
            <span style="color: #94a3b8;">Last Updated:</span>
            <span style="color: #3b82f6; font-weight: 700;">{current_time}</span>
        </div>
        <span style="color: #94a3b8;">•</span>
        <div style="padding: 8px; background: rgba(15, 23, 42, 0.8); border-radius: 6px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            <span style="color: #e2e8f0;">Total: <strong>{stats["total"]}</strong></span>
            <span style="color: #ef4444;">⚔️ <strong>{stats["conflicts"]}</strong></span>
            <span style="color: #22c55e;">⚽ <strong>{stats["sports"]}</strong></span>
            <span style="color: #fbbf24;">💰 <strong>{stats["finance"]}</strong></span>
            <span style="color: #a855f7;">🗳️ <strong>{stats["elections"]}</strong></span>
            <span style="color: #06b6d4;">💻 <strong>{stats["technology"]}</strong></span>
            <span style="color: #94a3b8;">Unmapped: <strong>{stats["unmapped"]}</strong></span>
        </div>
        <span style="color: #94a3b8;">•</span>
        <span id="map-description" style="color: #94a3b8;">Loading...</span>
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
    const map = L.map('map', {{
        zoomControl: false,
        attributionControl: false
    }}).setView([40, -100], 4); 

    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{ maxZoom: 20 }}).addTo(map);

    const markers = [];

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
        
        // Update title and description
        document.getElementById('map-title').textContent = config.name;
        document.getElementById('map-description').textContent = config.description;
        
        // Show/hide category filters
        document.querySelectorAll('.category-filters').forEach(el => el.style.display = 'none');
        document.getElementById(`category-filters-${{mapType}}`).style.display = 'block';
        
        // Update zone filters
        updateZoneFilters(mapType);
        
        // Update visibility
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
            const safe_id = z.replace(/ /g, '_').replace(/\./g, '');
            const checked = idx === 0 ? 'checked' : '';
            const count = all_zones[z];
            const volume = zone_volumes[z] || 0;
            const radio = document.createElement('div');
            radio.className = 'filter-item';
            radio.innerHTML = `<input type="radio" name="zone" class="zone-radio" id="zone_${{safe_id}}" data-zone="${{z}}" ${{checked}} onchange="onZoneChange('${{z}}')"> <label for="zone_${{safe_id}}">${{z}} (${{count}}) - ${{formatVol(volume)}}</label>`;
            zoneFiltersDiv.appendChild(radio);
        }});
    }}
    
    function onZoneChange(zoneName) {{
        const coords = ZONE_COORDS[zoneName];
        if (coords) {{
            map.setView(coords, 5, {{ animate: true, duration: 0.5 }});
        }}
        updateVisibility();
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
        markers.forEach(marker => map.removeLayer(marker));
        markers.length = 0;

        if (!selectedZone) {{
            document.getElementById('stats-text').innerText = 'Please select a zone.';
            return;
        }}

        // Center map on selected zone
        const selectedCoords = ZONE_COORDS[selectedZone];
        if (selectedCoords) {{
            map.setView(selectedCoords, 5, {{ animate: true, duration: 0.5 }});
        }}

        // Group events by zone - show ALL zones that match selected categories
        const zoneEvents = {{}};
        events.forEach(event => {{
            const eventCat = event.cat;
            const eventZone = event.zone;
            
            // Show all zones that match selected categories (not just selected zone)
            if (selectedCats.includes(eventCat)) {{
                if (!zoneEvents[eventZone]) {{
                    zoneEvents[eventZone] = [];
                }}
                zoneEvents[eventZone].push(event);
            }}
        }});

        let visibleCount = 0;
        let selectedZoneCount = 0;
        
        // Create markers grouped by zone
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
            
            // Highlight selected zone with larger icon and border
            const isSelected = zone === selectedZone;
            const iconSize = isSelected ? 36 : 28;
            const iconAnchor = isSelected ? 18 : 14;
            const iconStyle = isSelected 
                ? `color: ${{color}}; font-size: ${{iconSize}}px; font-weight: bold; filter: drop-shadow(0 0 8px ${{color}}) drop-shadow(0 0 12px rgba(255,255,255,0.3));`
                : `color: ${{color}}; font-size: ${{iconSize}}px; font-weight: bold; opacity: 0.6;`;
            
            // Create icon
            const icon = L.divIcon({{
                className: isSelected ? 'map-icon selected-zone-icon' : 'map-icon',
                html: `<span style="${{iconStyle}}">${{config.icon}}</span>`,
                iconSize: [iconSize, iconSize],
                iconAnchor: [iconAnchor, iconSize]
            }});
            
            const marker = L.marker(coords, {{ icon: icon }}).addTo(map);
            
            // Only show tooltip for selected zone events
            if (!isSelected) {{
                markers.push(marker);
                visibleCount += events.length;
                continue;
            }}
            
            selectedZoneCount += events.length;
            
            // Build tooltip HTML
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
            
            // Create tabs
            tooltipHtml += `<div class="tooltip-tabs" id="${{tooltipId}}-tabs">`;
            sortedCats.forEach((cat, idx) => {{
                const tabId = `${{tooltipId}}-tab-${{idx}}`;
                const activeClass = idx === 0 ? 'active' : '';
                tooltipHtml += `<div class="tooltip-tab ${{activeClass}}" onclick="switchTooltipTab('${{tooltipId}}', ${{idx}})" id="${{tabId}}">${{cat}}</div>`;
            }});
            tooltipHtml += `</div>`;
            
            // Create tab contents
            sortedCats.forEach((cat, idx) => {{
                const contentId = `${{tooltipId}}-content-${{idx}}`;
                const activeClass = idx === 0 ? 'active' : '';
                tooltipHtml += `<div class="tooltip-tab-content ${{activeClass}}" id="${{contentId}}">`;
                
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
                        const volStr = event.vol >= 1000 ? (event.vol / 1000).toFixed(1) + 'k' : Math.round(event.vol);
                        const polyLink = event.url || `https://polymarket.com/event/${{event.slug}}`;
                        tooltipHtml += `<div style="margin-bottom:2px; font-size: 0.8rem; padding-left: 10px;">
                            <span style="font-weight:700; color:#94a3b8;">[${{event.date}}]</span> 
                            <span style="font-weight:700; color:#94a3b8;">[Vol: $${{volStr}}]</span> 
                            <a href="${{polyLink}}" target="_blank" style="margin-left:5px; margin-right:5px;">${{event.q}}</a>
                            <span style="color:${{eventColor}}; font-weight:800;">${{Math.round(event.price * 100)}}%</span>
                        </div>`;
                    }});
                }});
                
                tooltipHtml += `</div>`;
            }});
            
            tooltipHtml += `</div>`;
            
            marker.bindPopup("", {{
                closeButton: false,
                autoClose: false,
                className: 'line-popup',
                minWidth: 400,
                maxWidth: 2000,
                offset: [0, -10]
            }});
            
            let popupTimeout;
            marker.on('mouseover', function(e) {{
                clearTimeout(popupTimeout);
                this.setPopupContent(tooltipHtml);
                this.openPopup(e.latlng);
            }});
            
            marker.on('mouseout', function(e) {{
                popupTimeout = setTimeout(() => {{
                    this.closePopup();
                }}, 400);
            }});
            
            marker.on('popupopen', function(e) {{
                const popupEl = e.popup.getElement();
                if (popupEl) {{
                    popupEl.addEventListener('mouseenter', () => clearTimeout(popupTimeout));
                    popupEl.addEventListener('mouseleave', () => {{
                        popupTimeout = setTimeout(() => {{
                            this.closePopup();
                        }}, 400);
                    }});
                }}
            }});
            
            markers.push(marker);
            visibleCount += events.length;
        }}
        
        document.getElementById('stats-text').innerText = `Visualizing ${{visibleCount}} events.`;
    }}
    
    function switchTooltipTab(tooltipId, tabIndex) {{
        const tabsContainer = document.getElementById(`${{tooltipId}}-tabs`);
        if (!tabsContainer) return;
        
        const tabs = tabsContainer.querySelectorAll('.tooltip-tab');
        const allContents = [];
        let idx = 0;
        while (true) {{
            const content = document.getElementById(`${{tooltipId}}-content-${{idx}}`);
            if (!content) break;
            allContents.push(content);
            idx++;
        }}
        
        tabs.forEach((tab, idx) => {{
            if (idx === tabIndex) {{
                tab.classList.add('active');
            }} else {{
                tab.classList.remove('active');
            }}
        }});
        
        allContents.forEach((content, idx) => {{
            if (idx === tabIndex) {{
                content.classList.add('active');
            }} else {{
                content.classList.remove('active');
            }}
        }});
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
    
    // Initialize
    switchMapType('conflict');
    updateZoneCounts();
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
