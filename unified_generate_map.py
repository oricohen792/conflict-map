#!/usr/bin/env python3
"""
Unified map generator - reads from JSON config and generates all map types
All maps use the same marker-based visualization (no arcs)
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

def generate_map(map_type, config_data):
    """Generate a map based on config"""
    config = config_data["maps"][map_type]
    generator = MapGeneratorBase(f"{config['name']} Generator", config["html_file"])
    markets = generator.load_markets()
    
    if not markets:
        print(f"No markets loaded for {map_type}")
        return
    
    # Get all keywords
    all_keywords = []
    for keywords_list in config["keywords"].values():
        all_keywords.extend(keywords_list)
    
    # Filter markets
    event_data = []
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"Filtering and categorizing {config['name']} events...")
    
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
            "unique_id": f"{map_type[0].upper()}{len(event_data)}",
            "q": q,
            "price": price,
            "date": end_date,
            "vol": vol,
            "lat": coords[0],
            "lng": coords[1],
            "zone": zone_name,
            "cat": assigned_cat,
            "updated": current_time,
            "slug": m.get("slug", ""),
            "url": f"https://polymarket.com/event/{parent_slug}",
            "clobTokenIds": m.get("clobTokenIds", "")
        })
    
    print(f"Found {len(event_data)} {config['name']} events.")
    
    if event_data:
        html = generate_html(map_type, config, event_data, generator, config_data)
        output_path = os.path.join(os.path.dirname(__file__), config["html_file"])
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Done! Generated {config['html_file']} with {len(event_data)} markets")
    else:
        print(f"No events found for {map_type}")

def generate_html(map_type, config, events, generator, config_data):
    """Generate HTML map from filtered event data"""
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    json_events = json.dumps(events)
    
    # Calculate market statistics
    stats = generator.calculate_market_stats()
    
    # Generate category filters
    category_checks = ""
    for cat in config["keywords"].keys():
        safe_id = cat.replace(" ", "_").replace("&", "")
        category_checks += f"<div class='filter-item'><input type='checkbox' id='{safe_id}' checked onchange='updateZoneCounts(); updateVisibility()'> <label for='{safe_id}'>{cat}</label></div>"
    
    # Generate zone filters
    all_zones = {}
    for e in events:
        zone = e.get("zone", "Unknown")
        all_zones[zone] = all_zones.get(zone, 0) + 1
    
    zone_checks = ""
    for z in sorted(all_zones.keys(), key=lambda x: all_zones[x], reverse=True):
        safe_id = z.replace(" ", "_").replace(".", "")
        checked = "checked" if z == "United States" else ""
        count = all_zones[z]
        zone_checks += f"<div class='filter-item'><input type='radio' name='zone' class='zone-radio' id='zone_{safe_id}' data-zone='{z}' {checked} onchange='onZoneChange(\"{z}\")'> <label for='zone_{safe_id}'>{z} ({count})</label></div>"
    
    # Get base HTML components
    html_head = generator.get_common_html_head()
    css = generator.get_common_css()
    analytics_code = generator.get_analytics_code()
    zone_coords_js = generator.get_zone_coords_js()
    
    # Map-specific CSS
    map_css = f"""
        .map-icon {{
            font-size: 24px;
            cursor: pointer;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
        }}
        .line-tooltip {{
            background: rgba(15, 23, 42, 0.98);
            border: 1px solid #475569;
            color: #f1f5f9;
            padding: 10px;
            border-radius: 6px;
            font-size: 13px;
            max-width: none;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            pointer-events: auto;
        }}
        .line-tooltip {{
            border: 1px solid #475569;
            background: #0f172a !important;
            color: #f1f5f9 !important;
        }}
        .leaflet-popup-content-wrapper, .leaflet-popup-tip {{
            background: #0f172a !important;
            color: #f1f5f9 !important;
            border: 1px solid #475569;
        }}
        .leaflet-popup-content {{ margin: 8px 12px; }}
        .line-tooltip a {{ color: #38bdf8; text-decoration: none; font-weight: 500; }}
        .line-tooltip a:hover {{ text-decoration: underline; color: #7dd3fc; }}
        
        .snapshot-btn {{
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
        }}
        .snapshot-btn:hover {{
            background: #2563eb;
        }}
        .snapshot-btn:active {{
            background: #1d4ed8;
        }}
        .tooltip-tabs {{
            display: flex;
            gap: 4px;
            margin-bottom: 10px;
            border-bottom: 1px solid #475569;
            flex-wrap: wrap;
        }}
        .tooltip-tab {{
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
        }}
        .tooltip-tab:hover {{
            background: #334155;
            color: #cbd5e1;
        }}
        .tooltip-tab.active {{
            background: #0f172a;
            color: {config['color']};
            border-color: #475569;
            border-bottom-color: #0f172a;
        }}
        .tooltip-tab-content {{
            display: none;
            max-height: 400px;
            overflow-y: auto;
        }}
        .tooltip-tab-content.active {{
            display: block;
        }}
        #zone-filters {{ max-height: 200px; overflow-y: auto; }}
        .info-box {{
            left: 50%;
            transform: translateX(-50%);
            max-width: 90%;
            width: auto;
            display: flex;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
            justify-content: center;
        }}
        .info-box > h1 {{
            margin: 0;
            white-space: nowrap;
        }}
        .info-box > p {{
            margin: 0;
            white-space: nowrap;
        }}
        .info-box > div {{
            margin: 0;
            padding: 0;
            border: none;
            background: transparent;
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: nowrap;
        }}
        .info-box > div > div {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }}
        .nav-links {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-top: 12px;
        }}
        .nav-link {{
            padding: 8px 12px;
            background: rgba(59, 130, 246, 0.1);
            color: #3b82f6;
            text-decoration: none;
            border-radius: 6px;
            border: 1px solid #3b82f6;
            font-weight: 600;
            font-size: 0.85rem;
            transition: all 0.2s;
            text-align: center;
        }}
        .nav-link:hover {{
            background: rgba(59, 130, 246, 0.2);
        }}
        """
    
    # Insert map_css before the closing </style> tag
    css_with_map = css.replace("    </style>", map_css + "    </style>")
    
    # Generate navigation links (all other maps)
    nav_links = ""
    for other_type, other_config in config_data["maps"].items():
        if other_type != map_type:
            nav_links += f'<a href="{other_config["html_file"]}" class="nav-link">{other_config["icon"]} {other_config["name"].split(" Map")[0]}</a>\n        '
    
    html_template = html_head + css_with_map + analytics_code + f"""
</head>
<body>

<div id="map"></div>
<button id="mobile-filter-btn" style="display:none;" onclick="document.querySelector('.filter-box').classList.toggle('active')">
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"></line><line x1="4" y1="10" x2="4" y2="3"></line><line x1="12" y1="21" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="3"></line><line x1="20" y1="21" x2="20" y2="16"></line><line x1="20" y1="12" x2="20" y2="3"></line><line x1="1" y1="14" x2="7" y2="14"></line><line x1="9" y1="8" x2="15" y2="8"></line><line x1="17" y1="16" x2="23" y2="16"></line></svg>
    Filters
</button>

<div class="filter-box">
    <div class="close-filter" style="display:none;" onclick="document.querySelector('.filter-box').classList.remove('active')">&times;</div>
    <h1>Select {config['name'].split(' Map')[0]} Categories</h1>
    CATEGORY_FILTERS_PLACEHOLDER
    
    <hr style="margin: 10px 0;">
    <h1 style="margin-bottom: 8px;">Choose Zone</h1>
    <div id="zone-filters" style="max-height: 200px; overflow-y: auto;">
        ZONE_FILTERS_PLACEHOLDER
    </div>
</div>

<div class="info-box">
    <h1 style="font-size: 1.2rem;">{config['name']}</h1>
    <p id="stats-text">Loading...</p>
    <div style="font-size: 0.75rem; color: #64748b; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
        <div style="padding: 8px; background: rgba(59, 130, 246, 0.1); border-radius: 6px; border-left: 3px solid #3b82f6; display: flex; align-items: center; gap: 8px;">
            <span style="color: #94a3b8;">Last Updated:</span>
            <span style="color: #3b82f6; font-weight: 700;">LAST_UPDATE_PLACEHOLDER</span>
        </div>
        <span style="color: #94a3b8;">•</span>
        <div style="padding: 8px; background: rgba(15, 23, 42, 0.8); border-radius: 6px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            <span style="color: #e2e8f0;">Total: <strong>STATS_TOTAL</strong></span>
            <span style="color: #ef4444;">⚔️ <strong>STATS_CONFLICTS</strong></span>
            <span style="color: #22c55e;">⚽ <strong>STATS_SPORTS</strong></span>
            <span style="color: #fbbf24;">💰 <strong>STATS_FINANCE</strong></span>
            <span style="color: #a855f7;">🗳️ <strong>STATS_ELECTIONS</strong></span>
            <span style="color: #06b6d4;">💻 <strong>STATS_TECHNOLOGY</strong></span>
            <span style="color: #94a3b8;">Unmapped: <strong>STATS_UNMAPPED</strong></span>
        </div>
        <span style="color: #94a3b8;">•</span>
        <span style="color: #94a3b8;">{config['description']}</span>
    </div>
</div>

<div class="legend">
    <h1>Market Odds</h1>
    <div class="legend-item"><div class="legend-color" style="background:#22c55e"></div>High ( > 70%)</div>
    <div class="legend-item"><div class="legend-color" style="background:#eab308"></div>Medium (40-70%)</div>
    <div class="legend-item"><div class="legend-color" style="background:#f97316"></div>Low (10-40%)</div>
    <div class="legend-item"><div class="legend-color" style="background:#ef4444"></div>Remote ( < 10%)</div>
    <hr style="margin: 12px 0; border-color: #334155;">
    <div class="nav-links">
        {nav_links}
    </div>
</div>

</div>


<script>
    const map = L.map('map', {{
        zoomControl: false,
        attributionControl: false
    }}).setView([40, -100], 4); 

    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{ maxZoom: 20 }}).addTo(map);

    const eventsData = JSON_EVENTS_PLACEHOLDER;
    const markers = [];

    function getProbColor(p) {{
        if (p >= 0.70) return '#22c55e';
        if (p >= 0.40) return '#eab308';
        if (p >= 0.10) return '#f97316';
        return '#ef4444';
    }}
    
    {zone_coords_js}
    
    function onZoneChange(zoneName) {{
        const coords = ZONE_COORDS[zoneName];
        if (coords) {{
            map.setView(coords, 5, {{ animate: true, duration: 0.5 }});
        }}
        updateVisibility();
    }}

    function updateZoneCounts() {{
        const selectedCats = Array.from(document.querySelectorAll('.filter-box input[type="checkbox"]:not(.zone-radio)')).filter(i => i.checked).map(i => i.id.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase()));
        
        const zoneCounts = {{}};
        const zoneVolumes = {{}};
        eventsData.forEach(event => {{
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
        const selectedCats = Array.from(document.querySelectorAll('.filter-box input[type="checkbox"]:not(.zone-radio)')).filter(i => i.checked).map(i => i.id.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase()));
        const selectedRadio = document.querySelector('.zone-radio:checked');
        const selectedZone = selectedRadio ? selectedRadio.getAttribute('data-zone') : null;

        // Remove all markers
        markers.forEach(marker => map.removeLayer(marker));
        markers.length = 0;

        if (!selectedZone) {{
            document.getElementById('stats-text').innerText = 'Please select a zone.';
            return;
        }}

        // Group events by zone
        const zoneEvents = {{}};
        eventsData.forEach(event => {{
            const eventCat = event.cat;
            const eventZone = event.zone;
            
            if (eventZone === selectedZone && selectedCats.includes(eventCat)) {{
                if (!zoneEvents[eventZone]) {{
                    zoneEvents[eventZone] = [];
                }}
                zoneEvents[eventZone].push(event);
            }}
        }});

        let visibleCount = 0;
        
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
            
            // Create icon
            const icon = L.divIcon({{
                className: 'map-icon',
                html: `<span style="color: ${{color}}; font-size: 28px; font-weight: bold;">{config['icon']}</span>`,
                iconSize: [28, 28],
                iconAnchor: [14, 28]
            }});
            
            const marker = L.marker(coords, {{ icon: icon }}).addTo(map);
            
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
        
        document.getElementById('stats-text').innerText = `Visualizing ${{visibleCount}} {config['name'].lower()} events.`;
    }}
    
    // Initialize visibility
    updateZoneCounts();
    updateVisibility();
    
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
        
        // Update tabs
        tabs.forEach((tab, idx) => {{
            if (idx === tabIndex) {{
                tab.classList.add('active');
            }} else {{
                tab.classList.remove('active');
            }}
        }});
        
        // Update contents
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
</script>
</body>
</html>
"""
    
    final_html = html_template.replace("JSON_EVENTS_PLACEHOLDER", json_events)
    final_html = final_html.replace("LAST_UPDATE_PLACEHOLDER", current_time)
    final_html = final_html.replace("CATEGORY_FILTERS_PLACEHOLDER", category_checks)
    final_html = final_html.replace("ZONE_FILTERS_PLACEHOLDER", zone_checks)
    final_html = final_html.replace("STATS_TOTAL", str(stats["total"]))
    final_html = final_html.replace("STATS_CONFLICTS", str(stats["conflicts"]))
    final_html = final_html.replace("STATS_SPORTS", str(stats["sports"]))
    final_html = final_html.replace("STATS_FINANCE", str(stats["finance"]))
    final_html = final_html.replace("STATS_ELECTIONS", str(stats["elections"]))
    final_html = final_html.replace("STATS_TECHNOLOGY", str(stats["technology"]))
    final_html = final_html.replace("STATS_UNMAPPED", str(stats["unmapped"]))
    
    return final_html

def main():
    """Main function - generate all maps"""
    import sys
    
    config_data = load_config()
    
    if len(sys.argv) > 1:
        # Generate specific map type
        map_type = sys.argv[1]
        if map_type in config_data["maps"]:
            print(f"Generating {map_type} map...")
            generate_map(map_type, config_data)
        else:
            print(f"Unknown map type: {map_type}")
            print(f"Available types: {', '.join(config_data['maps'].keys())}")
    else:
        # Generate all maps
        print("Generating all maps...")
        for map_type in config_data["maps"].keys():
            print(f"\n{'='*60}")
            generate_map(map_type, config_data)

if __name__ == "__main__":
    main()
