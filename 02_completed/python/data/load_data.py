#!/usr/bin/env python3
"""
Travel Assistant Data Loader

This script loads data into existing Cosmos DB containers.
It assumes that all containers have already been created by the Bicep deployment.

Usage:
    python data/load_data.py                    # Load all data
    python data/load_data.py --containers users places  # Load specific containers
    python data/load_data.py --dry-run          # Preview what would be loaded

Data Files:
    - users.json (4 users)
    - memories.json (10 memories with embeddings)
    - places.json OR hotels_all_cities.json + restaurants_all_cities.json + activities_all_cities.json
    - trips.json (5 sample trips)
"""

import json
import os
import sys
import argparse
from typing import List, Dict, Any
from pathlib import Path

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables from parent directory
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR.parent / ".env"
load_dotenv(ENV_FILE)

# ============================================================================
# Configuration
# ============================================================================

COSMOS_ENDPOINT = os.getenv("COSMOSDB_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = os.getenv("COSMOS_DB_DATABASE_NAME", "TravelAssistant")

# Azure OpenAI for embeddings
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

# Vector search configuration
VECTOR_DIMENSIONS = 1024

# Data directory (same directory as this script)
DATA_DIR = SCRIPT_DIR

print(f"📂 Data directory: {DATA_DIR}")
print(f"🌐 Cosmos endpoint: {COSMOS_ENDPOINT}")
print(f"💾 Database: {DATABASE_NAME}")
print(f"🤖 Azure OpenAI endpoint: {AZURE_OPENAI_ENDPOINT}")


# ============================================================================
# Cosmos DB & OpenAI Clients
# ============================================================================

def get_cosmos_client() -> CosmosClient:
    """Initialize Cosmos DB client"""
    if not COSMOS_ENDPOINT or not COSMOS_KEY:
        raise ValueError("Missing COSMOSDB_ENDPOINT or COSMOS_KEY in environment")
    return CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)


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


def generate_embedding(text: str) -> List[float]:
    """Generate embedding vector for text using Azure OpenAI"""
    if not text or not AZURE_OPENAI_ENDPOINT:
        return [0.0] * VECTOR_DIMENSIONS

    try:
        client = get_openai_client()
        response = client.embeddings.create(
            input=text,
            model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            dimensions=VECTOR_DIMENSIONS,
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"   ⚠️  Warning: Could not generate embedding: {e}")
        return [0.0] * VECTOR_DIMENSIONS


# ============================================================================
# Data Loading Functions
# ============================================================================

def load_json_file(filename: str) -> List[Dict[str, Any]]:
    """Load and parse a JSON file from the data directory"""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        print(f"   ⚠️  File not found: {filepath}")
        return []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"   ✅ Loaded {len(data)} items from {filename}")
            return data
    except Exception as e:
        print(f"   ❌ Error loading {filename}: {e}")
        return []


def seed_users(container, dry_run: bool = False):
    """Load users from users.json"""
    print("\n👤 Loading USERS...")
    users = load_json_file("users.json")

    if not users:
        print("   ⚠️  No users to load")
        return

    if dry_run:
        print(f"   🔍 DRY RUN: Would load {len(users)} users")
        for user in users:
            print(f"      - {user.get('userId')}: {user.get('name')}")
        return

    for idx, user in enumerate(users, 1):
        try:
            container.upsert_item(user)
            print(f"   ✅ Loaded user {idx}/{len(users)}: {user['userId']} - {user['name']}")
        except Exception as e:
            print(f"   ❌ Error loading user {user.get('userId')}: {e}")

    print(f"   ✅ Loaded {len(users)} users")


def seed_memories(container, dry_run: bool = False):
    """Load memories from memories.json and generate embeddings if needed"""
    print("\n🧠 Loading MEMORIES...")
    memories = load_json_file("memories.json")

    if not memories:
        print("   ⚠️  No memories to load")
        return

    if dry_run:
        print(f"   🔍 DRY RUN: Would load {len(memories)} memories")
        for memory in memories:
            mem_type = memory.get('memory_type', 'unknown')
            print(f"      - {memory.get('memoryId')}: {mem_type}")
        return

    for idx, memory in enumerate(memories, 1):
        try:
            # Generate embedding if not present or empty
            if not memory.get("embedding") or memory["embedding"] == []:
                print(f"   🔄 Generating embedding for memory {idx}/{len(memories)}...")
                memory["embedding"] = generate_embedding(memory["text"])

            # Handle TTL: -1 means no expiration (remove ttl field)
            if memory.get("ttl") == -1:
                memory.pop("ttl", None)

            container.upsert_item(memory)
            memory_type = memory.get('memory_type', 'unknown')
            ttl_info = "no expiration" if memory.get("ttl") is None else f"TTL={memory.get('ttl')}s"
            print(f"   ✅ Loaded memory {idx}/{len(memories)}: {memory['memoryId']} ({memory_type}, {ttl_info})")
        except Exception as e:
            print(f"   ❌ Error loading memory {memory.get('memoryId')}: {e}")

    print(f"   ✅ Loaded {len(memories)} memories with embeddings")


