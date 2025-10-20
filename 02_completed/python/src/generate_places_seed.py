#!/usr/bin/env python3
"""
Generate comprehensive places.json seed data for 35 cities worldwide.
Creates 10 hotels + 20 restaurants + 20 activities per city = 1,750 total places.
"""

import json
from datetime import datetime

# City list
CITIES = [
    "paris", "beijing", "milan", "madrid", "rome", "barcelona", "london",
    "new_york", "chicago", "seattle", "san_francisco", "los_angeles",
    "miami", "toronto", "vancouver", "berlin", "amsterdam",
    "auckland", "christchurch", "sydney", "melbourne", "tokyo", "osaka",
    "seoul", "dubai", "abu_dhabi", "istanbul", "vienna", "frankfurt",
    "athens", "reykjavik", "stockholm", "copenhagen", "lisbon", "budapest",
    "prague", "dublin", "brussels", "zurich", "edinburgh", "glasgow",
    "oslo", "manchester", "hong_kong", "singapore", "bangkok", "kuala_lumpur"

]

# Real hotels by city (10 per city)
HOTELS = {
    "paris": [
        {"name": "Hôtel Ritz Paris", "neighborhood": "Place Vendôme", "rating": 4.9, "priceTier": "luxury", "tags": ["historic", "luxury", "spa", "michelin_restaurant"]},
        {"name": "Le Meurice", "neighborhood": "Tuileries", "rating": 4.8, "priceTier": "luxury", "tags": ["palace_hotel", "art_deco", "fine_dining"]},
        {"name": "Shangri-La Hotel Paris", "neighborhood": "16th Arrondissement", "rating": 4.8, "priceTier": "luxury", "tags": ["palace", "eiffel_view", "michelin_star"]},
        {"name": "Hôtel Plaza Athénée", "neighborhood": "Avenue Montaigne", "rating": 4.9, "priceTier": "luxury", "tags": ["fashion_district", "haute_couture", "luxury"]},
        {"name": "Hotel du Louvre", "neighborhood": "Louvre", "rating": 4.6, "priceTier": "upscale", "tags": ["central", "historic", "business"]},
        {"name": "Pullman Paris Tour Eiffel", "neighborhood": "7th Arrondissement", "rating": 4.4, "priceTier": "upscale", "tags": ["eiffel_view", "modern", "business"]},
        {"name": "Hotel Lutetia", "neighborhood": "Saint-Germain-des-Prés", "rating": 4.7, "priceTier": "luxury", "tags": ["art_nouveau", "literary", "boutique"]},
        {"name": "Le Bristol Paris", "neighborhood": "Rue du Faubourg Saint-Honoré", "rating": 4.9, "priceTier": "luxury", "tags": ["palace", "garden", "three_michelin_stars"]},
        {"name": "Hôtel des Invalides", "neighborhood": "7th Arrondissement", "rating": 4.3, "priceTier": "moderate", "tags": ["historic", "central", "affordable"]},
        {"name": "Generator Paris", "neighborhood": "10th Arrondissement", "rating": 4.1, "priceTier": "budget", "tags": ["hostel", "social", "young_travelers"]},
    ],
    "london": [
        {"name": "The Ritz London", "neighborhood": "Piccadilly", "rating": 4.8, "priceTier": "luxury", "tags": ["historic", "afternoon_tea", "royal"]},
        {"name": "Claridge's", "neighborhood": "Mayfair", "rating": 4.9, "priceTier": "luxury", "tags": ["art_deco", "luxury", "celebrity"]},
        {"name": "The Savoy", "neighborhood": "Strand", "rating": 4.8, "priceTier": "luxury", "tags": ["historic", "thames_view", "luxury"]},
        {"name": "The Dorchester", "neighborhood": "Park Lane", "rating": 4.8, "priceTier": "luxury", "tags": ["park_view", "luxury", "spa"]},
        {"name": "Shangri-La The Shard", "neighborhood": "London Bridge", "rating": 4.7, "priceTier": "luxury", "tags": ["skyline_view", "modern", "height"]},
        {"name": "The Ned", "neighborhood": "City of London", "rating": 4.6, "priceTier": "upscale", "tags": ["historic_bank", "members_club", "rooftop"]},
        {"name": "Rosewood London", "neighborhood": "Holborn", "rating": 4.7, "priceTier": "luxury", "tags": ["courtyard", "elegant", "central"]},
        {"name": "Citizen M Tower of London", "neighborhood": "Tower Hill", "rating": 4.4, "priceTier": "moderate", "tags": ["modern", "tech", "affordable"]},
        {"name": "Premier Inn London County Hall", "neighborhood": "South Bank", "rating": 4.3, "priceTier": "moderate", "tags": ["thames_view", "family", "budget"]},
        {"name": "Generator London", "neighborhood": "King's Cross", "rating": 4.2, "priceTier": "budget", "tags": ["hostel", "social", "central"]},
    ],
    "new_york": [
        {"name": "The Plaza Hotel", "neighborhood": "Midtown Manhattan", "rating": 4.7, "priceTier": "luxury", "tags": ["historic", "fifth_avenue", "iconic"]},
        {"name": "The St. Regis New York", "neighborhood": "Midtown East", "rating": 4.8, "priceTier": "luxury", "tags": ["beaux_arts", "butler_service", "luxury"]},
        {"name": "The Peninsula New York", "neighborhood": "Fifth Avenue", "rating": 4.8, "priceTier": "luxury", "tags": ["rooftop_bar", "art_deco", "luxury"]},
        {"name": "The Carlyle", "neighborhood": "Upper East Side", "rating": 4.7, "priceTier": "luxury", "tags": ["jazz_club", "residential", "elegant"]},
        {"name": "1 Hotel Brooklyn Bridge", "neighborhood": "Brooklyn", "rating": 4.6, "priceTier": "upscale", "tags": ["eco_friendly", "brooklyn_bridge_view", "modern"]},
        {"name": "The Standard High Line", "neighborhood": "Meatpacking District", "rating": 4.5, "priceTier": "upscale", "tags": ["trendy", "rooftop_bar", "hudson_river"]},
        {"name": "Ace Hotel New York", "neighborhood": "NoMad", "rating": 4.4, "priceTier": "moderate", "tags": ["hipster", "lobby_bar", "creative"]},
        {"name": "Pod 51 Hotel", "neighborhood": "Midtown East", "rating": 4.2, "priceTier": "budget", "tags": ["micro_hotel", "rooftop", "affordable"]},
        {"name": "HI NYC Hostel", "neighborhood": "Upper West Side", "rating": 4.3, "priceTier": "budget", "tags": ["hostel", "central_park", "backpackers"]},
        {"name": "The Jane Hotel", "neighborhood": "West Village", "rating": 4.1, "priceTier": "budget", "tags": ["historic", "nautical", "unique"]},
    ],
    "tokyo": [
        {"name": "The Peninsula Tokyo", "neighborhood": "Marunouchi", "rating": 4.8, "priceTier": "luxury", "tags": ["imperial_palace_view", "spa", "luxury"]},
        {"name": "Aman Tokyo", "neighborhood": "Otemachi", "rating": 4.9, "priceTier": "luxury", "tags": ["zen", "sky_lobby", "ultra_luxury"]},
        {"name": "Park Hyatt Tokyo", "neighborhood": "Shinjuku", "rating": 4.7, "priceTier": "luxury", "tags": ["lost_in_translation", "skyline_view", "modern"]},
        {"name": "The Ritz-Carlton Tokyo", "neighborhood": "Roppongi", "rating": 4.8, "priceTier": "luxury", "tags": ["tokyo_tower_view", "high_floors", "luxury"]},
        {"name": "Andaz Tokyo Toranomon Hills", "neighborhood": "Toranomon", "rating": 4.6, "priceTier": "upscale", "tags": ["modern", "rooftop_bar", "business"]},
        {"name": "Hotel Gracery Shinjuku", "neighborhood": "Shinjuku", "rating": 4.4, "priceTier": "moderate", "tags": ["godzilla_head", "central", "entertainment"]},
        {"name": "Shibuya Excel Hotel Tokyu", "neighborhood": "Shibuya", "rating": 4.3, "priceTier": "moderate", "tags": ["shibuya_crossing_view", "shopping", "convenient"]},
        {"name": "Capsule Hotel Anshin Oyado", "neighborhood": "Shinjuku", "rating": 4.1, "priceTier": "budget", "tags": ["capsule", "traditional", "unique"]},
        {"name": "Sakura Hotel Ikebukuro", "neighborhood": "Ikebukuro", "rating": 4.2, "priceTier": "budget", "tags": ["backpackers", "social", "affordable"]},
        {"name": "Khaosan Tokyo Origami", "neighborhood": "Asakusa", "rating": 4.3, "priceTier": "budget", "tags": ["hostel", "traditional_area", "friendly"]},
    ],
    "rome": [
        {"name": "Hotel Hassler Roma", "neighborhood": "Spanish Steps", "rating": 4.8, "priceTier": "luxury", "tags": ["rooftop_restaurant", "panoramic", "luxury"]},
        {"name": "Hotel de Russie", "neighborhood": "Piazza del Popolo", "rating": 4.7, "priceTier": "luxury", "tags": ["secret_garden", "elegant", "central"]},
        {"name": "The St. Regis Rome", "neighborhood": "Via Vittorio Veneto", "rating": 4.8, "priceTier": "luxury", "tags": ["baroque", "butler_service", "luxury"]},
        {"name": "Hotel Artemide", "neighborhood": "Termini", "rating": 4.5, "priceTier": "upscale", "tags": ["rooftop_terrace", "central", "modern"]},
        {"name": "Hotel Campo de' Fiori", "neighborhood": "Campo de' Fiori", "rating": 4.6, "priceTier": "upscale", "tags": ["rooftop_terrace", "market_square", "charming"]},
        {"name": "Hotel Ponte Sisto", "neighborhood": "Trastevere", "rating": 4.4, "priceTier": "moderate", "tags": ["courtyard", "bohemian", "romantic"]},
        {"name": "Hotel Nazionale", "neighborhood": "Montecitorio", "rating": 4.5, "priceTier": "moderate", "tags": ["historic", "parliament", "central"]},
        {"name": "Generator Rome", "neighborhood": "Esquilino", "rating": 4.2, "priceTier": "budget", "tags": ["hostel", "social", "modern"]},
        {"name": "The RomeHello", "neighborhood": "Termini", "rating": 4.3, "priceTier": "budget", "tags": ["hostel", "clean", "convenient"]},
        {"name": "Yellow Hostel", "neighborhood": "San Lorenzo", "rating": 4.1, "priceTier": "budget", "tags": ["party", "young", "social"]},
    ],
}

