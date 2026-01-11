#!/usr/bin/env python3
"""
Analyze unmapped markets to prioritize new map categories by volume
"""
import json
from map_base import MapGeneratorBase
from generate_map_conflict import CAT_KEYWORDS, all_keywords
from generate_map_sport import SPORT_KEYWORDS, all_sport_keywords, EXCLUSION_KEYWORDS
from generate_map_finance import FINANCE_KEYWORDS, all_finance_keywords

# Define potential new categories
ELECTION_KEYWORDS = {
    "Presidential": ["president", "presidential election", "presidential nomination", "presidential nominee"],
    "Congressional": ["senate", "congress", "senator", "representative", "house of representatives"],
    "Supreme Court": ["supreme court", "scotus", "justice", "judge"],
    "State/Local": ["governor", "mayor", "state election", "local election"],
    "Voting": ["vote", "polling", "ballot", "referendum", "primary", "caucus"]
}

TECH_KEYWORDS = {
    "Product Launches": ["product launch", "announcement", "release", "unveil"],
    "Companies": ["apple", "google", "microsoft", "tesla", "meta", "amazon", "nvidia"],
    "AI/ML": ["ai", "artificial intelligence", "chatgpt", "gpt", "machine learning", "llm"],
    "Conferences": ["ces", "wwdc", "google i/o", "developer conference"]
}

ENTERTAINMENT_KEYWORDS = {
    "Awards": ["oscar", "emmy", "grammy", "golden globe", "tony", "award"],
    "Movies/TV": ["movie", "film", "tv show", "series", "premiere", "box office"],
    "Streaming": ["netflix", "disney", "hbo", "streaming", "disney+"],
    "Celebrity": ["celebrity", "actor", "actress", "director"]
}

LEGAL_KEYWORDS = {
    "Court Cases": ["court", "trial", "lawsuit", "verdict", "ruling", "appeal"],
    "Supreme Court": ["supreme court", "scotus", "justice"],
    "Legal": ["legal", "law", "attorney", "prosecutor"]
}

HEALTH_KEYWORDS = {
    "Pandemics": ["pandemic", "covid", "coronavirus", "outbreak", "epidemic"],
    "Medical": ["vaccine", "fda", "clinical trial", "drug", "medical", "health"],
    "Diseases": ["disease", "cancer", "treatment", "therapy"]
}

WEATHER_KEYWORDS = {
    "Natural Disasters": ["hurricane", "earthquake", "tornado", "flood", "wildfire", "tsunami", "disaster"],
    "Climate": ["climate", "temperature", "weather", "storm", "extreme weather"]
}

ENERGY_KEYWORDS = {
    "Oil & Gas": ["oil", "gas", "petroleum", "crude", "barrel", "opec"],
    "Renewable": ["renewable", "solar", "wind", "energy", "power"]
}

SPACE_KEYWORDS = {
    "Space Missions": ["spacex", "nasa", "rocket", "launch", "mission", "mars", "moon"],
    "Science": ["satellite", "discovery", "science", "astronaut"]
}

CRYPTO_KEYWORDS = {
    "Cryptocurrency": ["bitcoin", "ethereum", "crypto", "blockchain", "defi", "nft"],
    "Exchanges": ["coinbase", "binance", "exchange"]
}

