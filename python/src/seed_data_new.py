#!/usr/bin/env python3
"""
Comprehensive Data Seeding Script for Travel Assistant Cosmos DB

This script:
1. Creates all 8 required Cosmos DB containers with proper vector/full-text indexing
2. Seeds rich synthetic data for 9-10 European cities
3. Supports vector search (DiskANN, cosine similarity, 1536 dimensions)
4. Supports full-text search (en-us locale)
5. Supports hybrid search scenarios

Container List:
- threads (activeAgent tracking)
- messages (vector + full-text)
- summaries (vector + full-text)
- memories (vector + full-text)
- places (vector + full-text) - PRIMARY DATA
- trips (basic)
- api_events (basic)
- checkpoints (LangGraph state)

Run: python seed_data_new.py
"""

import json
import os
import sys
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'app'))

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceExistsError
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# Configuration
# ============================================================================

COSMOS_ENDPOINT = os.getenv("COSMOSDB_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = os.getenv("COSMOS_DB_DATABASE_NAME", "TravelAssistant")

# Azure OpenAI for embeddings
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

print(AZURE_OPENAI_ENDPOINT)
print(AZURE_OPENAI_EMBEDDING_DEPLOYMENT)


# Vector search configuration
VECTOR_DIMENSIONS = 1024
VECTOR_INDEX_TYPE = "diskANN"
SIMILARITY_METRIC = "cosine"

# Full-text search configuration
FULL_TEXT_LOCALE = "en-us"


# ============================================================================
# Cosmos DB Client Initialization
# ============================================================================

def get_cosmos_client() -> CosmosClient:
    """Initialize Cosmos DB client with Azure authentication"""

    return CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)


# ============================================================================
# Azure OpenAI Client Initialization
# ============================================================================

_openai_client = None


def get_openai_client() -> AzureOpenAI:
    """Initialize Azure OpenAI client (lazy)"""
    global _openai_client
    if _openai_client is None:
        _openai_client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION
        )
    return _openai_client