# For cities not detailed above, use generic hotel templates
GENERIC_HOTEL_TEMPLATES = [
    {"name": "{city} Grand Hotel", "neighborhood": "City Center", "rating": 4.7, "priceTier": "luxury"},
    {"name": "The {city} Palace", "neighborhood": "Historic District", "rating": 4.8, "priceTier": "luxury"},
    {"name": "Luxury Suites {city}", "neighborhood": "Downtown", "rating": 4.6, "priceTier": "upscale"},
    {"name": "{city} Plaza Hotel", "neighborhood": "Main Square", "rating": 4.5, "priceTier": "upscale"},
    {"name": "Boutique Hotel {city}", "neighborhood": "Arts Quarter", "rating": 4.4, "priceTier": "moderate"},
    {"name": "{city} Business Hotel", "neighborhood": "Business District", "rating": 4.3, "priceTier": "moderate"},
    {"name": "{city} City Hotel", "neighborhood": "Central", "rating": 4.2, "priceTier": "moderate"},
    {"name": "Budget Inn {city}", "neighborhood": "Near Station", "rating": 4.1, "priceTier": "budget"},
    {"name": "{city} Hostel", "neighborhood": "Backpacker Area", "rating": 4.0, "priceTier": "budget"},
    {"name": "Express Hotel {city}", "neighborhood": "Airport Area", "rating": 4.2, "priceTier": "budget"},
]