def analyze_unmapped():
    """Analyze unmapped markets and categorize them"""
    generator = MapGeneratorBase("Analyzer", "dummy.html")
    markets = generator.load_markets()
    
    if not markets:
        return
    
    # Identify mapped markets
    conflict_ids = set()
    sport_ids = set()
    finance_ids = set()
    
    for m in markets:
        q = m.get("question", "").lower()
        m_id = m.get("id", "")
        
        # Check conflict
        if any(k in q for k in all_keywords):
            found_zones = generator.find_zones_in_text(m.get("question", ""))
            if len(found_zones) >= 2:
                conflict_ids.add(m_id)
        
        # Check sport
        if not any(excl in q for excl in EXCLUSION_KEYWORDS):
            if any(k in q for k in all_sport_keywords):
                found_zones = generator.find_zones_in_text(m.get("question", ""))
                if len(found_zones) >= 1:
                    sport_ids.add(m_id)
        
        # Check finance
        if not any(excl in q for excl in EXCLUSION_KEYWORDS):
            if any(k in q for k in all_finance_keywords):
                found_zones = generator.find_zones_in_text(m.get("question", ""))
                if len(found_zones) >= 1 or any(k in q for k in ["fed", "federal reserve", "fomc"]):
                    finance_ids.add(m_id)
    
    # Analyze unmapped markets
    categories = {
        "Elections & Politics": {"keywords": ELECTION_KEYWORDS, "count": 0, "volume": 0, "markets": []},
        "Technology": {"keywords": TECH_KEYWORDS, "count": 0, "volume": 0, "markets": []},
        "Entertainment": {"keywords": ENTERTAINMENT_KEYWORDS, "count": 0, "volume": 0, "markets": []},
        "Legal & Judiciary": {"keywords": LEGAL_KEYWORDS, "count": 0, "volume": 0, "markets": []},
        "Health & Medical": {"keywords": HEALTH_KEYWORDS, "count": 0, "volume": 0, "markets": []},
        "Weather & Climate": {"keywords": WEATHER_KEYWORDS, "count": 0, "volume": 0, "markets": []},
        "Energy & Resources": {"keywords": ENERGY_KEYWORDS, "count": 0, "volume": 0, "markets": []},
        "Space & Science": {"keywords": SPACE_KEYWORDS, "count": 0, "volume": 0, "markets": []},
        "Crypto & Blockchain": {"keywords": CRYPTO_KEYWORDS, "count": 0, "volume": 0, "markets": []}
    }
    
    for m in markets:
        m_id = m.get("id", "")
        q = m.get("question", "")
        q_lower = q.lower()
        vol = float(m.get("volume", 0) or 0)
        
        # Skip if already mapped
        if m_id in conflict_ids or m_id in sport_ids or m_id in finance_ids:
            continue
        
        # Check if has zones
        found_zones = generator.find_zones_in_text(q)
        if not found_zones:
            # For elections, default to US if no zone found
            if any(k in q_lower for k in ["president", "presidential", "election", "senate", "congress", "supreme court"]):
                found_zones = {"United States": None}
            else:
                continue
        
        # Categorize
        for cat_name, cat_data in categories.items():
            matched = False
            for subcat, keywords in cat_data["keywords"].items():
                if any(k in q_lower for k in keywords):
                    categories[cat_name]["count"] += 1
                    categories[cat_name]["volume"] += vol
                    categories[cat_name]["markets"].append({
                        "question": q,
                        "volume": vol,
                        "zones": list(found_zones.keys())
                    })
                    matched = True
                    break
            if matched:
                break
    
    # Sort by volume
    sorted_cats = sorted(categories.items(), key=lambda x: x[1]["volume"], reverse=True)
    
    print("\n" + "="*80)
    print("UNMAPPED MARKETS ANALYSIS - PRIORITIZED BY VOLUME")
    print("="*80)
    print(f"\n{'Category':<25} {'Markets':<12} {'Volume ($)':<20} {'Avg Vol/Market':<15}")
    print("-"*80)
    
    for cat_name, cat_data in sorted_cats:
        if cat_data["count"] > 0:
            avg_vol = cat_data["volume"] / cat_data["count"] if cat_data["count"] > 0 else 0
            vol_str = f"${cat_data['volume']:,.0f}" if cat_data["volume"] >= 1000 else f"${cat_data['volume']:.2f}"
            avg_str = f"${avg_vol:,.0f}" if avg_vol >= 1000 else f"${avg_vol:.2f}"
            print(f"{cat_name:<25} {cat_data['count']:<12} {vol_str:<20} {avg_str:<15}")
    
    print("\n" + "="*80)
    print("TOP PRIORITY RECOMMENDATIONS:")
    print("="*80)
    
    for i, (cat_name, cat_data) in enumerate(sorted_cats[:5], 1):
        if cat_data["count"] > 0:
            print(f"\n{i}. {cat_name}")
            print(f"   - {cat_data['count']} markets")
            print(f"   - ${cat_data['volume']:,.0f} total volume")
            print(f"   - ${cat_data['volume']/cat_data['count']:,.0f} avg volume per market")
            if cat_data["markets"]:
                print(f"   - Sample: {cat_data['markets'][0]['question'][:70]}...")
    
    return sorted_cats

if __name__ == "__main__":
    analyze_unmapped()
