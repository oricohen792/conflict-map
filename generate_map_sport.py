#!/usr/bin/env python3
"""
Generate sport map from saved Polymarket data - uses base class
Shows sport events as flags at their locations
"""
import json
from datetime import datetime, timezone
from map_base import MapGeneratorBase, ZONE_COORD_MAP

# Category Keywords for sports
SPORT_KEYWORDS = {
    "Football": ["football", "nfl", "super bowl", "ncaa", "college football", "nfl game", "touchdown", "quarterback"],
    "Basketball": ["basketball", "nba", "ncaa basketball", "march madness", "nba game", "basketball game"],
    "Baseball": ["baseball", "mlb", "world series", "baseball game", "mlb game"],
    "Soccer": ["soccer", "football match", "premier league", "champions league", "world cup", "fifa", "euro", "copa"],
    "Tennis": ["tennis", "wimbledon", "us open", "french open", "australian open", "atp", "wta"],
    "Hockey": ["hockey", "nhl", "stanley cup", "hockey game"],
    "Other Sports": ["golf", "boxing", "mma", "ufc", "olympics", "racing", "formula", "nascar", "cricket", "rugby"]
}

# Combined list for initial check
all_sport_keywords = []
for k in SPORT_KEYWORDS.values():
    all_sport_keywords.extend(k)

# Exclusion keywords - markets containing these should NOT be considered sports
EXCLUSION_KEYWORDS = [
    "inflation", "cpi", "consumer price index", "economic", "economy", "gdp", "unemployment",
    "interest rate", "fed rate", "federal reserve", "central bank", "monetary policy",
    "stock market", "dow", "nasdaq", "s&p", "sp500", "market crash", "recession",
    "election", "president", "senate", "congress", "vote", "polling", "candidate",
    "war", "conflict", "military", "attack", "invasion", "sanctions", "trade war",
    "crypto", "bitcoin", "ethereum", "cryptocurrency", "blockchain", "nft"
]