def generate_hotels():
    """Generate all hotel data"""
    hotels = []
    hotel_id = 1
    
    for city in CITIES:
        # Use real hotels if available, otherwise use templates
        if city in HOTELS:
            city_hotels = HOTELS[city]
        else:
            city_name = city.replace("_", " ").title()
            city_hotels = []
            for template in GENERIC_HOTEL_TEMPLATES:
                hotel = template.copy()
                hotel["name"] = template["name"].format(city=city_name)
                if "neighborhood" in template and "{city}" in template["neighborhood"]:
                    hotel["neighborhood"] = template["neighborhood"].format(city=city_name)
                city_hotels.append(hotel)
        
        for idx, hotel_data in enumerate(city_hotels):
            hotel = {
                "id": f"hotel_{city}_{hotel_id:04d}",
                "geoScopeId": city,
                "type": "hotel",
                "name": hotel_data["name"],
                "description": f"A {hotel_data['priceTier']} hotel in {hotel_data['neighborhood']}, {city.replace('_', ' ').title()}.",
                "neighborhood": hotel_data["neighborhood"],
                "rating": hotel_data.get("rating", 4.5),
                "priceTier": hotel_data["priceTier"],
                "tags": hotel_data.get("tags", ["comfortable", "clean"]),
                "accessibility": ["wheelchair-accessible"] if hotel_data.get("rating", 4.0) >= 4.5 else [],
                "hours": {
                    "monday": "00:00-23:59",
                    "tuesday": "00:00-23:59",
                    "wednesday": "00:00-23:59",
                    "thursday": "00:00-23:59",
                    "friday": "00:00-23:59",
                    "saturday": "00:00-23:59",
                    "sunday": "00:00-23:59"
                },
                "embedding": []
            }
            hotels.append(hotel)
            hotel_id += 1
    
    return hotels