def generate_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding vector for text using Azure OpenAI"""
    if not text or not AZURE_OPENAI_ENDPOINT:
        return None

    try:
        client = get_openai_client()
        response = client.embeddings.create(
            input=text,
            model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            dimensions=1024,
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"   ⚠️  Warning: Could not generate embedding: {e}")
        return None


# ============================================================================
# Container Definitions with Vector + Full-Text Indexing
# ============================================================================

CONTAINER_CONFIGS = {
    "threads": {
        "partition_key": ["/tenantId", "/userId", "/threadId"],
        "hierarchical": True,
        "vector_search": False,
        "full_text_search": False,
        "description": "Conversation threads with activeAgent tracking"
    },
    "messages": {
        "partition_key": ["/tenantId", "/userId", "/threadId"],
        "hierarchical": True,
        "vector_search": True,
        "full_text_search": True,
        "vector_paths": ["/embedding"],
        "full_text_paths": ["/content", "/keywords"],
        "embedding_source": "content",  # Field to generate embedding from
        "description": "User and assistant messages with embeddings"
    },
    "summaries": {
        "partition_key": ["/tenantId", "/userId", "/threadId"],
        "hierarchical": True,
        "vector_search": True,
        "full_text_search": True,
        "vector_paths": ["/embedding"],
        "full_text_paths": ["/text"],
        "embedding_source": "text",  # Field to generate embedding from
        "description": "Conversation summaries with embeddings"
    },
    "memories": {
        "partition_key": ["/tenantId", "/userId", "/memoryId"],
        "hierarchical": True,
        "vector_search": True,
        "full_text_search": True,
        "vector_paths": ["/embedding"],
        "full_text_paths": ["/text"],
        "embedding_source": "text",  # Field to generate embedding from
        "description": "User memories (declarative, episodic, procedural)"
    },
    "places": {
        "partition_key": "/geoScopeId",
        "hierarchical": False,
        "vector_search": True,
        "full_text_search": True,
        "vector_paths": ["/embedding"],
        "full_text_paths": ["/name", "/description", "/tags"],
        "embedding_source": "description",  # Field to generate embedding from
        "description": "Places across European cities (restaurants, cafes, attractions)"
    },
    "trips": {
        "partition_key": ["/tenantId", "/userId", "/tripId"],
        "hierarchical": True,
        "vector_search": False,
        "full_text_search": False,
        "description": "Trip itineraries and plans"
    },
    "api_events": {
        "partition_key": ["/tenantId", "/threadId"],
        "hierarchical": True,
        "vector_search": False,
        "full_text_search": False,
        "description": "External API call logs"
    },
    "checkpoints": {
        "partition_key": "/thread_id",
        "hierarchical": False,
        "vector_search": False,
        "full_text_search": False,
        "description": "LangGraph checkpoints for state persistence"
    }
}


def create_container_with_indexing(
        database,
        container_name: str,
        config: Dict[str, Any]
) -> Any:
    """
    Create container with vector and/or full-text indexing policies
    Supports hierarchical partition keys for multi-tenant scenarios
    
    References:
    - https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/vector-search
    - https://learn.microsoft.com/en-us/azure/cosmos-db/gen-ai/sharded-diskann
    - https://learn.microsoft.com/en-us/azure/cosmos-db/gen-ai/full-text-search
    - https://learn.microsoft.com/en-us/azure/cosmos-db/gen-ai/hybrid-search
    """
    print(f"\n📦 Creating container: {container_name}")
    print(f"   Description: {config['description']}")

    # Handle hierarchical partition keys
    partition_key_config = config['partition_key']
    if config.get('hierarchical', False):
        print(f"   Partition Key: {' / '.join(partition_key_config)} (Hierarchical)")
        partition_key = PartitionKey(path=partition_key_config, kind='MultiHash')
    else:
        print(f"   Partition Key: {partition_key_config}")
        partition_key = PartitionKey(path=partition_key_config)

    # Base indexing policy
    indexing_policy = {
        "indexingMode": "consistent",
        "automatic": True,
        "includedPaths": [{"path": "/*"}],
        "excludedPaths": [{"path": "/\"_etag\"/?"}]
    }

    # Vector embedding policy for DiskANN
    vector_embedding_policy = None
    if config.get("vector_search"):
        print(f"   ✅ Vector Search: Enabled (DiskANN, cosine, {VECTOR_DIMENSIONS}d)")
        vector_embedding_policy = {
            "vectorEmbeddings": [
                {
                    "path": path,
                    "dataType": "float32",
                    "dimensions": VECTOR_DIMENSIONS,
                    "distanceFunction": SIMILARITY_METRIC
                }
                for path in config.get("vector_paths", [])
            ]
        }
        indexing_policy["vectorIndexes"] = [
            {"path": "/embedding", "type": f"{VECTOR_INDEX_TYPE}"}
        ]

    # Full-text indexing policy
    full_text_policy = None
    if config.get("full_text_search"):
        print(f"   ✅ Full-Text Search: Enabled ({FULL_TEXT_LOCALE})")
        indexing_policy["fullTextIndexes"] = [
            {
                "path": path,
                "language": FULL_TEXT_LOCALE
            }
            for path in config.get("full_text_paths", [])
        ]
        full_text_policy = {
            "defaultLanguage": "en-US",
            "fullTextPaths": [
                {
                    "path": path,
                    "language": "en-US"
                }
                for path in config.get("full_text_paths", [])
            ]
        }

    # Create container
    try:
        container = database.create_container(
            id=container_name,
            partition_key=partition_key,
            indexing_policy=indexing_policy,
            vector_embedding_policy=vector_embedding_policy,
            full_text_policy=full_text_policy,
        )
        print(f"   ✅ Created successfully")
        return container
    except CosmosResourceExistsError:
        print(f"   ⚠️  Already exists, using existing container")
        return database.get_container_client(container_name)


def create_all_containers(client: CosmosClient):
    """Create database and all containers"""
    print("=" * 70)
    print("🗄️  Creating Cosmos DB Database and Containers")
    print("=" * 70)

    # Create database
    try:
        database = client.create_database(DATABASE_NAME)
        print(f"\n✅ Database '{DATABASE_NAME}' created")
    except CosmosResourceExistsError:
        database = client.get_database_client(DATABASE_NAME)
        print(f"\n✅ Database '{DATABASE_NAME}' already exists")

    # Create all containers
    containers = {}
    for name, config in CONTAINER_CONFIGS.items():
        container = create_container_with_indexing(database, name, config)
        containers[name] = container

    print("\n" + "=" * 70)
    print(f"✅ All {len(containers)} containers ready!")
    print("=" * 70)

    return database, containers


# ============================================================================
# Synthetic Data Generation - European Cities
# ============================================================================

CITIES = [
    {"id": "barcelona", "name": "Barcelona", "country": "Spain", "lat": 41.3851, "lon": 2.1734},
    {"id": "paris", "name": "Paris", "country": "France", "lat": 48.8566, "lon": 2.3522},
    {"id": "rome", "name": "Rome", "country": "Italy", "lat": 41.9028, "lon": 12.4964},
    {"id": "amsterdam", "name": "Amsterdam", "country": "Netherlands", "lat": 52.3676, "lon": 4.9041},
    {"id": "berlin", "name": "Berlin", "country": "Germany", "lat": 52.5200, "lon": 13.4050},
    {"id": "london", "name": "London", "country": "UK", "lat": 51.5074, "lon": -0.1278},
    {"id": "prague", "name": "Prague", "country": "Czech Republic", "lat": 50.0755, "lon": 14.4378},
    {"id": "vienna", "name": "Vienna", "country": "Austria", "lat": 48.2082, "lon": 16.3738},
    {"id": "lisbon", "name": "Lisbon", "country": "Portugal", "lat": 38.7223, "lon": -9.1393},
    {"id": "budapest", "name": "Budapest", "country": "Hungary", "lat": 47.4979, "lon": 19.0402}
]

# Template data for each city type
RESTAURANT_TEMPLATES = [
    {
        "type": "vegetarian",
        "names": ["Green Garden", "Veggie Paradise", "Plant Kitchen", "Herbivore Haven", "Root & Leaf"],
        "description": "Plant-based restaurant with creative vegetarian and vegan dishes. Fresh, locally-sourced ingredients.",
        "dietary": ["vegetarian", "vegan", "gluten-free"],
        "tags": ["healthy", "modern", "eco-friendly"],
        "priceTier": 2,
        "cuisineTypes": ["vegetarian", "vegan", "international"],
        "seatingOptions": ["indoor", "outdoor"],
        "mealTypes": ["breakfast", "lunch", "dinner"]
    },
    {
        "type": "traditional",
        "names": ["Heritage Table", "Old Town Kitchen", "Traditional Tavern", "Classic Bistro", "Local Flavor"],
        "description": "Traditional local cuisine in a cozy, historic setting. Family recipes passed down through generations.",
        "dietary": ["gluten-free-options"],
        "tags": ["cozy", "traditional", "authentic", "local-favorite"],
        "priceTier": 2,
        "cuisineTypes": ["local", "traditional", "regional"],
        "seatingOptions": ["indoor"],
        "mealTypes": ["lunch", "dinner"]
    },
    {
        "type": "fine_dining",
        "names": ["Michelin Star", "The Gourmet", "Elite Dining", "Chef's Table", "Culinary Art"],
        "description": "Upscale fine dining experience with innovative cuisine. Reservations required.",
        "dietary": ["gluten-free-options"],
        "tags": ["upscale", "michelin", "romantic", "creative"],
        "priceTier": 4,
        "cuisineTypes": ["french", "fusion", "contemporary"],
        "seatingOptions": ["indoor", "private-room"],
        "mealTypes": ["dinner"]
    },
    {
        "type": "late_night",
        "names": ["Night Owl", "Midnight Kitchen", "After Hours", "Late Bite", "Moon Café"],
        "description": "Late-night dining spot perfect for night owls. Open until 2 AM on weekends.",
        "dietary": ["vegetarian-friendly"],
        "tags": ["late-night", "casual", "vibrant"],
        "priceTier": 2,
        "cuisineTypes": ["international", "comfort-food", "street-food"],
        "seatingOptions": ["indoor", "bar"],
        "mealTypes": ["dinner", "late-night"]
    },
    {
        "type": "seafood",
        "names": ["Ocean's Catch", "The Fish Market", "Seaside Grill", "Maritime Dining", "Blue Waters"],
        "description": "Fresh seafood restaurant with daily catches. Specializes in local fish preparations.",
        "dietary": ["gluten-free-options"],
        "tags": ["seafood", "fresh", "waterfront"],
        "priceTier": 3,
        "cuisineTypes": ["seafood", "mediterranean", "local"],
        "seatingOptions": ["indoor", "outdoor", "waterfront"],
        "mealTypes": ["lunch", "dinner"]
    }
]

CAFE_TEMPLATES = [
    {
        "names": ["Artisan Coffee", "Bean & Co", "Roast House", "Coffee Lab", "Espresso Bar"],
        "description": "Specialty coffee shop with artisan roasts. Perfect for remote work with fast WiFi.",
        "tags": ["specialty-coffee", "work-friendly", "modern", "wifi"],
        "priceTier": 2
    },
    {
        "names": ["Sweet Treats", "Pastry Paradise", "The Bakery", "Cake Corner", "Sugar & Spice"],
        "description": "Charming café famous for homemade pastries and desserts. Instagram-worthy presentations.",
        "tags": ["pastries", "instagram-worthy", "cozy", "desserts"],
        "priceTier": 2
    },
    {
        "names": ["Book Café", "Literary Lounge", "Reader's Rest", "Page Turner", "Chapter One"],
        "description": "Cozy café with extensive book collection. Quiet atmosphere perfect for reading.",
        "tags": ["books", "quiet", "cozy", "intellectual"],
        "priceTier": 2
    }
]

ATTRACTION_TEMPLATES = [
    {
        "type": "museum",
        "names": ["National Museum", "Art Gallery", "History Museum", "Modern Art", "Cultural Center"],
        "description": "World-class museum with extensive collection. Photography allowed in most sections.",
        "tags": ["museum", "art", "culture", "photography", "educational"],
        "priceTier": 2,
        "categories": ["art", "culture", "history"],
        "durationMinutes": 180,  # 3 hours
        "ticketRequired": True
    },
    {
        "type": "landmark",
        "names": ["Historic Cathedral", "City Palace", "Ancient Tower", "Royal Castle", "Grand Monument"],
        "description": "Iconic landmark and UNESCO World Heritage Site. Must-see architectural masterpiece.",
        "tags": ["iconic", "architecture", "unesco", "photography", "historic"],
        "priceTier": 2,
        "categories": ["architecture", "history", "unesco"],
        "durationMinutes": 120,  # 2 hours
        "ticketRequired": True
    },
    {
        "type": "park",
        "names": ["Central Park", "Botanical Gardens", "Green Space", "City Gardens", "Nature Reserve"],
        "description": "Beautiful public park perfect for leisurely walks. Great for photography and relaxation.",
        "tags": ["nature", "photography", "relaxing", "free", "scenic"],
        "priceTier": 0,
        "categories": ["nature", "outdoor", "relaxation"],
        "durationMinutes": 90,  # 1.5 hours
        "ticketRequired": False
    },
    {
        "type": "viewpoint",
        "names": ["Sky Terrace", "Panorama Point", "Observation Deck", "Vista Tower", "Overlook"],
        "description": "Breathtaking panoramic views of the city. Best visited at sunset. Wheelchair accessible.",
        "tags": ["views", "photography", "sunset", "romantic", "accessible"],
        "priceTier": 1,
        "categories": ["views", "photography", "landmark"],
        "durationMinutes": 60,  # 1 hour
        "ticketRequired": True
    }
]

HOTEL_TEMPLATES = [
    {
        "type": "luxury",
        "names": ["Grand Palace Hotel", "The Ritz", "Royal Suite", "Premium Plaza", "Elite Towers"],
        "description": "Five-star luxury hotel with world-class amenities. Concierge service, spa, and fine dining on-site.",
        "tags": ["luxury", "spa", "concierge", "fine-dining", "premium"],
        "priceTier": 4,
        "amenities": ["pool", "spa", "gym", "restaurant", "bar", "room-service", "concierge", "valet"],
        "roomTypes": ["suite", "deluxe", "executive"],
        "style": ["modern", "elegant", "sophisticated"]
    },
    {
        "type": "boutique",
        "names": ["Boutique House", "Artisan Hotel", "The Design Hotel", "Creative Suites", "Urban Boutique"],
        "description": "Stylish boutique hotel with unique character. Each room individually designed with artistic flair.",
        "tags": ["boutique", "design", "unique", "artistic", "intimate"],
        "priceTier": 3,
        "amenities": ["wifi", "breakfast", "bar", "lounge", "artwork"],
        "roomTypes": ["standard", "deluxe", "suite"],
        "style": ["artistic", "unique", "eclectic", "modern"]
    },
    {
        "type": "business",
        "names": ["Business Center Hotel", "Executive Inn", "Corporate Suites", "Meeting Plaza", "WorkHub Hotel"],
        "description": "Modern business hotel with meeting rooms and high-speed internet. Near business district.",
        "tags": ["business", "meeting-rooms", "wifi", "central", "efficient"],
        "priceTier": 3,
        "amenities": ["wifi", "meeting-rooms", "gym", "business-center", "desk", "printer"],
        "roomTypes": ["standard", "executive", "suite"],
        "style": ["modern", "efficient", "professional"]
    },
    {
        "type": "family",
        "names": ["Family Resort", "Kids Paradise Hotel", "Family Suites", "Happy Stay", "Family Haven"],
        "description": "Family-friendly hotel with kids' club, playground, and connecting rooms. Entertainment for all ages.",
        "tags": ["family-friendly", "kids-club", "playground", "spacious", "entertainment"],
        "priceTier": 2,
        "amenities": ["pool", "kids-club", "playground", "restaurant", "family-rooms", "wifi"],
        "roomTypes": ["family", "connecting", "suite"],
        "style": ["casual", "spacious", "comfortable"]
    },
    {
        "type": "romantic",
        "names": ["Romantic Retreat", "Lovers' Nest", "Honeymoon Suite Hotel", "Couples Paradise", "Romance Inn"],
        "description": "Intimate romantic hotel perfect for couples. Private balconies, couples' spa, and candlelit dining.",
        "tags": ["romantic", "couples", "intimate", "private", "honeymoon"],
        "priceTier": 3,
        "amenities": ["spa", "restaurant", "bar", "balcony", "room-service", "couples-packages"],
        "roomTypes": ["suite", "deluxe", "honeymoon"],
        "style": ["romantic", "intimate", "elegant"]
    },
    {
        "type": "budget",
        "names": ["Smart Stay", "Economy Inn", "Budget Lodge", "Value Hotel", "City Sleep"],
        "description": "Clean, comfortable budget hotel with essential amenities. Great value for money in central location.",
        "tags": ["budget", "value", "clean", "simple", "central"],
        "priceTier": 1,
        "amenities": ["wifi", "breakfast", "24hr-desk"],
        "roomTypes": ["standard", "twin", "double"],
        "style": ["simple", "functional", "clean"]
    },
    {
        "type": "historic",
        "names": ["Heritage Hotel", "Historic Manor", "Old Town Inn", "Classic Palace", "Vintage Suites"],
        "description": "Beautifully restored historic building with period features. Combines old-world charm with modern comfort.",
        "tags": ["historic", "heritage", "restored", "charming", "authentic"],
        "priceTier": 3,
        "amenities": ["wifi", "restaurant", "bar", "courtyard", "historic-tours"],
        "roomTypes": ["standard", "deluxe", "suite"],
        "style": ["historic", "traditional", "charming"]
    },
    {
        "type": "eco",
        "names": ["Green Stay Hotel", "Eco Lodge", "Sustainable Suites", "Earth Hotel", "Nature Retreat"],
        "description": "Eco-friendly hotel with sustainable practices. Solar power, organic breakfast, recycling programs.",
        "tags": ["eco-friendly", "sustainable", "green", "organic", "environmental"],
        "priceTier": 2,
        "amenities": ["wifi", "organic-breakfast", "bike-rental", "solar-power", "recycling"],
        "roomTypes": ["standard", "eco-suite", "garden-view"],
        "style": ["natural", "sustainable", "peaceful"]
    }
]


def generate_places_for_city(city: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate diverse places for a city"""
    places = []
    place_counter = 0

    # Generate 5 restaurants per city
    for i, template in enumerate(RESTAURANT_TEMPLATES):
        place_counter += 1
        place_id = f"place-{city['id']}-rest-{place_counter:03d}"
        name = f"{random.choice(template['names'])} {city['name']}"

        place = {
            "id": place_id,
            "placeId": place_id,
            "geoScopeId": city["id"],
            "type": "restaurant",
            "name": name,
            "description": template["description"],
            "tags": template["tags"],
            "accessibility": ["wheelchair-accessible"] if random.random() > 0.3 else [],
            "hours": generate_hours(template.get("type", "regular")),
            "geo": {
                "lat": city["lat"] + random.uniform(-0.02, 0.02),
                "lon": city["lon"] + random.uniform(-0.02, 0.02)
            },
            "neighborhood": f"{random.choice(['Old Town', 'City Center', 'Downtown', 'Historic District', 'Waterfront'])}",
            "priceTier": template["priceTier"],
            "rating": round(random.uniform(3.8, 4.9), 1),
            "reviewCount": random.randint(200, 3000),
            "website": f"https://example.com/{place_id}",
            "phone": f"+{random.randint(30, 49)} {random.randint(100, 999)} {random.randint(1000, 9999)}",
            # Restaurant-specific fields
            "restaurantSpecific": {
                "dietaryOptions": template["dietary"],
                "cuisineTypes": template["cuisineTypes"],
                "seatingOptions": template["seatingOptions"],
                "mealTypes": template["mealTypes"]
            },
            "embedding": None,  # Will be generated during seeding
            "_embedding_source": template["description"]  # Mark for embedding generation
        }
        places.append(place)

    # Generate 3 cafés per city
    for i, template in enumerate(CAFE_TEMPLATES):
        place_counter += 1
        place_id = f"place-{city['id']}-cafe-{place_counter:03d}"
        name = f"{random.choice(template['names'])}"

        place = {
            "id": place_id,
            "placeId": place_id,
            "geoScopeId": city["id"],
            "type": "cafe",
            "name": name,
            "description": template["description"],
            "tags": template["tags"],
            "accessibility": ["wheelchair-accessible"] if random.random() > 0.4 else [],
            "hours": generate_hours("cafe"),
            "geo": {
                "lat": city["lat"] + random.uniform(-0.02, 0.02),
                "lon": city["lon"] + random.uniform(-0.02, 0.02)
            },
            "neighborhood": f"{random.choice(['Old Town', 'Trendy District', 'Arts Quarter', 'University Area'])}",
            "priceTier": template["priceTier"],
            "rating": round(random.uniform(4.0, 4.8), 1),
            "reviewCount": random.randint(150, 1500),
            "website": f"https://example.com/{place_id}",
            "phone": f"+{random.randint(30, 49)} {random.randint(100, 999)} {random.randint(1000, 9999)}",
            # Restaurant-specific fields (cafes use same structure as restaurants)
            "restaurantSpecific": {
                "dietaryOptions": ["vegan-options", "lactose-free"],
                "cuisineTypes": ["cafe", "bakery", "coffee"],
                "seatingOptions": ["indoor", "outdoor"],
                "mealTypes": ["breakfast", "brunch", "lunch"]
            },
            "embedding": None,  # Will be generated during seeding
            "_embedding_source": template["description"]  # Mark for embedding generation
        }
        places.append(place)

    # Generate 4 attractions per city
    for i, template in enumerate(ATTRACTION_TEMPLATES):
        place_counter += 1
        place_id = f"place-{city['id']}-attr-{place_counter:03d}"
        name = f"{random.choice(template['names'])}"

        place = {
            "id": place_id,
            "placeId": place_id,
            "geoScopeId": city["id"],
            "type": template["type"],  # museum, landmark, park, viewpoint
            "name": name,
            "description": template["description"],
            "tags": template["tags"],
            "accessibility": ["wheelchair-accessible", "audio-guide"] if template["type"] != "viewpoint" else [
                "wheelchair-accessible"],
            "hours": generate_hours("attraction"),
            "geo": {
                "lat": city["lat"] + random.uniform(-0.03, 0.03),
                "lon": city["lon"] + random.uniform(-0.03, 0.03)
            },
            "neighborhood": "City Center",
            "priceTier": template["priceTier"],
            "rating": round(random.uniform(4.3, 4.9), 1),
            "reviewCount": random.randint(500, 8000),
            "website": f"https://example.com/{place_id}",
            "phone": f"+{random.randint(30, 49)} {random.randint(100, 999)} {random.randint(1000, 9999)}",
            # Activity-specific fields
            "activitySpecific": {
                "categories": template["categories"],
                "durationMinutes": template["durationMinutes"],
                "ticketRequired": template["ticketRequired"]
            },
            "embedding": None,  # Will be generated during seeding
            "_embedding_source": template["description"]  # Mark for embedding generation
        }
        places.append(place)

    # Generate 8 hotels per city (one of each type)
    for i, template in enumerate(HOTEL_TEMPLATES):
        place_counter += 1
        place_id = f"place-{city['id']}-hotel-{place_counter:03d}"
        name = f"{random.choice(template['names'])}"

        place = {
            "id": place_id,
            "placeId": place_id,
            "geoScopeId": city["id"],
            "type": "hotel",
            "name": name,
            "description": template["description"],
            "tags": template["tags"],
            "accessibility": ["wheelchair-accessible", "elevator", "accessible-bathroom"] if template["type"] != "budget" else ["elevator"],
            "hours": {"24/7": True},  # Hotels are always open
            "geo": {
                "lat": city["lat"] + random.uniform(-0.03, 0.03),
                "lon": city["lon"] + random.uniform(-0.03, 0.03)
            },
            "neighborhood": f"{random.choice(['City Center', 'Old Town', 'Business District', 'Waterfront', 'Historic Quarter', 'Shopping District'])}",
            "priceTier": template["priceTier"],
            "rating": round(random.uniform(3.8, 4.9), 1),
            "reviewCount": random.randint(300, 5000),
            "website": f"https://example.com/{place_id}",
            "phone": f"+{random.randint(30, 49)} {random.randint(100, 999)} {random.randint(1000, 9999)}",
            # Hotel-specific fields
            "hotelSpecific": {
                "amenities": template["amenities"],
                "roomTypes": template["roomTypes"],
                "style": template["style"],
                "checkIn": "15:00",
                "checkOut": "11:00"
            },
            "embedding": None,  # Will be generated during seeding
            "_embedding_source": template["description"]  # Mark for embedding generation
        }
        places.append(place)

    return places


