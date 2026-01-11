#!/usr/bin/env python3
"""
Detailed analysis of all unmapped markets
"""
import json
from map_base import MapGeneratorBase
from generate_map_conflict import CAT_KEYWORDS, all_keywords
from generate_map_sport import SPORT_KEYWORDS, all_sport_keywords, EXCLUSION_KEYWORDS
from generate_map_finance import FINANCE_KEYWORDS, all_finance_keywords
from generate_map_elections import ELECTION_KEYWORDS, all_election_keywords, EXCLUSION_KEYWORDS as ELECTION_EXCLUSION_KEYWORDS
from generate_map_technology import TECH_KEYWORDS, all_tech_keywords

# Define potential new categories
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

def analyze_unmapped_detailed():
    """Detailed analysis of all unmapped markets"""
    generator = MapGeneratorBase("Analyzer", "dummy.html")
    markets = generator.load_markets()
    
    if not markets:
        return
    
    # Identify mapped markets
    conflict_ids = set()
    sport_ids = set()
    finance_ids = set()
    election_ids = set()
    tech_ids = set()
    
    print("Identifying mapped markets...")
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
        
        # Check elections
        if not any(excl in q for excl in ELECTION_EXCLUSION_KEYWORDS):
            if any(k in q for k in all_election_keywords):
                found_zones = generator.find_zones_in_text(m.get("question", ""))
                if len(found_zones) >= 1 or any(k in q for k in ["president", "presidential", "senate", "congress", "supreme court"]):
                    election_ids.add(m_id)
        
        # Check technology
        if not any(excl in q for excl in EXCLUSION_KEYWORDS):
            if any(k in q for k in all_tech_keywords):
                found_zones = generator.find_zones_in_text(m.get("question", ""))
                if len(found_zones) >= 1 or any(k in q for k in ["apple", "google", "microsoft", "meta", "amazon", "nvidia", "tesla", "openai"]):
                    tech_ids.add(m_id)
    
    # Collect all unmapped markets with zones
    unmapped_markets = []
    categories = {
        "Entertainment": {"keywords": ENTERTAINMENT_KEYWORDS, "count": 0, "volume": 0, "markets": []},
        "Legal & Judiciary": {"keywords": LEGAL_KEYWORDS, "count": 0, "volume": 0, "markets": []},
        "Health & Medical": {"keywords": HEALTH_KEYWORDS, "count": 0, "volume": 0, "markets": []},
        "Weather & Climate": {"keywords": WEATHER_KEYWORDS, "count": 0, "volume": 0, "markets": []},
        "Energy & Resources": {"keywords": ENERGY_KEYWORDS, "count": 0, "volume": 0, "markets": []},
        "Space & Science": {"keywords": SPACE_KEYWORDS, "count": 0, "volume": 0, "markets": []},
        "Crypto & Blockchain": {"keywords": CRYPTO_KEYWORDS, "count": 0, "volume": 0, "markets": []}
    }
    
    print("Analyzing unmapped markets...")
    for m in markets:
        m_id = m.get("id", "")
        q = m.get("question", "")
        q_lower = q.lower()
        vol = float(m.get("volume", 0) or 0)
        
        # Skip if already mapped
        if m_id in conflict_ids or m_id in sport_ids or m_id in finance_ids or m_id in election_ids or m_id in tech_ids:
            continue
        
        # Check if has zones
        found_zones = generator.find_zones_in_text(q)
        if not found_zones:
            continue
        
        # Try to categorize
        categorized = False
        for cat_name, cat_data in categories.items():
            for subcat, keywords in cat_data["keywords"].items():
                if any(k in q_lower for k in keywords):
                    categories[cat_name]["count"] += 1
                    categories[cat_name]["volume"] += vol
                    categories[cat_name]["markets"].append({
                        "question": q,
                        "volume": vol,
                        "zones": list(found_zones.keys())
                    })
                    categorized = True
                    break
            if categorized:
                break
        
        # If not categorized, add to uncategorized list
        if not categorized:
            unmapped_markets.append({
                "question": q,
                "volume": vol,
                "zones": list(found_zones.keys()),
                "id": m_id
            })
    
    # Sort categories by volume
    sorted_cats = sorted(categories.items(), key=lambda x: x[1]["volume"], reverse=True)
    
    # Sort uncategorized by volume
    uncategorized_sorted = sorted(unmapped_markets, key=lambda x: x["volume"], reverse=True)
    
    print("\n" + "="*80)
    print("DETAILED UNMAPPED MARKETS ANALYSIS")
    print("="*80)
    
    print(f"\nTotal unmapped markets with zones: {len(unmapped_markets) + sum(c['count'] for c in categories.values())}")
    print(f"  - Categorized: {sum(c['count'] for c in categories.values())}")
    print(f"  - Uncategorized: {len(unmapped_markets)}")
    
    print(f"\n{'Category':<25} {'Markets':<12} {'Volume ($)':<20} {'Avg Vol/Market':<15}")
    print("-"*80)
    
    for cat_name, cat_data in sorted_cats:
        if cat_data["count"] > 0:
            avg_vol = cat_data["volume"] / cat_data["count"] if cat_data["count"] > 0 else 0
            vol_str = f"${cat_data['volume']:,.0f}" if cat_data["volume"] >= 1000 else f"${cat_data['volume']:.2f}"
            avg_str = f"${avg_vol:,.0f}" if avg_vol >= 1000 else f"${avg_vol:.2f}"
            print(f"{cat_name:<25} {cat_data['count']:<12} {vol_str:<20} {avg_str:<15}")
    
    # Show uncategorized summary
    uncategorized_vol = sum(m["volume"] for m in unmapped_markets)
    uncategorized_avg = uncategorized_vol / len(unmapped_markets) if unmapped_markets else 0
    vol_str = f"${uncategorized_vol:,.0f}" if uncategorized_vol >= 1000 else f"${uncategorized_vol:.2f}"
    avg_str = f"${uncategorized_avg:,.0f}" if uncategorized_avg >= 1000 else f"${uncategorized_avg:.2f}"
    print(f"{'Uncategorized':<25} {len(unmapped_markets):<12} {vol_str:<20} {avg_str:<15}")
    
    print("\n" + "="*80)
    print("TOP PRIORITY RECOMMENDATIONS (Categorized):")
    print("="*80)
    
    for i, (cat_name, cat_data) in enumerate(sorted_cats[:5], 1):
        if cat_data["count"] > 0:
            print(f"\n{i}. {cat_name}")
            print(f"   - {cat_data['count']} markets")
            print(f"   - ${cat_data['volume']:,.0f} total volume")
            print(f"   - ${cat_data['volume']/cat_data['count']:,.0f} avg volume per market")
            if cat_data["markets"]:
                print(f"   - Sample: {cat_data['markets'][0]['question'][:80]}...")
    
    print("\n" + "="*80)
    print("TOP 20 UNCategorized MARKETS (by volume):")
    print("="*80)
    
    for i, m in enumerate(uncategorized_sorted[:20], 1):
        vol_str = f"${m['volume']:,.0f}" if m['volume'] >= 1000 else f"${m['volume']:.2f}"
        zones_str = ", ".join(m['zones'][:3])
        if len(m['zones']) > 3:
            zones_str += f" (+{len(m['zones'])-3} more)"
        print(f"\n{i}. {vol_str} - {zones_str}")
        print(f"   {m['question'][:100]}...")
    
    # Analyze common words in uncategorized
    print("\n" + "="*80)
    print("COMMON WORDS IN UNCategorized MARKETS (top 30):")
    print("="*80)
    
    from collections import Counter
    all_words = []
    for m in unmapped_markets:
        words = m["question"].lower().split()
        # Filter out common words
        stop_words = {"will", "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "as", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "this", "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "what", "which", "who", "where", "when", "why", "how"}
        words = [w.strip(".,!?;:()[]{}'\"") for w in words if w.strip(".,!?;:()[]{}'\"") not in stop_words and len(w.strip(".,!?;:()[]{}'\"")) > 2]
        all_words.extend(words)
    
    word_counts = Counter(all_words)
    print("\nTop 30 words:")
    for word, count in word_counts.most_common(30):
        print(f"  {word}: {count}")
    
    return {
        "categorized": dict(sorted_cats),
        "uncategorized": unmapped_markets,
        "uncategorized_count": len(unmapped_markets),
        "uncategorized_volume": uncategorized_vol
    }

if __name__ == "__main__":
    analyze_unmapped_detailed()
