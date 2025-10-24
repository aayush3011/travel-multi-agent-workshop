#!/usr/bin/env python3
"""
Travel Assistant Cosmos DB Seeding Script

This script:
1. Creates the Cosmos DB database (if it doesn't exist)
2. Creates all required containers with proper indexing policies
3. Loads data from JSON files in the data/ directory:
   - users.json (4 users)
   - memories.json (10 memories)
   - places.json (1,700 places across 35 cities)
   - trips.json (5 sample trips)

Container List:
- Sessions
- Messages (chat messages)
- Summaries (conversation summaries)
- Memories (user preferences - loaded from JSON)
- Places (hotels, restaurants, attractions - loaded from JSON)
- Trips (trip itineraries - loaded from JSON)
- Users (user profiles - loaded from JSON)
- ApiEvents (API call logs)
- Checkpoints (LangGraph state)
- Debug (chat completion logs)

Run: python src/seed_data_new.py
"""

import json
import os
import sys
from typing import List, Dict, Any
from pathlib import Path

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceExistsError, CosmosResourceNotFoundError
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

# Vector search configuration
VECTOR_DIMENSIONS = 1024
VECTOR_INDEX_TYPE = "diskANN"
SIMILARITY_METRIC = "cosine"

# Full-text search configuration
FULL_TEXT_LOCALE = "en-us"

# Data directory
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"

print(f"📂 Data directory: {DATA_DIR}")
print(f"🌐 Cosmos endpoint: {COSMOS_ENDPOINT}")
print(f"🤖 Azure OpenAI endpoint: {AZURE_OPENAI_ENDPOINT}")
print(f"📊 Embedding model: {AZURE_OPENAI_EMBEDDING_DEPLOYMENT}")


# ============================================================================
# Cosmos DB Client Initialization
# ============================================================================

def get_cosmos_client() -> CosmosClient:
    """Initialize Cosmos DB client"""
    return CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)

# ============================================================================
# Container Definitions with Vector + Full-Text Indexing
# ============================================================================