def generate_restaurants():
    """Generate restaurant data - 20 per city"""
    restaurants = []
    restaurant_id = 1
    
    # Restaurant templates with variety
    restaurant_types = [
        {"suffix": "Bistro", "priceTier": "moderate", "tags": ["french", "casual"]},
        {"suffix": "Trattoria", "priceTier": "moderate", "tags": ["italian", "family"]},
        {"suffix": "Sushi Bar", "priceTier": "upscale", "tags": ["japanese", "fresh"]},
        {"suffix": "Steakhouse", "priceTier": "upscale", "tags": ["american", "meat"]},
        {"suffix": "Café", "priceTier": "budget", "tags": ["coffee", "breakfast"]},
        {"suffix": "Pizzeria", "priceTier": "budget", "tags": ["italian", "casual"]},
        {"suffix": "Fine Dining", "priceTier": "luxury", "tags": ["michelin", "gourmet"]},
        {"suffix": "Gastropub", "priceTier": "moderate", "tags": ["pub", "craft_beer"]},
        {"suffix": "Noodle House", "priceTier": "budget", "tags": ["asian", "quick"]},
        {"suffix": "Seafood Grill", "priceTier": "upscale", "tags": ["seafood", "fresh"]},
        {"suffix": "Vegetarian Kitchen", "priceTier": "moderate", "tags": ["vegetarian", "healthy"]},
        {"suffix": "BBQ Joint", "priceTier": "moderate", "tags": ["bbq", "casual"]},
        {"suffix": "Wine Bar", "priceTier": "upscale", "tags": ["wine", "tapas"]},
        {"suffix": "Ramen Shop", "priceTier": "budget", "tags": ["ramen", "japanese"]},
        {"suffix": "Burger Bar", "priceTier": "budget", "tags": ["burgers", "casual"]},
        {"suffix": "Thai Restaurant", "priceTier": "moderate", "tags": ["thai", "spicy"]},
        {"suffix": "Mexican Cantina", "priceTier": "moderate", "tags": ["mexican", "lively"]},
        {"suffix": "Indian Curry House", "priceTier": "moderate", "tags": ["indian", "curry"]},
        {"suffix": "Mediterranean Grill", "priceTier": "upscale", "tags": ["mediterranean", "healthy"]},
        {"suffix": "Dim Sum Palace", "priceTier": "moderate", "tags": ["chinese", "brunch"]},
    ]
    
    for city in CITIES:
        city_name = city.replace("_", " ").title()
        
        for idx, rest_type in enumerate(restaurant_types):
            restaurant = {
                "id": f"restaurant_{city}_{restaurant_id:04d}",
                "geoScopeId": city,
                "type": "restaurant",
                "name": f"{city_name} {rest_type['suffix']}",
                "description": f"A {rest_type['priceTier']} {rest_type['suffix'].lower()} in {city_name}.",
                "neighborhood": f"District {(idx % 5) + 1}",
                "rating": round(3.8 + (idx % 10) * 0.1, 1),
                "priceTier": rest_type["priceTier"],
                "tags": rest_type["tags"],
                "accessibility": ["wheelchair-accessible"] if idx % 3 == 0 else [],
                "hours": {
                    "monday": "11:00-22:00",
                    "tuesday": "11:00-22:00",
                    "wednesday": "11:00-22:00",
                    "thursday": "11:00-23:00",
                    "friday": "11:00-00:00",
                    "saturday": "10:00-00:00",
                    "sunday": "10:00-22:00"
                },
                "embedding": []
            }
            restaurants.append(restaurant)
            restaurant_id += 1
    
    return restaurants