def generate_hours(place_type: str) -> Dict[str, List]:
    """Generate operating hours based on place type"""
    if place_type == "late_night":
        return {
            "mon": [],
            "tue": [["19:00", "01:00"]],
            "wed": [["19:00", "01:00"]],
            "thu": [["19:00", "01:00"]],
            "fri": [["19:00", "02:00"]],
            "sat": [["19:00", "02:00"]],
            "sun": []
        }
    elif place_type == "cafe":
        return {
            "mon": [["07:00", "19:00"]],
            "tue": [["07:00", "19:00"]],
            "wed": [["07:00", "19:00"]],
            "thu": [["07:00", "19:00"]],
            "fri": [["07:00", "20:00"]],
            "sat": [["08:00", "20:00"]],
            "sun": [["08:00", "19:00"]]
        }
    elif place_type == "attraction":
        return {
            "mon": [],  # Closed Mondays
            "tue": [["10:00", "18:00"]],
            "wed": [["10:00", "18:00"]],
            "thu": [["10:00", "18:00"]],
            "fri": [["10:00", "20:00"]],
            "sat": [["10:00", "20:00"]],
            "sun": [["10:00", "18:00"]]
        }
    else:  # regular restaurant
        return {
            "mon": [["12:00", "15:00"], ["19:00", "23:00"]],
            "tue": [["12:00", "15:00"], ["19:00", "23:00"]],
            "wed": [["12:00", "15:00"], ["19:00", "23:00"]],
            "thu": [["12:00", "15:00"], ["19:00", "23:00"]],
            "fri": [["12:00", "15:00"], ["19:00", "00:00"]],
            "sat": [["12:00", "15:00"], ["19:00", "00:00"]],
            "sun": [["12:00", "15:00"], ["19:00", "22:00"]]
        }


