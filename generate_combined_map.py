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
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <style>
        #map {{ position: relative; }}
        #globe-container {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; }}
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
        
        category_filters_html += f'<div id="category-filters-{map_type}" class="category-filters" style="display: none;">\n{category_checks}\n</div>\n'
    
    # CSS
    combined_css = """
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
<div id="globe-container" style="display: none;"></div>
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
    <div style="margin-bottom: 12px; padding: 8px; background: #1e293b; border-radius: 6px; border: 1px solid #475569;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
            <span style="font-size: 0.75rem; color: #94a3b8;">View Mode:</span>
            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                <input type="checkbox" id="globe-mode-toggle" onchange="toggleViewMode()" style="cursor: pointer;">
                <span style="font-size: 0.75rem; color: #e2e8f0;">🌍 Globe</span>
            </label>
        </div>
        <div style="font-size: 0.7rem; color: #64748b; margin-top: 4px;">
            <span id="view-mode-label">🗺️ Map</span>
        </div>
    </div>
    <h1>Select Map Type</h1>
    {map_selector}
    
    <hr style="margin: 10px 0;">
    <h1>Select Categories</h1>
    {category_filters_html}
    
    <hr style="margin: 10px 0;">
    <h1 style="margin-bottom: 8px;">Choose Zone <span id="total-events-count" style="font-size: 0.75rem; color: #94a3b8; font-weight: normal;">(0 events)</span></h1>
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
    let isGlobeMode = false;
    let map = null;
    let scene = null;
    let camera = null;
    let renderer = null;
    let controls = null;
    let markerGroup = null;
    let globe = null;
    
    // Initialize Leaflet Map
    function initMapMode() {{
        if (map) return; // Already initialized
        
        const mapContainer = document.getElementById('map');
        mapContainer.style.display = 'block';
        
        map = L.map('map', {{
            zoomControl: false,
            attributionControl: false,
            minZoom: 2,
            maxZoom: 18,
            worldCopyJump: false
        }}).setView([20, 0], 2);

        // Set strict bounds to prevent wrapping
        const southWest = L.latLng(-85, -180);
        const northEast = L.latLng(85, 180);
        const bounds = L.latLngBounds(southWest, northEast);
        map.setMaxBounds(bounds);
        map.setMaxBoundsViscosity(1.0);

        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            maxZoom: 18,
            noWrap: true
        }}).addTo(map);
        
        // Prevent wrapping on move
        map.on('moveend', function() {{
            const center = map.getCenter();
            const zoom = map.getZoom();
            if (center.lng < -180 || center.lng > 180) {{
                map.setView([center.lat, Math.max(-180, Math.min(180, center.lng))], zoom);
            }}
        }});
    }}
    
    // Initialize Three.js Globe
    function initGlobeMode() {{
        if (renderer) return; // Already initialized
        
        const globeContainer = document.getElementById('globe-container');
        globeContainer.style.display = 'block';
        globeContainer.style.position = 'absolute';
        globeContainer.style.top = '0';
        globeContainer.style.left = '0';
        globeContainer.style.width = '100%';
        globeContainer.style.height = '100%';
        
        // Three.js Globe Setup
        scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0f172a);
        
        camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.z = 2.5;
        
        renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        globeContainer.appendChild(renderer.domElement);
    
        // Orbit controls for rotation
        controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.minDistance = 1.5;
        controls.maxDistance = 5;
        controls.autoRotate = true;
        controls.autoRotateSpeed = 0.5;
    
    // Create globe sphere with dark theme
    const globeGeometry = new THREE.SphereGeometry(1, 64, 64);
    const textureLoader = new THREE.TextureLoader();
    
    // Try to load earth texture, fallback to dark material
    const globeMaterial = new THREE.MeshPhongMaterial({{
        color: 0x1e293b,
        shininess: 0,
        transparent: false
    }});
    
    // Try loading earth texture
    textureLoader.load(
        'https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg',
        function(texture) {{
            globeMaterial.map = texture;
            globeMaterial.needsUpdate = true;
        }},
        undefined,
        function(err) {{
            console.log('Texture load failed, using dark globe');
        }}
    );
    
        globe = new THREE.Mesh(globeGeometry, globeMaterial);
        scene.add(globe);
        
        // Add ambient light
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        scene.add(ambientLight);
        
        // Add directional light
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(5, 3, 5);
        scene.add(directionalLight);
        
        markerGroup = new THREE.Group();
        scene.add(markerGroup);
        
        // Animation loop
        function animate() {{
            requestAnimationFrame(animate);
            if (controls) controls.update();
            if (renderer && scene && camera) renderer.render(scene, camera);
        }}
        animate();
        
        // Handle window resize
        window.addEventListener('resize', () => {{
            if (camera && renderer) {{
                camera.aspect = window.innerWidth / window.innerHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(window.innerWidth, window.innerHeight);
            }}
        }});
    }}
    
    // Helper function to convert lat/lng to 3D position on sphere
    function latLngToVector3(lat, lng, radius = 1) {{
        const phi = (90 - lat) * (Math.PI / 180);
        const theta = (lng + 180) * (Math.PI / 180);
        const x = -(radius * Math.sin(phi) * Math.cos(theta));
        const z = radius * Math.sin(phi) * Math.sin(theta);
        const y = radius * Math.cos(phi);
        return new THREE.Vector3(x, y, z);
    }}
    
    const markers = [];
    
    // Raycaster for click detection
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    let tooltipOverlay = null;
    
    // Create tooltip overlay element
    function createTooltipOverlay() {{
        if (!tooltipOverlay) {{
            tooltipOverlay = document.createElement('div');
            tooltipOverlay.className = 'tooltip-overlay line-tooltip';
            tooltipOverlay.id = 'globe-tooltip';
            tooltipOverlay.style.cssText = 'position: fixed; background: rgba(15, 23, 42, 0.98); border: 1px solid #475569; color: #f1f5f9; padding: 10px; border-radius: 6px; font-size: 13px; max-width: 800px; min-width: 600px; z-index: 10000; pointer-events: auto; display: none; box-shadow: 0 4px 15px rgba(0,0,0,0.5);';
            document.body.appendChild(tooltipOverlay);
        }}
        return tooltipOverlay;
    }}
    
    // Handle mouse clicks on markers
    function onMouseClick(event) {{
        mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
        
        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObjects(markerGroup.children);
        
        if (intersects.length > 0) {{
            const marker = intersects[0].object;
            const zone = marker.zoneName;
            const safe_id = zone.replace(/ /g, '_').replace(/\./g, '');
            const radio = document.getElementById(`zone_${{safe_id}}`);
            if (radio) {{
                radio.checked = true;
                updateVisibility();
                if (marker.tooltipHtml) {{
                    showTooltip(event.clientX, event.clientY, marker.tooltipHtml);
                }}
            }}
        }}
    }}
    
    // Handle mouse move for hover
    function onMouseMove(event) {{
        mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
        
        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObjects(markerGroup.children);
        
        if (intersects.length > 0) {{
            const marker = intersects[0].object;
            if (marker.tooltipHtml) {{
                showTooltip(event.clientX, event.clientY, marker.tooltipHtml);
            }}
        }} else {{
            hideTooltip();
        }}
    }}
    
    function showTooltip(x, y, html) {{
        const tooltip = createTooltipOverlay();
        tooltip.innerHTML = html;
        tooltip.style.display = 'block';
        // Position tooltip, but keep it on screen
        const tooltipWidth = 800;
        const tooltipHeight = 400;
        let leftPos = x + 10;
        let topPos = y + 10;
        
        // Adjust if tooltip would go off screen
        if (leftPos + tooltipWidth > window.innerWidth) {{
            leftPos = x - tooltipWidth - 10;
        }}
        if (topPos + tooltipHeight > window.innerHeight) {{
            topPos = window.innerHeight - tooltipHeight - 10;
        }}
        if (leftPos < 0) leftPos = 10;
        if (topPos < 0) topPos = 10;
        
        tooltip.style.left = leftPos + 'px';
        tooltip.style.top = topPos + 'px';
    }}
    
    function hideTooltip() {{
        if (tooltipOverlay) {{
            tooltipOverlay.style.display = 'none';
        }}
    }}
    
    // Toggle between globe and map mode
    function toggleViewMode() {{
        const toggle = document.getElementById('globe-mode-toggle');
        isGlobeMode = toggle.checked;
        const mapContainer = document.getElementById('map');
        const globeContainer = document.getElementById('globe-container');
        const viewModeLabel = document.getElementById('view-mode-label');
        
        if (isGlobeMode) {{
            mapContainer.style.display = 'none';
            globeContainer.style.display = 'block';
            viewModeLabel.textContent = '🌍 Globe';
            initGlobeMode();
            // Re-attach event listeners if renderer exists
            setTimeout(() => {{
                if (renderer && renderer.domElement) {{
                    renderer.domElement.addEventListener('click', onMouseClick);
                    renderer.domElement.addEventListener('mousemove', onMouseMove);
                }}
            }}, 100);
        }} else {{
            globeContainer.style.display = 'none';
            mapContainer.style.display = 'block';
            viewModeLabel.textContent = '🗺️ Map';
            initMapMode();
            if (renderer && renderer.domElement) {{
                renderer.domElement.removeEventListener('click', onMouseClick);
                renderer.domElement.removeEventListener('mousemove', onMouseMove);
            }}
        }}
        
        // Update visibility to show markers in current mode
        updateVisibility();
    }}
    
    // Initialize with map mode by default
    initMapMode();

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
            const checked = ''; // Don't auto-select any zone
            const count = all_zones[z];
            const volume = zone_volumes[z] || 0;
            const radio = document.createElement('div');
            radio.className = 'filter-item';
            radio.innerHTML = `<input type="radio" name="zone" class="zone-radio" id="zone_${{safe_id}}" data-zone="${{z}}" ${{checked}} onchange="onZoneChange('${{z}}')"> <label for="zone_${{safe_id}}">${{z}} <span style="color: #94a3b8; font-size: 0.85rem;">(${{count}} events, ${{formatVol(volume)}})</span></label>`;
            zoneFiltersDiv.appendChild(radio);
        }});
    }}
    
    function onZoneChange(zoneName) {{
        const coords = ZONE_COORDS[zoneName];
        if (coords) {{
            const [lat, lng] = coords;
            if (isGlobeMode && camera) {{
                const targetPos = latLngToVector3(lat, lng, 1.0);
                // Animate camera to look at selected zone
                const startPos = camera.position.clone();
                const endPos = new THREE.Vector3(targetPos.x * 2.2, targetPos.y * 2.2, targetPos.z * 2.2);
                let progress = 0;
                const animateCamera = () => {{
                    progress += 0.03;
                    if (progress < 1) {{
                        camera.position.lerpVectors(startPos, endPos, progress);
                        camera.lookAt(targetPos);
                        requestAnimationFrame(animateCamera);
                    }} else {{
                        camera.lookAt(targetPos);
                    }}
                }};
                animateCamera();
            }} else if (map) {{
                map.setView([lat, lng], 5, {{ animate: true, duration: 0.5 }});
            }}
        }}
        updateVisibility();
        
        // After visibility updates, show tooltip for selected zone marker
        setTimeout(() => {{
            const selectedMarker = markers.find(m => m.zoneName === zoneName);
            if (selectedMarker && selectedMarker.tooltipHtml) {{
                if (isGlobeMode) {{
                    const tooltip = createTooltipOverlay();
                    tooltip.innerHTML = selectedMarker.tooltipHtml;
                    tooltip.style.display = 'block';
                    tooltip.style.left = (window.innerWidth / 2) + 'px';
                    tooltip.style.top = (window.innerHeight / 2) + 'px';
                    tooltip.style.transform = 'translate(-50%, -50%)';
                }} else if (selectedMarker.openPopup) {{
                    selectedMarker.setPopupContent(selectedMarker.tooltipHtml);
                    selectedMarker.openPopup(selectedMarker.getLatLng());
                }}
            }}
        }}, isGlobeMode ? 500 : 150);
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
        if (isGlobeMode && markerGroup) {{
            markers.forEach(marker => markerGroup.remove(marker));
        }} else if (map) {{
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
        document.getElementById('total-events-count').innerText = `(${{totalCount}} events)`;

        // If no zone selected, show all markers but don't center
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
                
                tooltipHtml += `<div class="tooltip-tabs" id="${{tooltipId}}-tabs">`;
                sortedCats.forEach((cat, idx) => {{
                    const tabId = `${{tooltipId}}-tab-${{idx}}`;
                    const activeClass = idx === 0 ? 'active' : '';
                    tooltipHtml += `<div class="tooltip-tab ${{activeClass}}" onclick="switchTooltipTab('${{tooltipId}}', ${{idx}})" id="${{tabId}}">${{cat}}</div>`;
                }});
                tooltipHtml += `</div>`;
                
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
                if (isGlobeMode && markerGroup) {{
                    // Create 3D marker on globe
                    const position = latLngToVector3(lat, lng, 1.02);
                    const markerGeometry = new THREE.SphereGeometry(0.02, 16, 16);
                    const markerMaterial = new THREE.MeshBasicMaterial({{ color: color, opacity: 0.8, transparent: true }});
                    marker = new THREE.Mesh(markerGeometry, markerMaterial);
                    marker.position.copy(position);
                    marker.zoneName = zone;
                    marker.tooltipHtml = tooltipHtml;
                    marker.lat = lat;
                    marker.lng = lng;
                    markerGroup.add(marker);
                }} else if (map) {{
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
                    
                    marker.on('click', function(e) {{
                        const safe_id = zone.replace(/ /g, '_').replace(/\./g, '');
                        const radio = document.getElementById(`zone_${{safe_id}}`);
                        if (radio) {{
                            radio.checked = true;
                            updateVisibility();
                            setTimeout(() => {{
                                const selectedMarker = markers.find(m => m.zoneName === zone);
                                if (selectedMarker && selectedMarker.tooltipHtml) {{
                                    selectedMarker.setPopupContent(selectedMarker.tooltipHtml);
                                    selectedMarker.openPopup(selectedMarker.getLatLng());
                                }}
                            }}, 150);
                        }}
                    }});
                }}
                
                if (marker) {{
                    markers.push(marker);
                }}
            }});
            return;
        }}

        // Center camera/map on selected zone
        const selectedCoords = ZONE_COORDS[selectedZone];
        if (selectedCoords) {{
            const [lat, lng] = selectedCoords;
            if (isGlobeMode && camera) {{
                const targetPos = latLngToVector3(lat, lng, 1.0);
                // Animate camera to look at selected zone
                const startPos = camera.position.clone();
                const endPos = new THREE.Vector3(targetPos.x * 2.2, targetPos.y * 2.2, targetPos.z * 2.2);
                let progress = 0;
                const animateCamera = () => {{
                    progress += 0.03;
                    if (progress < 1) {{
                        camera.position.lerpVectors(startPos, endPos, progress);
                        camera.lookAt(targetPos);
                        requestAnimationFrame(animateCamera);
                    }} else {{
                        camera.lookAt(targetPos);
                    }}
                }};
                animateCamera();
            }} else if (map) {{
                map.setView([lat, lng], 5, {{ animate: true, duration: 0.5 }});
            }}
        }}

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
            
            // Highlight selected zone with larger marker
            const isSelected = zone === selectedZone;
            const [lat, lng] = coords;
            let marker;
            
            if (isGlobeMode && markerGroup) {{
                const position = latLngToVector3(lat, lng, isSelected ? 1.05 : 1.02);
                const markerSize = isSelected ? 0.04 : 0.02;
                const markerGeometry = new THREE.SphereGeometry(markerSize, 16, 16);
                const markerMaterial = new THREE.MeshBasicMaterial({{
                    color: color,
                    opacity: isSelected ? 1.0 : 0.6,
                    transparent: true
                }});
                marker = new THREE.Mesh(markerGeometry, markerMaterial);
                marker.position.copy(position);
                marker.zoneName = zone;
                markerGroup.add(marker);
            }} else if (map) {{
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
                
                marker.on('click', function(e) {{
                    const safe_id = zone.replace(/ /g, '_').replace(/\./g, '');
                    const radio = document.getElementById(`zone_${{safe_id}}`);
                    if (radio) {{
                        radio.checked = true;
                        updateVisibility();
                        setTimeout(() => {{
                            const selectedMarker = markers.find(m => m.zoneName === zone);
                            if (selectedMarker && selectedMarker.tooltipHtml) {{
                                selectedMarker.setPopupContent(selectedMarker.tooltipHtml);
                                selectedMarker.openPopup(selectedMarker.getLatLng());
                            }}
                        }}, 150);
                    }}
                }});
            }}
            
            if (isSelected) {{
                selectedZoneCount += events.length;
            }}
            visibleCount += events.length;
            
            // Make marker interactive
            marker.userData = {{ zone: zone, events: events }};
            
            // Build tooltip HTML for all zones
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
            
            // Store zone name and tooltip HTML on marker
            marker.tooltipHtml = tooltipHtml;
            marker.lat = lat;
            marker.lng = lng;
            markers.push(marker);
            visibleCount += events.length;
        }}
        
        document.getElementById('total-events-count').innerText = `(${{visibleCount}} events)`;
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