def generate_activities():
    """Generate activity data - 20 per city"""
    activities = []
    activity_id = 1
    
    # Activity templates with subtypes
    activity_types = [
        {"name": "National Museum", "subtype": "museum", "priceTier": "moderate", "tags": ["history", "culture"]},
        {"name": "Art Gallery", "subtype": "museum", "priceTier": "moderate", "tags": ["art", "paintings"]},
        {"name": "Science Museum", "subtype": "museum", "priceTier": "moderate", "tags": ["science", "interactive"]},
        {"name": "Modern Art Museum", "subtype": "museum", "priceTier": "moderate", "tags": ["contemporary", "art"]},
        {"name": "City Tower", "subtype": "landmark", "priceTier": "upscale", "tags": ["viewpoint", "iconic"]},
        {"name": "Historic Cathedral", "subtype": "landmark", "priceTier": "budget", "tags": ["religious", "architecture"]},
        {"name": "Ancient Ruins", "subtype": "landmark", "priceTier": "moderate", "tags": ["history", "archaeology"]},
        {"name": "Royal Palace", "subtype": "landmark", "priceTier": "upscale", "tags": ["royal", "gardens"]},
        {"name": "Central Park", "subtype": "attraction", "priceTier": "budget", "tags": ["nature", "outdoors"]},
        {"name": "Botanical Gardens", "subtype": "attraction", "priceTier": "budget", "tags": ["flowers", "nature"]},
        {"name": "Zoo", "subtype": "attraction", "priceTier": "moderate", "tags": ["animals", "family"]},
        {"name": "Aquarium", "subtype": "attraction", "priceTier": "moderate", "tags": ["marine", "family"]},
        {"name": "Observation Deck", "subtype": "viewpoint", "priceTier": "upscale", "tags": ["panoramic", "photography"]},
        {"name": "River Cruise", "subtype": "attraction", "priceTier": "moderate", "tags": ["water", "scenic"]},
        {"name": "Street Market", "subtype": "attraction", "priceTier": "budget", "tags": ["shopping", "local"]},
        {"name": "Theme Park", "subtype": "attraction", "priceTier": "upscale", "tags": ["rides", "family"]},
        {"name": "Historic Monument", "subtype": "landmark", "priceTier": "budget", "tags": ["memorial", "historic"]},
        {"name": "Harbor Walk", "subtype": "viewpoint", "priceTier": "budget", "tags": ["waterfront", "walking"]},
        {"name": "Old Town Square", "subtype": "landmark", "priceTier": "budget", "tags": ["historic", "architecture"]},
        {"name": "Scenic Viewpoint", "subtype": "viewpoint", "priceTier": "budget", "tags": ["nature", "photography"]},
    ]
    
    for city in CITIES:
        city_name = city.replace("_", " ").title()
        
        for idx, activity_type in enumerate(activity_types):
            activity = {
                "id": f"activity_{city}_{activity_id:04d}",
                "geoScopeId": city,
                "type": "activity",
                "subtype": activity_type["subtype"],
                "name": f"{city_name} {activity_type['name']}",
                "description": f"{activity_type['name']} in {city_name} - {', '.join(activity_type['tags'])}",
                "neighborhood": f"Area {(idx % 4) + 1}",
                "rating": round(4.0 + (idx % 10) * 0.1, 1),
                "priceTier": activity_type["priceTier"],
                "tags": activity_type["tags"],
                "accessibility": ["wheelchair-accessible"] if idx % 2 == 0 else [],
                "hours": {
                    "monday": "09:00-18:00",
                    "tuesday": "09:00-18:00",
                    "wednesday": "09:00-18:00",
                    "thursday": "09:00-20:00",
                    "friday": "09:00-20:00",
                    "saturday": "09:00-20:00",
                    "sunday": "10:00-18:00"
                },
                "embedding": []
            }
            activities.append(activity)
            activity_id += 1
    
    return activities

def main():
    """Generate complete places.json file"""
    print("🏨 Generating hotels...")
    hotels = generate_hotels()
    print(f"   Generated {len(hotels)} hotels")
    
    print("🍽️  Generating restaurants...")
    restaurants = generate_restaurants()
    print(f"   Generated {len(restaurants)} restaurants")
    
    print("🎭 Generating activities...")
    activities = generate_activities()
    print(f"   Generated {len(activities)} activities")
    
    # Combine all places
    all_places = hotels + restaurants + activities
    print(f"\n📊 Total places: {len(all_places)}")
    
    # Write to JSON file
    output_file = "/Users/aayushkataria/git/travel-multi-agent-workshop/02_completed/python/data/places.json"
    print(f"\n💾 Writing to {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_places, f, indent=2, ensure_ascii=False)
    
    print("✅ places.json created successfully!")
    print(f"   File size: {len(json.dumps(all_places, indent=2)) / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    main()