# ============================================================================
# Sample Threads Data
# ============================================================================

def generate_sample_threads() -> List[Dict[str, Any]]:
    """Generate sample conversation threads"""
    threads = []

    for i in range(5):
        thread_id = f"thread-{uuid.uuid4()}"
        user_id = f"user-demo-{i + 1:02d}"
        tenant_id = "demo-tenant"

        now = datetime.utcnow()

        threads.append({
            "id": f"{tenant_id}_{user_id}_{thread_id}",  # Composite ID for hierarchical PK
            "threadId": thread_id,
            "userId": user_id,
            "tenantId": tenant_id,
            "title": random.choice([
                "Planning Barcelona Trip",
                "Weekend in Paris",
                "Rome Food Tour",
                "Amsterdam Adventure",
                "Berlin Museum Hunt"
            ]),
            "activeAgent": random.choice(["orchestrator", "hotel", "activity", "dining", "itinerary_generator"]),
            "createdAt": (now - timedelta(days=random.randint(1, 30))).isoformat(),
            "lastMessageAt": (now - timedelta(hours=random.randint(1, 72))).isoformat(),
            "messageCount": random.randint(5, 25),
            "status": "active"
        })

    return threads


# ============================================================================
# Sample Memories Data
# ============================================================================

def generate_sample_memories() -> List[Dict[str, Any]]:
    """Generate sample user memories with embeddings"""
    memories = []

    memory_templates = [
        {
            "type": "declarative",
            "category": "dining",
            "text": "User prefers vegetarian restaurants and avoids seafood",
            "facets": {"dietary": ["vegetarian"], "avoidance": ["seafood"]},
            "salience": 0.9
        },
        {
            "type": "declarative",
            "category": "dining",
            "text": "User is gluten-free and requires gluten-free menu options",
            "facets": {"dietary": ["gluten-free"]},
            "salience": 1.0
        },
        {
            "type": "declarative",
            "category": "activity",
            "text": "User loves photography and seeks Instagram-worthy locations",
            "facets": {"interests": ["photography"], "preferences": ["instagram-worthy"]},
            "salience": 0.8
        },
        {
            "type": "declarative",
            "category": "lodging",
            "text": "User requires wheelchair-accessible accommodations",
            "facets": {"accessibility": ["wheelchair"]},
            "salience": 1.0
        },
        {
            "type": "declarative",
            "category": "lodging",
            "text": "User prefers boutique hotels with rooftop pools",
            "facets": {"hotelType": ["boutique"], "amenities": ["pool", "rooftop"]},
            "salience": 0.8
        },
        {
            "type": "episodic",
            "category": "dining",
            "text": "User enjoyed late-night dining at tapas bars during last Barcelona trip",
            "facets": {"timeOfDay": ["late-night"], "cuisine": ["tapas"], "city": ["barcelona"]},
            "salience": 0.7
        },
        {
            "type": "episodic",
            "category": "activity",
            "text": "User visited Louvre Museum in Paris and spent 4 hours there",
            "facets": {"placeType": ["museum"], "city": ["paris"], "duration": ["long"]},
            "salience": 0.6
        },
        {
            "type": "episodic",
            "category": "lodging",
            "text": "User stayed at Cotton House Hotel in Barcelona and loved it",
            "facets": {"hotel": ["Cotton House"], "city": ["barcelona"]},
            "salience": 0.7
        },
        {
            "type": "procedural",
            "category": "lodging",
            "text": "User always books accommodations near public transportation",
            "facets": {"preferences": ["transit-accessible"]},
            "salience": 0.8
        },
        {
            "type": "procedural",
            "category": "activity",
            "text": "User prefers morning activities and avoids crowded tourist spots",
            "facets": {"timeOfDay": ["morning"], "preferences": ["less-crowded"]},
            "salience": 0.7
        },
        {
            "type": "procedural",
            "category": "dining",
            "text": "User prefers outdoor seating and early dinners around 6-7pm",
            "facets": {"seating": ["outdoor"], "timeOfDay": ["early-evening"]},
            "salience": 0.7
        }
    ]

    now = datetime.utcnow()

    for i in range(3):  # 3 demo users
        user_id = f"user-demo-{i + 1:02d}"
        tenant_id = "demo-tenant"

        for template in random.sample(memory_templates, k=random.randint(4, 7)):
            memory_id = f"mem-{uuid.uuid4()}"
            memories.append({
                "id": f"{tenant_id}_{user_id}_{memory_id}",  # Composite ID for hierarchical PK
                "memoryId": memory_id,
                "userId": user_id,
                "tenantId": tenant_id,
                "category": template["category"],  # lodging, activity, or dining
                "memoryType": template["type"],
                "text": template["text"],
                "facets": template["facets"],
                "salience": template["salience"],
                "justification": f"Extracted from conversation on {now.date()}",
                "createdAt": (now - timedelta(days=random.randint(1, 60))).isoformat(),
                "ttl": 365 * 24 * 60 * 60 if template["type"] in ["declarative", "procedural"] else 90 * 24 * 60 * 60,  # 1 year for long-term, 90 days for episodic
                "embedding": None,  # Will be generated during seeding
                "_embedding_source": template["text"]  # Mark for embedding generation
            })

    return memories