def seed_places(container, dry_run: bool = False):
    """Load places from separate JSON files (hotels, restaurants, activities) and generate embeddings"""
    print("\n🏨 Loading PLACES...")

    # Try to load from separate files first
    print("   📂 Loading data files...")
    hotels = load_json_file("hotels_all_cities.json")
    restaurants = load_json_file("restaurants_all_cities.json")
    activities = load_json_file("activities_all_cities.json")

    # Combine all places
    all_places = hotels + restaurants + activities

    if not all_places:
        print("   ⚠️  No places to load")
        return

    # Display statistics
    print(f"\n   📊 Data loaded:")
    print(f"      • Hotels: {len(hotels)}")
    print(f"      • Restaurants: {len(restaurants)}")
    print(f"      • Activities: {len(activities)}")
    print(f"      • Total places: {len(all_places)}")

    if dry_run:
        print(f"   🔍 DRY RUN: Would load {len(all_places)} places")
        return

    # Batch processing
    batch_size = 50
    total_batches = (len(all_places) + batch_size - 1) // batch_size

    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(all_places))
        batch = all_places[start_idx:end_idx]

        print(f"\n   📦 Processing batch {batch_idx + 1}/{total_batches} ({len(batch)} places)...")

        for idx, place in enumerate(batch, start=start_idx + 1):
            try:
                # Generate embedding if not present or empty
                if not place.get("embedding") or place["embedding"] == []:
                    description = f"{place.get('name', '')} {place.get('description', '')} {' '.join(place.get('tags', []))}"
                    place["embedding"] = generate_embedding(description)

                container.upsert_item(place)
                place_name = place.get('name', 'Unknown')
                place_type = place.get('type', 'unknown')
                geo_scope = place.get('geoScopeId', 'unknown')

                if idx % 10 == 0:  # Print every 10th item
                    print(f"   ✅ Loaded {idx}/{len(all_places)}: {place_name} ({place_type}, {geo_scope})")
            except Exception as e:
                print(f"   ❌ Error loading place {place.get('id')}: {e}")

        print(f"   ✅ Batch {batch_idx + 1}/{total_batches} complete")

    print(f"\n   ✅ Loaded {len(all_places)} places with embeddings")


def seed_trips(container, dry_run: bool = False):
    """Load trips from trips.json"""
    print("\n✈️  Loading TRIPS...")
    trips = load_json_file("trips.json")

    if not trips:
        print("   ⚠️  No trips to load")
        return

    if dry_run:
        print(f"   🔍 DRY RUN: Would load {len(trips)} trips")
        for trip in trips:
            print(f"      - {trip.get('tripId')}: {trip.get('destination')}")
        return

    for idx, trip in enumerate(trips, 1):
        try:
            container.upsert_item(trip)
            destination = trip.get('destination', 'Unknown')
            start_date = trip.get('startDate', 'N/A')
            print(f"   ✅ Loaded trip {idx}/{len(trips)}: {trip['tripId']} - {destination} (starts {start_date})")
        except Exception as e:
            print(f"   ❌ Error loading trip {trip.get('tripId')}: {e}")

    print(f"   ✅ Loaded {len(trips)} trips")


# ============================================================================
# Main Data Loading Logic
# ============================================================================

def load_data(containers_to_load: List[str] = None, dry_run: bool = False):
    """
    Load data into Cosmos DB containers
    
    Args:
        containers_to_load: List of container names to load (None = all)
        dry_run: If True, only show what would be loaded without actually loading
    """
    print("\n" + "=" * 70)
    print("🚀 Travel Assistant Data Loader")
    print("=" * 70)

    if dry_run:
        print("\n⚠️  DRY RUN MODE - No data will be loaded\n")

    # Initialize Cosmos DB client
    try:
        client = get_cosmos_client()
        database = client.get_database_client(DATABASE_NAME)
        print(f"\n✅ Connected to database: {DATABASE_NAME}")
    except Exception as e:
        print(f"\n❌ Failed to connect to Cosmos DB: {e}")
        return

    # Define container -> loader mapping
    container_loaders = {
        "Users": seed_users,
        "Memories": seed_memories,
        "Places": seed_places,
        "Trips": seed_trips,
    }

    # Determine which containers to load
    if containers_to_load:
        # Validate container names (case-insensitive)
        containers_to_load = [c.capitalize() for c in containers_to_load]
        invalid = [c for c in containers_to_load if c not in container_loaders]
        if invalid:
            print(f"\n❌ Invalid container names: {', '.join(invalid)}")
            print(f"   Valid containers: {', '.join(container_loaders.keys())}")
            return
        loaders_to_run = {k: v for k, v in container_loaders.items() if k in containers_to_load}
    else:
        loaders_to_run = container_loaders

    # Load data for each container
    for container_name, loader_func in loaders_to_run.items():
        try:
            container = database.get_container_client(container_name)
            loader_func(container, dry_run=dry_run)
        except CosmosResourceNotFoundError:
            print(f"\n❌ Container '{container_name}' not found. Please run infrastructure deployment first.")
        except Exception as e:
            print(f"\n❌ Error loading {container_name}: {e}")

    print("\n" + "=" * 70)
    if dry_run:
        print("✅ DRY RUN COMPLETE - No data was loaded")
    else:
        print("✅ DATA LOADING COMPLETE")
    print("=" * 70 + "\n")


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Load data into existing Cosmos DB containers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python data/load_data.py                           # Load all data
  python data/load_data.py --containers users places  # Load specific containers
  python data/load_data.py --dry-run                 # Preview without loading
  python data/load_data.py --containers memories --dry-run  # Preview memories only
        """
    )

    parser.add_argument(
        '--containers',
        nargs='+',
        help='Specific containers to load (Users, Memories, Places, Trips). If not specified, loads all.'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be loaded without actually loading data'
    )

    args = parser.parse_args()

    # Verify environment variables
    missing_vars = []
    if not COSMOS_ENDPOINT:
        missing_vars.append("COSMOSDB_ENDPOINT")
    if not COSMOS_KEY:
        missing_vars.append("COSMOS_KEY")

    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        print(f"   Please set them in {ENV_FILE}")
        sys.exit(1)

    # Run data loading
    load_data(containers_to_load=args.containers, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
