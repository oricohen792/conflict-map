#!/usr/bin/env python3
"""
Generate conflict map from saved Polymarket data - uses base class
"""
import json
from datetime import datetime, timezone
from map_base import MapGeneratorBase, ZONE_COORD_MAP

# Category Keywords for conflicts
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


class ConflictMapGenerator(MapGeneratorBase):
    """Conflict map generator - shows conflicts between zones as arcs"""
    
    def __init__(self):
        super().__init__("Conflict Map Generator", "market_report.html")
    
    def filter_markets(self):
        """Filter and categorize conflict markets"""
        line_data = []
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        print("Filtering and categorizing conflict bets...")
        
        for m in self.markets:
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
                
            found_zones = self.find_zones_in_text(q)
            unique_names = list(found_zones.keys())
            
            if len(unique_names) >= 2:
                sorted_names = sorted(unique_names[:2])
                src_name = sorted_names[0]
                tgt_name = sorted_names[1]
                src_coords = ZONE_COORD_MAP[src_name]
                tgt_coords = ZONE_COORD_MAP[tgt_name]
                
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
                    "updated": current_time,
                    "zones": sorted([src_name, tgt_name]),
                    "slug": m.get("slug", ""),
                    "url": f"https://polymarket.com/event/{parent_slug}",
                    "clobTokenIds": m.get("clobTokenIds", "")
                })

        print(f"Found {len(line_data)} conflict bets between zones.")
        return line_data
    
    def generate_html(self, lines):
        """Generate HTML map from filtered market data"""
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        json_lines = json.dumps(lines)
        
        # Generate zone filters
        all_zones = {}
        for l in lines:
            for z in l["zones"]:
                all_zones[z] = all_zones.get(z, 0) + 1
        
        zone_checks = ""
        for z in sorted(all_zones.keys(), key=lambda x: all_zones[x], reverse=True):
            safe_id = z.replace(" ", "_").replace(".", "")
            checked = "checked" if z == "Israel" else ""
            count = all_zones[z]
            zone_checks += f"<div class='filter-item'><input type='radio' name='zone' class='zone-radio' id='{safe_id}' data-zone='{z}' {checked} onchange='onZoneChange(\"{z}\")'> <label for='{safe_id}'>{z} ({count})</label></div>"
        
        # Get base HTML components
        html_head = self.get_common_html_head()
        css = self.get_common_css()
        analytics_code = self.get_analytics_code()
        zone_coords_js = self.get_zone_coords_js()
        
        # Add conflict-specific CSS
        conflict_css = """
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
        .info-box a { transition: opacity 0.2s; }
        .info-box a:hover { opacity: 0.8; }
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
        .snapshot-btn:active {
            background: #1d4ed8;
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
            color: #fbbf24;
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
        #zone-filters { max-height: 50vh !important; }
        .nav-links {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-top: 12px;
        }
        .nav-link {
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
        }
        .nav-link:hover {
            background: rgba(59, 130, 246, 0.2);
        }
        """
        
        # Insert conflict_css before the closing </style> tag
        css_with_conflict = css.replace("    </style>", conflict_css + "    </style>")
        
        html_template = html_head + css_with_conflict + analytics_code + """
</head>
<body>

<div id="map"></div>
<button id="mobile-filter-btn" style="display:none;" onclick="document.querySelector('.filter-box').classList.toggle('active')">
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"></line><line x1="4" y1="10" x2="4" y2="3"></line><line x1="12" y1="21" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="3"></line><line x1="20" y1="21" x2="20" y2="16"></line><line x1="20" y1="12" x2="20" y2="3"></line><line x1="1" y1="14" x2="7" y2="14"></line><line x1="9" y1="8" x2="15" y2="8"></line><line x1="17" y1="16" x2="23" y2="16"></line></svg>
    Filters
</button>

<div class="filter-box">
    <div class="close-filter" style="display:none;" onclick="document.querySelector('.filter-box').classList.remove('active')">&times;</div>
    <h1>Select Conflicts</h1>
    <div class="filter-item"><input type="checkbox" id="Military" checked onchange="updateZoneCounts(); updateVisibility()"> <label for="Military">Military</label></div>
    <div class="filter-item"><input type="checkbox" id="Trade" checked onchange="updateZoneCounts(); updateVisibility()"> <label for="Trade">Trade</label></div>
    <div class="filter-item"><input type="checkbox" id="Drugs & Border" checked onchange="updateZoneCounts(); updateVisibility()"> <label for="Drugs & Border">Drugs & Border</label></div>
    <div class="filter-item"><input type="checkbox" id="Diplomatic" checked onchange="updateZoneCounts(); updateVisibility()"> <label for="Diplomatic">Diplomatic</label></div>
    
    <hr style="margin: 10px 0;">
    <h1 style="margin-bottom: 8px;">Choose Zone</h1>
    <div id="zone-filters" style="max-height: 200px; overflow-y: auto;">
        ZONE_FILTERS_PLACEHOLDER
    </div>
</div>

<div class="info-box">
    <h1 style="font-size: 1.2rem;">Conflict Prediction Map</h1>
    <p id="stats-text">Loading...</p>
    <div style="font-size: 0.75rem; color: #64748b; display: flex; align-items: center; gap: 12px;">
        <div style="padding: 8px; background: rgba(59, 130, 246, 0.1); border-radius: 6px; border-left: 3px solid #3b82f6; display: flex; align-items: center; gap: 8px;">
            <span style="color: #94a3b8;">Last Updated:</span>
            <span style="color: #3b82f6; font-weight: 700;">LAST_UPDATE_PLACEHOLDER</span>
        </div>
        <span style="color: #94a3b8;">•</span>
        <span style="color: #94a3b8;">Arcs are offset by date. Arrows indicate directed action.</span>
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
        <a href="sport_report.html" class="nav-link">⚽ Sport</a>
        <a href="finance_report.html" class="nav-link">💰 Finance</a>
        <a href="elections_report.html" class="nav-link">🗳️ Elections</a>
    </div>
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
    
    """ + zone_coords_js + """
    
    function onZoneChange(zoneName) {
        const coords = ZONE_COORDS[zoneName];
        if (coords) {
            map.setView(coords, 5, { animate: true, duration: 0.5 });
        }
        updateVisibility();
    }

    function updateZoneCounts() {
        const selectedCats = Array.from(document.querySelectorAll('.filter-box input[type="checkbox"]:not(.zone-radio)')).filter(i => i.checked).map(i => i.id);
        
        const zoneCounts = {};
        const zoneVolumes = {};
        linesData.forEach(market => {
            if (selectedCats.includes(market.cat)) {
                market.zones.forEach(zone => {
                    zoneCounts[zone] = (zoneCounts[zone] || 0) + 1;
                    zoneVolumes[zone] = (zoneVolumes[zone] || 0) + (market.vol || 0);
                });
            }
        });
        
        function formatVol(vol) {
            if (vol >= 1000000) return '$' + (vol / 1000000).toFixed(1) + 'M';
            if (vol >= 1000) return '$' + (vol / 1000).toFixed(0) + 'K';
            return '$' + Math.round(vol);
        }
        
        document.querySelectorAll('.zone-radio').forEach(radio => {
            const zone = radio.getAttribute('data-zone');
            const count = zoneCounts[zone] || 0;
            const volume = zoneVolumes[zone] || 0;
            const label = document.querySelector(`label[for='${radio.id}']`);
            if (label) {
                label.textContent = `${zone} (${count}) - ${formatVol(volume)}`;
            }
        });
    }

    function updateVisibility() {
        const selectedCats = Array.from(document.querySelectorAll('.filter-box input[type="checkbox"]:not(.zone-radio)')).filter(i => i.checked).map(i => i.id);
        const selectedRadio = document.querySelector('.zone-radio:checked');
        const selectedZones = selectedRadio ? [selectedRadio.getAttribute('data-zone')] : [];

        let visibleCount = 0;
        for (const pairKey in groupLayers) {
            const group = marketGroups[pairKey];
            
            const arcEndpoints = group.pair; 
            const arcMatchesFilter = arcEndpoints.some(zone => selectedZones.includes(zone));
            
            if (!arcMatchesFilter) {
                const layerGroup = groupLayers[pairKey];
                if (map.hasLayer(layerGroup)) map.removeLayer(layerGroup);
                continue;
            }
            
            const visibleMarkets = group.markets.filter(m => 
                selectedCats.includes(m.cat) && m.zones.some(z => selectedZones.includes(z))
            );

            visibleMarkets.sort((a, b) => a.date.localeCompare(b.date));

            const layerGroup = groupLayers[pairKey];
            if (visibleMarkets.length > 0) {
                if (!map.hasLayer(layerGroup)) map.addLayer(layerGroup);
                visibleCount += visibleMarkets.length;
                
                const maxProb = Math.max(...visibleMarkets.map(m => m.price));
                const newColor = getProbColor(maxProb);
                group.polyline.setStyle({ color: newColor });
                group.hitbox.setStyle({ color: 'transparent' }); 

                let tooltipHtml = `<div class="line-tooltip"><div style="font-weight:700; color:white; margin-bottom:6px; border-bottom:1px solid #475569; padding-bottom:4px;">${group.pair[0]} & ${group.pair[1]}</div>`;
                
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
                    
                    base = base.replace(new RegExp(`-(${preps})-(${months}|\\\\d{1,2}|\\\\d{4})(-(\\\\d{1,2}|\\\\d{4}))?(-.*)?$`, "i"), '');
                    base = base.replace(new RegExp(`-(${months})(-(\\\\d{1,2}|\\\\d{4}))?(-(\\\\d{4}))?$`, "i"), '');
                    base = base.replace(new RegExp(`-(\\\\d{1,2})-(${months})(-.*)?$`, "i"), '');
                    base = base.replace(/-(2024|2025|2026|2027|2028)$/, '');
                    base = base.replace(/^will-/, '').replace(/-?any-?$/, '').replace(/-?daily-?$/, '').replace(/-?weekly-?$/, '');
                    return base.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                }

                tooltipHtml += `<button class="snapshot-btn" onclick="captureTooltipSnapshot(this)" title="Save tooltip as image">📷 Save as Image</button>`;

                const sortedCats = Object.keys(groups).sort();
                const tooltipId = `tooltip-${group.pair[0].replace(/[^a-zA-Z0-9]/g, '-')}-${group.pair[1].replace(/[^a-zA-Z0-9]/g, '-')}-${Date.now()}`;
                
                // Create tabs
                tooltipHtml += `<div class="tooltip-tabs" id="${tooltipId}-tabs">`;
                sortedCats.forEach((cat, idx) => {
                    const tabId = `${tooltipId}-tab-${idx}`;
                    const activeClass = idx === 0 ? 'active' : '';
                    tooltipHtml += `<div class="tooltip-tab ${activeClass}" onclick="switchTooltipTab('${tooltipId}', ${idx})" id="${tabId}">${cat}</div>`;
                });
                tooltipHtml += `</div>`;
                
                // Create tab contents
                sortedCats.forEach((cat, idx) => {
                    const contentId = `${tooltipId}-content-${idx}`;
                    const activeClass = idx === 0 ? 'active' : '';
                    tooltipHtml += `<div class="tooltip-tab-content ${activeClass}" id="${contentId}">`;
                    
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
                                <span style="font-weight:700; color:#94a3b8;">[Vol: $${volStr}]</span> 
                                <a href="${polyLink}" target="_blank" style="margin-left:5px; margin-right:5px;">${m.q}</a>
                                <span style="color:${color}; font-weight:800;">${Math.round(m.price * 100)}%</span>
                            </div>`;
                        });
                    });
                    
                    tooltipHtml += `</div>`;
                });
                
                tooltipHtml += `</div>`;
                group.content = tooltipHtml;
            } else {
                if (map.hasLayer(layerGroup)) map.removeLayer(layerGroup);
            }
        }
        document.getElementById('stats-text').innerText = `Visualizing ${visibleCount} conflict bets.`;
    }

    const groupLayers = {}; 
    const marketGroups = {};

    try {
        linesData.forEach(l => {
            const pair = l.zones.sort();
            const pairKey = pair.join("-");
            if (!marketGroups[pairKey]) {
                const srcCoords = ZONE_COORDS[pair[0]] || [l.src_lat, l.src_lng];
                const tgtCoords = ZONE_COORDS[pair[1]] || [l.tgt_lat, l.tgt_lng];
                
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
            const itemGroup = L.layerGroup();
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
        updateZoneCounts();
        updateVisibility();
    } catch (err) { console.error(err); }
    
    function switchTooltipTab(tooltipId, tabIndex) {
        const tabsContainer = document.getElementById(`${tooltipId}-tabs`);
        if (!tabsContainer) return;
        
        const tabs = tabsContainer.querySelectorAll('.tooltip-tab');
        const allContents = [];
        let idx = 0;
        while (true) {
            const content = document.getElementById(`${tooltipId}-content-${idx}`);
            if (!content) break;
            allContents.push(content);
            idx++;
        }
        
        // Update tabs
        tabs.forEach((tab, idx) => {
            if (idx === tabIndex) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });
        
        // Update contents
        allContents.forEach((content, idx) => {
            if (idx === tabIndex) {
                content.classList.add('active');
            } else {
                content.classList.remove('active');
            }
        });
    }
    
    function captureTooltipSnapshot(button) {
        const tooltipElement = button.closest('.line-tooltip');
        if (!tooltipElement) {
            console.error('Tooltip element not found');
            return;
        }
        
        const originalDisplay = button.style.display;
        button.style.display = 'none';
        
        const headerText = tooltipElement.querySelector('div').textContent || 'tooltip';
        const filename = headerText.replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_]/g, '') + '_' + new Date().toISOString().slice(0, 10) + '.png';
        
        if (typeof html2canvas !== 'undefined') {
            html2canvas(tooltipElement, {
                backgroundColor: '#0f172a',
                scale: 2,
                logging: false,
                useCORS: true
            }).then(canvas => {
                canvas.toBlob(function(blob) {
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
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.style.background = '';
                    }, 1500);
                }, 'image/png');
            }).catch(err => {
                console.error('Error capturing tooltip:', err);
                button.style.display = originalDisplay;
                alert('Failed to capture tooltip. Please try again.');
            });
        } else {
            button.style.display = originalDisplay;
            alert('html2canvas library not loaded. Please refresh the page.');
        }
    }
</script>
</body>
</html>
"""
        
        final_html = html_template.replace("JSON_LINES_PLACEHOLDER", json_lines)
        final_html = final_html.replace("LAST_UPDATE_PLACEHOLDER", current_time)
        final_html = final_html.replace("ZONE_FILTERS_PLACEHOLDER", zone_checks)
        
        return final_html


def main():
    generator = ConflictMapGenerator()
    generator.run()


if __name__ == "__main__":
    main()