# ============================================================================
# Sample Trips Data
# ============================================================================

def generate_sample_trips() -> List[Dict[str, Any]]:
    """Generate sample trip itineraries"""
    trips = []

    trip_templates = [
        {
            "city": "barcelona",
            "duration": 3,
            "title": "Barcelona Food & Culture Tour"
        },
        {
            "city": "paris",
            "duration": 4,
            "title": "Romantic Paris Weekend"
        },
        {
            "city": "rome",
            "duration": 5,
            "title": "Ancient Rome Explorer"
        },
        {
            "city": "amsterdam",
            "duration": 2,
            "title": "Amsterdam Museums & Canals"
        },
        {
            "city": "berlin",
            "duration": 3,
            "title": "Berlin History & Art"
        },
        {
            "city": "london",
            "duration": 4,
            "title": "London Classics"
        },
        {
            "city": "prague",
            "duration": 3,
            "title": "Prague Old Town Discovery"
        },
        {
            "city": "vienna",
            "duration": 3,
            "title": "Vienna Imperial Experience"
        },
        {
            "city": "lisbon",
            "duration": 4,
            "title": "Lisbon Coastal Adventure"
        },
        {
            "city": "budapest",
            "duration": 3,
            "title": "Budapest Thermal Baths & Ruin Bars"
        }
    ]

    now = datetime.utcnow()

    for i, template in enumerate(trip_templates):
        trip_id = f"trip-{uuid.uuid4()}"
        user_id = f"user-demo-{(i % 3) + 1:02d}"
        tenant_id = "demo-tenant"
        start_date = now + timedelta(days=random.randint(30, 180))
        end_date = start_date + timedelta(days=template["duration"])

        # Generate daily plans
        days = []
        for day_num in range(template["duration"]):
            days.append({
                "date": (start_date + timedelta(days=day_num)).strftime("%Y-%m-%d"),
                "activities": [
                    {
                        "time": "09:00",
                        "type": "cafe",
                        "name": "Morning Coffee",
                        "duration": 60
                    },
                    {
                        "time": "10:30",
                        "type": "attraction",
                        "name": "Museum Visit",
                        "duration": 180
                    },
                    {
                        "time": "14:00",
                        "type": "restaurant",
                        "name": "Lunch",
                        "duration": 90
                    },
                    {
                        "time": "16:00",
                        "type": "attraction",
                        "name": "City Walk",
                        "duration": 120
                    },
                    {
                        "time": "19:30",
                        "type": "restaurant",
                        "name": "Dinner",
                        "duration": 120
                    }
                ]
            })

        trips.append({
            "id": f"{tenant_id}_{user_id}_{trip_id}",  # Composite ID for hierarchical PK
            "tripId": trip_id,
            "userId": user_id,
            "tenantId": tenant_id,
            "title": template["title"],
            "scope": {
                "type": "city",
                "id": template["city"]
            },
            "dates": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d")
            },
            "travelers": [user_id],
            "constraints": {
                "budgetTier": random.choice([2, 3]),
                "dietary": random.choice([[], ["vegetarian"], ["vegan"]]),
                "accessibility": random.choice([[], ["wheelchair"]])
            },
            "days": days,
            "status": random.choice(["draft", "confirmed", "completed"]),
            "createdAt": (now - timedelta(days=random.randint(5, 90))).isoformat(),
            "updatedAt": (now - timedelta(days=random.randint(1, 30))).isoformat()
        })

    return trips