class SportMapGenerator(MapGeneratorBase):
    """Sport map generator - shows sport events as flags at locations"""
    
    def __init__(self):
        super().__init__("Sport Events Map Generator", "sport_report.html")
    
    def filter_markets(self):
        """Filter and categorize sport markets"""
        event_data = []
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        print("Filtering and categorizing sport events...")
        
        for m in self.markets:
            q = m.get("question", "")
            q_lower = q.lower()
            vol = float(m.get("volume", 0) or 0)
            price = float(m.get("lastTradePrice", 0) or 0)
            end_date = m.get("endDate", "")[:10]
            
            # First check for exclusion keywords - skip non-sport markets
            if any(excl in q_lower for excl in EXCLUSION_KEYWORDS):
                continue
            
            assigned_cat = "Other Sports"
            for cat, keywords in SPORT_KEYWORDS.items():
                if any(k in q_lower for k in keywords):
                    assigned_cat = cat
                    break
            
            if assigned_cat == "Other Sports" and not any(k in q_lower for k in all_sport_keywords):
                continue
                
            # Find location(s) mentioned in the question
            found_zones = self.find_zones_in_text(q)
            
            # Use first zone found, or default to a central location if none found
            if found_zones:
                zone_name = list(found_zones.keys())[0]
                coords = ZONE_COORD_MAP[zone_name]
            else:
                # Try to find any location mention, if none use default
                continue  # Skip if no location found
            
            parent_slug = m.get("slug", "")
            events = m.get("events", [])
            if events and len(events) > 0:
                parent_slug = events[0].get("slug", parent_slug)
            
            event_data.append({
                "id": m.get("id", ""),
                "unique_id": f"E{len(event_data)}", 
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

        print(f"Found {len(event_data)} sport events.")
        return event_data
    
    def generate_html(self, events):
        """Generate HTML map from filtered sport event data"""
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        json_events = json.dumps(events)
        
        # Generate category filters
        category_checks = ""
        for cat in SPORT_KEYWORDS.keys():
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
        html_head = self.get_common_html_head()
        css = self.get_common_css()
        analytics_code = self.get_analytics_code()
        zone_coords_js = self.get_zone_coords_js()
        
        # Add sport-specific CSS (insert before closing </style> tag)
        sport_css = """
        .flag-icon {
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
        #zone-filters { max-height: 200px; overflow-y: auto; }
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
        
        # Insert sport_css before the closing </style> tag
        css_with_sport = css.replace("    </style>", sport_css + "    </style>")
        
        html_template = html_head + css_with_sport + analytics_code + """
</head>
<body>

<div id="map"></div>
<button id="mobile-filter-btn" style="display:none;" onclick="document.querySelector('.filter-box').classList.toggle('active')">
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"></line><line x1="4" y1="10" x2="4" y2="3"></line><line x1="12" y1="21" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="3"></line><line x1="20" y1="21" x2="20" y2="16"></line><line x1="20" y1="12" x2="20" y2="3"></line><line x1="1" y1="14" x2="7" y2="14"></line><line x1="9" y1="8" x2="15" y2="8"></line><line x1="17" y1="16" x2="23" y2="16"></line></svg>
    Filters
</button>

<div class="filter-box">
    <div class="close-filter" style="display:none;" onclick="document.querySelector('.filter-box').classList.remove('active')">&times;</div>
    <h1>Select Sports</h1>
    CATEGORY_FILTERS_PLACEHOLDER
    
    <hr style="margin: 10px 0;">
    <h1 style="margin-bottom: 8px;">Choose Zone</h1>
    <div id="zone-filters" style="max-height: 200px; overflow-y: auto;">
        ZONE_FILTERS_PLACEHOLDER
    </div>
</div>

<div class="info-box">
    <h1 style="font-size: 1.2rem;">Sport Events Map</h1>
    <p id="stats-text">Loading...</p>
    <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #334155; font-size: 0.75rem; color: #64748b;">
        <div style="margin-bottom: 6px; padding: 8px; background: rgba(59, 130, 246, 0.1); border-radius: 6px; border-left: 3px solid #3b82f6;">
            <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 2px;">Last Updated</div>
            <div style="color: #3b82f6; font-weight: 700; font-size: 0.95rem;">LAST_UPDATE_PLACEHOLDER</div>
        </div>
        Flags show sport event locations. Click flags for details.
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
        <a href="market_report.html" class="nav-link">⚔️ Conflict</a>
        <a href="finance_report.html" class="nav-link">💰 Finance</a>
        <a href="elections_report.html" class="nav-link">🗳️ Elections</a>
    </div>
</div>

</div>


<script>
    const map = L.map('map', {
        zoomControl: false,
        attributionControl: false
    }).setView([40, -100], 4); 

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 20 }).addTo(map);

    const eventsData = JSON_EVENTS_PLACEHOLDER;
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
        const selectedCats = Array.from(document.querySelectorAll('.filter-box input[type="checkbox"]:not(.zone-radio)')).filter(i => i.checked).map(i => i.id.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));
        
        const zoneCounts = {};
        const zoneVolumes = {};
        eventsData.forEach(event => {
            if (selectedCats.includes(event.cat)) {
                const zone = event.zone;
                zoneCounts[zone] = (zoneCounts[zone] || 0) + 1;
                zoneVolumes[zone] = (zoneVolumes[zone] || 0) + (event.vol || 0);
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
        const selectedCats = Array.from(document.querySelectorAll('.filter-box input[type="checkbox"]:not(.zone-radio)')).filter(i => i.checked).map(i => i.id.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));
        const selectedRadio = document.querySelector('.zone-radio:checked');
        const selectedZone = selectedRadio ? selectedRadio.getAttribute('data-zone') : null;

        // Remove all markers
        markers.forEach(marker => map.removeLayer(marker));
        markers.length = 0;

        if (!selectedZone) {
            document.getElementById('stats-text').innerText = 'Please select a zone.';
            return;
        }

        // Group events by zone
        const zoneEvents = {};
        eventsData.forEach(event => {
            const eventCat = event.cat;
            const eventZone = event.zone;
            
            if (eventZone === selectedZone && selectedCats.includes(eventCat)) {
                if (!zoneEvents[eventZone]) {
                    zoneEvents[eventZone] = [];
                }
                zoneEvents[eventZone].push(event);
            }
        });

        let visibleCount = 0;
        
        // Create markers grouped by zone
        for (const zone in zoneEvents) {
            const events = zoneEvents[zone];
            const coords = ZONE_COORDS[zone] || [events[0].lat, events[0].lng];
            
            // Group events by category
            const eventsByCat = {};
            events.forEach(event => {
                if (!eventsByCat[event.cat]) eventsByCat[event.cat] = [];
                eventsByCat[event.cat].push(event);
            });
            
            // Get max probability for color
            const maxProb = Math.max(...events.map(e => e.price));
            const color = getProbColor(maxProb);
            
            // Create flag icon
            const icon = L.divIcon({
                className: 'flag-icon',
                html: `<span style="color: ${color}; font-size: 28px;">🚩</span>`,
                iconSize: [28, 28],
                iconAnchor: [14, 28]
            });
            
            const marker = L.marker(coords, { icon: icon }).addTo(map);
            
            // Build tooltip HTML similar to conflicts
            let tooltipHtml = `<div class="line-tooltip"><div style="font-weight:700; color:white; margin-bottom:6px; border-bottom:1px solid #475569; padding-bottom:4px;">${zone}</div>`;
            
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
            
            const sortedCats = Object.keys(eventsByCat).sort();
            const tooltipId = `tooltip-${zone.replace(/[^a-zA-Z0-9]/g, '-')}-${Date.now()}`;
            
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
                eventsByCat[cat].forEach(event => {
                    const topic = getBaseTopic(event.slug, event.q);
                    if (!topics[topic]) topics[topic] = [];
                    topics[topic].push(event);
                });
                
                Object.keys(topics).forEach(topic => {
                    tooltipHtml += `<div style="font-weight:700; color:#cbd5e1; margin-top:4px; margin-bottom:2px;">${topic}</div>`;
                    topics[topic].forEach(event => {
                        const eventColor = getProbColor(event.price);
                        const volStr = event.vol >= 1000 ? (event.vol / 1000).toFixed(1) + 'k' : Math.round(event.vol);
                        const polyLink = event.url || `https://polymarket.com/event/${event.slug}`;
                        tooltipHtml += `<div style="margin-bottom:2px; font-size: 0.8rem; padding-left: 10px;">
                            <span style="font-weight:700; color:#94a3b8;">[${event.date}]</span> 
                            <span style="font-weight:700; color:#94a3b8;">[Vol: $${volStr}]</span> 
                            <a href="${polyLink}" target="_blank" style="margin-left:5px; margin-right:5px;">${event.q}</a>
                            <span style="color:${eventColor}; font-weight:800;">${Math.round(event.price * 100)}%</span>
                        </div>`;
                    });
                });
                
                tooltipHtml += `</div>`;
            });
            
            tooltipHtml += `</div>`;
            
            marker.bindPopup("", {
                closeButton: false,
                autoClose: false,
                className: 'line-popup',
                minWidth: 400,
                maxWidth: 2000,
                offset: [0, -10]
            });
            
            let popupTimeout;
            marker.on('mouseover', function(e) {
                clearTimeout(popupTimeout);
                this.setPopupContent(tooltipHtml);
                this.openPopup(e.latlng);
            });
            
            marker.on('mouseout', function(e) {
                popupTimeout = setTimeout(() => {
                    this.closePopup();
                }, 400);
            });
            
            marker.on('popupopen', function(e) {
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
            
            markers.push(marker);
            visibleCount += events.length;
        }
        
        document.getElementById('stats-text').innerText = `Visualizing ${visibleCount} sport events.`;
    }
    
    // Initialize visibility
    updateZoneCounts();
    updateVisibility();
    
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
        
        final_html = html_template.replace("JSON_EVENTS_PLACEHOLDER", json_events)
        final_html = final_html.replace("LAST_UPDATE_PLACEHOLDER", current_time)
        final_html = final_html.replace("CATEGORY_FILTERS_PLACEHOLDER", category_checks)
        final_html = final_html.replace("ZONE_FILTERS_PLACEHOLDER", zone_checks)
        
        return final_html


def main():
    generator = SportMapGenerator()
    generator.run()


if __name__ == "__main__":
    main()