CONTAINER_CONFIGS = {
    "Sessions": {
        "partition_key": ["/tenantId", "/userId", "/sessionId"],
        "hierarchical": True,
        "vector_search": False,
        "full_text_search": False,
        "description": "Conversation sessions"
    },
    "Messages": {
        "partition_key": ["/tenantId", "/userId", "/sessionId"],
        "hierarchical": True,
        "vector_search": True,
        "full_text_search": True,
        "vector_paths": ["/embedding"],
        "full_text_paths": ["/content", "/keywords"],
        "description": "Chat messages with embeddings"
    },
    "Summaries": {
        "partition_key": ["/tenantId", "/userId", "/sessionId"],
        "hierarchical": True,
        "vector_search": True,
        "full_text_search": True,
        "vector_paths": ["/embedding"],
        "full_text_paths": ["/text"],
        "description": "Conversation summaries with embeddings"
    },
    "Memories": {
        "partition_key": ["/tenantId", "/userId", "/memoryId"],
        "hierarchical": True,
        "vector_search": True,
        "full_text_search": True,
        "vector_paths": ["/embedding"],
        "full_text_paths": ["/text"],
        "description": "User memories (declarative, episodic, procedural)"
    },
    "Places": {
        "partition_key": "/geoScopeId",
        "hierarchical": False,
        "vector_search": True,
        "full_text_search": True,
        "vector_paths": ["/embedding"],
        "full_text_paths": ["/name", "/description", "/tags"],
        "description": "Places across cities (hotels, restaurants, attractions)"
    },
    "Trips": {
        "partition_key": ["/tenantId", "/userId", "/tripId"],
        "hierarchical": True,
        "vector_search": False,
        "full_text_search": False,
        "description": "Trip itineraries and plans"
    },
    "Users": {
        "partition_key": "/userId",
        "hierarchical": False,
        "vector_search": False,
        "full_text_search": False,
        "description": "User profiles"
    },
    "ApiEvents": {
        "partition_key": ["/tenantId", "/userId", "/sessionId"],
        "hierarchical": True,
        "vector_search": False,
        "full_text_search": False,
        "description": "External API call logs"
    },
    "Debug": {
        "partition_key": ["/tenantId", "/userId", "/sessionId"],
        "hierarchical": True,
        "vector_search": False,
        "full_text_search": False,
        "description": "Debug logs for chat completions with token usage and metadata"
    },
    "Checkpoints": {
        "partition_key": "/session_id",
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
    Create a Cosmos DB container with optional vector and full-text search indexing.
    
    Args:
        database: Cosmos database client
        container_name: Name of the container
        config: Container configuration dictionary
        
    Returns:
        Container client object
    """
    print(f"\n📦 Creating container: {container_name}")
    print(f"   Description: {config['description']}")

    # Build partition key
    if config["hierarchical"]:
        partition_key_paths = config["partition_key"]
        partition_key = PartitionKey(
            path=partition_key_paths,
            kind="MultiHash"
        )
        print(f"   Partition key: {partition_key_paths} (hierarchical)")
    else:
        partition_key = PartitionKey(path=config["partition_key"])
        print(f"   Partition key: {config['partition_key']}")

    # Build indexing policy
    indexing_policy = {
        "automatic": True,
        "indexingMode": "consistent",
        "includedPaths": [{"path": "/*"}],
        "excludedPaths": [{"path": "/\"_etag\"/?"}]
    }

    # Add vector embedding policies
    vector_embedding_policy = None
    if config.get("vector_search", False):
        print(f"   ✅ Vector search enabled (dimensions: {VECTOR_DIMENSIONS})")
        vector_paths = config.get("vector_paths", ["/embedding"])
        vector_embedding_policy = {
            "vectorEmbeddings": [
                {
                    "path": path,
                    "dataType": "float32",
                    "dimensions": VECTOR_DIMENSIONS,
                    "distanceFunction": SIMILARITY_METRIC
                }
                for path in vector_paths
            ]
        }

        # Add vector indexes
        indexing_policy["vectorIndexes"] = [
            {
                "path": path,
                "type": VECTOR_INDEX_TYPE
            }
            for path in vector_paths
        ]

    # Add full-text search policies
    full_text_policy = None
    if config.get("full_text_search", False):
        print(f"   ✅ Full-text search enabled (locale: {FULL_TEXT_LOCALE})")
        full_text_paths = config.get("full_text_paths", [])
        full_text_policy = {
            "defaultLanguage": "en-US",
            "fullTextPaths": [
                {
                    "path": path,
                    "language": "en-US"
                }
                for path in full_text_paths
            ]
        }
        indexing_policy["fullTextIndexes"] = [
            {
                "path": path,
                "language": FULL_TEXT_LOCALE
            }
            for path in full_text_paths
        ]

    # Create container
    try:
        container = database.create_container_if_not_exists(
            id=container_name,
            partition_key=partition_key,
            indexing_policy=indexing_policy,
            vector_embedding_policy=vector_embedding_policy,
            full_text_policy=full_text_policy,
        )
        print(f"   ✅ Container created successfully")
        return container

    except CosmosResourceExistsError:
        print(f"   ⚠️  Container already exists, using existing container")
        return database.get_container_client(container_name)


# ============================================================================
# Database and Container Creation
# ============================================================================

def create_database_and_containers(client: CosmosClient) -> tuple:
    """Create database and all containers"""
    print("\n" + "=" * 70)
    print("🗄️  DATABASE SETUP")
    print("=" * 70)

    # Create database
    try:
        database = client.create_database_if_not_exists(id=DATABASE_NAME)
        print(f"✅ Created database: {DATABASE_NAME}")
    except CosmosResourceExistsError:
        print(f"⚠️  Database already exists: {DATABASE_NAME}")
        database = client.get_database_client(DATABASE_NAME)

    # Create all containers
    print("\n" + "=" * 70)
    print("📦 CONTAINER CREATION")
    print("=" * 70)

    containers = {}
    for container_name, config in CONTAINER_CONFIGS.items():
        container = create_container_with_indexing(database, container_name, config)
        containers[container_name] = container

    print(f"\n✅ Created/verified {len(containers)} containers")
    return database, containers


# ============================================================================
# Data Loading Functions
# ============================================================================

def load_json_file(filename: str) -> List[Dict[str, Any]]:
    """Load data from JSON file"""
    file_path = DATA_DIR / filename

    if not file_path.exists():
        print(f"   ⚠️  File not found: {file_path}")
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"   ✅ Loaded {len(data)} items from {filename}")
        return data
    except Exception as e:
        print(f"   ❌ Error loading {filename}: {e}")
        return []


def seed_users(container, dry_run: bool = False):
    """Load users from users.json"""
    print("\n👤 Seeding USERS...")

    users = load_json_file("users.json")

    if not users:
        print("   ⚠️  No users to seed")
        return

    if dry_run:
        print(f"   🔍 DRY RUN: Would seed {len(users)} users")
        return

    for user in users:
        try:
            container.upsert_item(user)
            print(f"   ✅ Seeded user: {user['name']} ({user['userId']})")
        except Exception as e:
            print(f"   ❌ Error seeding user {user.get('userId')}: {e}")

    print(f"   ✅ Seeded {len(users)} users")


def seed_memories(container, dry_run: bool = False):
    """Load memories from memories.json and generate embeddings"""
    print("\n🧠 Seeding MEMORIES...")

    memories = load_json_file("memories.json")

    if not memories:
        print("   ⚠️  No memories to seed")
        return

    if dry_run:
        print(f"   🔍 DRY RUN: Would seed {len(memories)} memories")
        return

    for idx, memory in enumerate(memories, 1):
        try:
            container.upsert_item(memory)
            memory_type = memory.get('memoryType', 'unknown')
            ttl_info = "no expiration" if memory.get("ttl") == -1 else f"TTL={memory.get('ttl')}s"
            print(f"   ✅ Seeded memory: {memory['memoryId']} ({memory_type}, {ttl_info})")
        except Exception as e:
            print(f"   ❌ Error seeding memory {memory.get('memoryId')}: {e}")

    print(f"   ✅ Seeded {len(memories)} memories with embeddings")


def seed_places(container, dry_run: bool = False):
    """Load places from three separate JSON files and generate embeddings"""
    print("\n🏨 Seeding PLACES...")
    
    # Load all three files
    print("   📂 Loading data files...")
    hotels = load_json_file("hotels_all_cities.json")
    restaurants = load_json_file("restaurants_all_cities.json")
    activities = load_json_file("activities_all_cities.json")
    
    # Combine all places
    all_places = hotels + restaurants + activities
    
    if not all_places:
        print("   ⚠️  No places to seed")
        return
    
    # Display statistics
    print(f"\n   📊 Data loaded:")
    print(f"      • Hotels: {len(hotels)} (49 cities × 10 hotels = 490 expected)")
    print(f"      • Restaurants: {len(restaurants)} (49 cities × 20 restaurants = 980 expected)")
    print(f"      • Activities: {len(activities)} (49 cities × 30 activities = 1,470 expected)")
    print(f"      • Total places: {len(all_places)}")
    
    if dry_run:
        print(f"\n   🔍 DRY RUN: Would seed {len(all_places)} places")
        print(f"      • Hotels: {len(hotels)}")
        print(f"      • Restaurants: {len(restaurants)}")
        print(f"      • Activities: {len(activities)}")
        return
    
    # Count by type for verification
    type_counts = {}
    for place in all_places:
        place_type = place.get("type", "unknown")
        type_counts[place_type] = type_counts.get(place_type, 0) + 1
    
    print(f"\n   � Breakdown by type:")
    for place_type, count in sorted(type_counts.items()):
        print(f"      • {place_type}: {count}")
    
    # Seed all places with progress tracking
    success_count = 0
    error_count = 0
    
    for idx, place in enumerate(all_places, 1):
        try:
            container.upsert_item(place)
            success_count += 1
            
            # Progress updates
            if idx % 50 == 0:
                print(f"      Progress: {idx}/{len(all_places)} places processed ({success_count} success, {error_count} errors)...")
            
            if idx % 100 == 0:
                print(f"   ✅ Milestone: {idx}/{len(all_places)} places seeded")
        
        except Exception as e:
            error_count += 1
            print(f"   ❌ Error seeding place {place.get('id', 'unknown')}: {e}")
            
            # Show first few errors in detail, then summarize
            if error_count <= 3:
                print(f"      Place details: {place.get('name', 'N/A')} ({place.get('type', 'N/A')})")
    
    # Final summary
    print(f"\n   ✅ Seeding complete!")
    print(f"      • Successfully seeded: {success_count}/{len(all_places)} places")
    if error_count > 0:
        print(f"      • Errors encountered: {error_count}")
    print(f"      • Hotels: {len(hotels)}")
    print(f"      • Restaurants: {len(restaurants)}")
    print(f"      • Activities: {len(activities)}")


def seed_trips(container, dry_run: bool = False):
    """Load trips from trips.json"""
    print("\n✈️  Seeding TRIPS...")

    trips = load_json_file("trips.json")

    if not trips:
        print("   ⚠️  No trips to seed")
        return

    if dry_run:
        print(f"   🔍 DRY RUN: Would seed {len(trips)} trips")
        return

    for trip in trips:
        try:
            container.upsert_item(trip)
            print(f"   ✅ Seeded trip: {trip['destination']} ({trip['tripDuration']} days)")
        except Exception as e:
            print(f"   ❌ Error seeding trip {trip.get('tripId')}: {e}")

    print(f"   ✅ Seeded {len(trips)} trips")


def seed_all_data(containers: Dict[str, Any], dry_run: bool = False):
    """Seed all data from JSON files"""
    print("\n" + "=" * 70)
    print("📝 DATA SEEDING")
    print("=" * 70)

    # Seed each container
    seed_users(containers["Users"], dry_run)
    seed_memories(containers["Memories"], dry_run)
    seed_places(containers["Places"], dry_run)
    seed_trips(containers["Trips"], dry_run)

    print("\n✅ Data seeding complete!")


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

    # Create database and containers
    if not args.skip_containers:
        database, containers = create_database_and_containers(client)
    else:
        print("\n⏭️  Skipping container creation")
        database = client.get_database_client(DATABASE_NAME)
        containers = {
            name: database.get_container_client(name)
            for name in CONTAINER_CONFIGS.keys()
        }

    # Seed data from JSON files
    seed_all_data(containers, dry_run=args.dry_run)

    print("\n" + "=" * 70)
    print("🎉 ALL DONE!")
    print("=" * 70)
    print("\n📝 Next Steps:")
    print("   1. Verify containers in Azure Portal")
    print("   2. Check vector and full-text indexing policies")
    print("   3. Start MCP server: python -m mcp_server.mcp_http_server")
    print("   4. Start API server: uvicorn src.app.travel_agents_api:app --reload")
    print("   5. Test endpoints at http://localhost:8000/docs\n")


if __name__ == "__main__":
    main()