# ============================================================================
# Data Seeding Functions
# ============================================================================

def seed_container(
        container,
        items: List[Dict[str, Any]],
        container_name: str,
        dry_run: bool = False,
        generate_embeddings: bool = False
):
    """Seed items into a container with optional embedding generation"""
    print(f"\n📝 Seeding {container_name}...")
    print(f"   Items to insert: {len(items)}")

    if dry_run:
        print(f"   [DRY RUN] Would insert {len(items)} items")
        if generate_embeddings:
            print(f"   [DRY RUN] Would generate embeddings for items")
        return

    success = 0
    errors = 0
    embeddings_generated = 0

    for item in items:
        try:
            # Generate embedding if needed
            if generate_embeddings and "_embedding_source" in item:
                source_text = item.get("_embedding_source")
                if source_text:
                    embedding = generate_embedding(source_text)
                    if embedding:
                        item["embedding"] = embedding
                        embeddings_generated += 1
                # Remove temporary marker
                del item["_embedding_source"]

            container.upsert_item(item)
            success += 1
            if success % 10 == 0:
                print(f"   Progress: {success}/{len(items)}")
        except Exception as e:
            errors += 1
            print(f"   ❌ Error inserting {item.get('id', 'unknown')}: {e}")

    print(f"   ✅ Success: {success}/{len(items)}")
    if embeddings_generated > 0:
        print(f"   🧮 Embeddings generated: {embeddings_generated}")
    if errors > 0:
        print(f"   ❌ Errors: {errors}")


def seed_all_data(containers: Dict[str, Any], dry_run: bool = False):
    """Seed all synthetic data"""
    print("\n" + "=" * 70)
    print("🌱 Seeding Synthetic Data")
    print("=" * 70)

    # Check if embeddings can be generated
    can_generate_embeddings = bool(AZURE_OPENAI_ENDPOINT)
    if can_generate_embeddings:
        print("\n✅ Azure OpenAI configured - will generate embeddings")
    else:
        print("\n⚠️  Azure OpenAI not configured - skipping embedding generation")
        print("   Set AZURE_OPENAI_ENDPOINT in .env to enable embeddings")

    # Generate all places for all cities
    print("\n🏙️  Generating places for 10 European cities...")
    all_places = []
    for city in CITIES:
        city_places = generate_places_for_city(city)
        all_places.extend(city_places)
        print(f"   ✅ {city['name']}: {len(city_places)} places")

    print(f"\n📊 Total places generated: {len(all_places)}")

    # Seed places with embeddings
    seed_container(
        containers["places"],
        all_places,
        "places",
        dry_run,
        generate_embeddings=can_generate_embeddings
    )

    # Generate and seed threads
    # threads = generate_sample_threads()
    # seed_container(containers["threads"], threads, "threads", dry_run)

    # Generate and seed memories with embeddings
    memories = generate_sample_memories()
    seed_container(
        containers["memories"],
        memories,
        "memories",
        dry_run,
        generate_embeddings=can_generate_embeddings
    )

    # Generate and seed trips
    trips = generate_sample_trips()
    seed_container(containers["trips"], trips, "trips", dry_run)

    print("\n" + "=" * 70)
    print("✅ Data Seeding Complete!")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"   Places: {len(all_places)} (across 10 cities)")
    print(f"   Memories: {len(memories)}")
    print(f"   Trips: {len(trips)}")
    if can_generate_embeddings:
        print(f"\n✨ Vector embeddings generated for places and memories")
    print(f"\n🎯 Ready for end-to-end testing!")


# ============================================================================
# Main
# ============================================================================

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed Travel Assistant Cosmos DB with containers and data"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without actually creating/inserting data"
    )
    parser.add_argument(
        "--skip-containers",
        action="store_true",
        help="Skip container creation (only seed data)"
    )
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("🌍 TRAVEL ASSISTANT - COSMOS DB SETUP")
    print("=" * 70)

    if not COSMOS_ENDPOINT:
        print("\n❌ Error: COSMOSDB_ENDPOINT not set in environment")
        print("   Please set COSMOSDB_ENDPOINT in your .env file")
        return

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")

    # Initialize Cosmos client
    client = get_cosmos_client()

    # Create containers
    if not args.skip_containers:
        database, containers = create_all_containers(client)
    else:
        print("\n⏭️  Skipping container creation")
        database = client.get_database_client(DATABASE_NAME)
        containers = {
            name: database.get_container_client(name)
            for name in CONTAINER_CONFIGS.keys()
        }

    # Seed data
    seed_all_data(containers, dry_run=args.dry_run)

    print("\n" + "=" * 70)
    print("🎉 ALL DONE!")
    print("=" * 70)
    print("\n📝 Next Steps:")
    print("   1. Verify containers in Azure Portal")
    print("   2. Check vector and full-text indexing policies")
    print("   3. Run the agent application: python src/app/travel_agents.py")
    print("   4. Test hybrid search scenarios\n")


if __name__ == "__main__":
    main()
