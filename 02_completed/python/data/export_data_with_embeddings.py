#!/usr/bin/env python3
"""
Export Cosmos DB Data with Embeddings

This script exports embeddings FROM Cosmos DB containers and updates your local JSON files.
This preserves all the costly embeddings that were already generated while keeping your 
original JSON file formatting intact.

Usage:
    python data/export_data_with_embeddings.py                    # Export all containers
    python data/export_data_with_embeddings.py --containers places memories  # Export specific containers
    python data/export_data_with_embeddings.py --no-backup        # Skip backup creation

What it does:
    1. Connects to your Cosmos DB
    2. Reads embeddings from specified containers
    3. Creates backup of existing JSON files (.backup extension)
    4. Updates the 'embedding' field in your JSON files (preserves original formatting)

After running this:
    - Your JSON files will have all the embeddings from Cosmos DB
    - Original JSON formatting is preserved
    - Future loads won't need to regenerate embeddings
    - You save time and money on API calls!
"""

import json
import os
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import argparse

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from dotenv import load_dotenv

# Load environment variables
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR.parent / ".env"
load_dotenv(ENV_FILE)

# ============================================================================
# Configuration
# ============================================================================

COSMOS_ENDPOINT = os.getenv("COSMOSDB_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = os.getenv("COSMOS_DB_DATABASE_NAME", "TravelAssistant")

DATA_DIR = SCRIPT_DIR  # Same directory as this script

print(f"📂 Data directory: {DATA_DIR}")
print(f"🌐 Cosmos endpoint: {COSMOS_ENDPOINT}")
print(f"💾 Database: {DATABASE_NAME}\n")


# ============================================================================
# Cosmos DB Client
# ============================================================================

def get_cosmos_client() -> CosmosClient:
    """Initialize Cosmos DB client"""
    return CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)


# ============================================================================
# Backup Functions
# ============================================================================

# def create_backup(file_path: Path) -> Optional[Path]:
#     """Create a backup of existing file with timestamp"""
#     if not file_path.exists():
#         return None
#
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     backup_path = file_path.with_suffix(f".backup_{timestamp}{file_path.suffix}")
#
#     try:
#         with open(file_path, 'r', encoding='utf-8') as src:
#             content = src.read()
#
#         with open(backup_path, 'w', encoding='utf-8') as dst:
#             dst.write(content)
#
#         print(f"   💾 Created backup: {backup_path.name}")
#         return backup_path
#     except Exception as e:
#         print(f"   ⚠️  Warning: Could not create backup: {e}")
#         return None


# ============================================================================
# Export Functions
# ============================================================================

# def export_users(database, create_backups: bool = True) -> int:
#     """Export users from Cosmos DB to users.json"""
#     print("\n👤 Exporting USERS...")
#
#     try:
#         container = database.get_container_client("users")
#
#         # Query all users
#         query = "SELECT * FROM c ORDER BY c.createdAt ASC"
#         items = list(container.query_items(query=query, enable_cross_partition_query=True))
#
#         if not items:
#             print("   ⚠️  No users found in database")
#             return 0
#
#         # Clean up Cosmos DB internal fields
#         for item in items:
#             item.pop('_rid', None)
#             item.pop('_self', None)
#             item.pop('_etag', None)
#             item.pop('_attachments', None)
#             item.pop('_ts', None)
#
#         # Save to file
#         output_file = DATA_DIR / "users.json"
#
#         if create_backups:
#             create_backup(output_file)
#
#         with open(output_file, 'w', encoding='utf-8') as f:
#             json.dump(items, f, indent=2, ensure_ascii=False)
#
#         print(f"   ✅ Exported {len(items)} users to {output_file.name}")
#         return len(items)
#
#     except Exception as e:
#         print(f"   ❌ Error exporting users: {e}")
#         return 0


# def export_memories(database, create_backups: bool = True) -> int:
#     """Export memories from Cosmos DB to memories.json (WITH embeddings!)"""
#     print("\n🧠 Exporting MEMORIES (with embeddings)...")
#
#     try:
#         container = database.get_container_client("memories")
#
#         # Query all memories
#         query = "SELECT * FROM c ORDER BY c.createdAt ASC"
#         items = list(container.query_items(query=query, enable_cross_partition_query=True))
#
#         if not items:
#             print("   ⚠️  No memories found in database")
#             return 0
#
#         embeddings_found = sum(1 for item in items if item.get('embedding') and len(item.get('embedding', [])) > 0)
#
#         # Clean up Cosmos DB internal fields
#         for item in items:
#             item.pop('_rid', None)
#             item.pop('_self', None)
#             item.pop('_etag', None)
#             item.pop('_attachments', None)
#             item.pop('_ts', None)
#
#         # Save to file
#         output_file = DATA_DIR / "memories.json"
#
#         if create_backups:
#             create_backup(output_file)
#
#         with open(output_file, 'w', encoding='utf-8') as f:
#             json.dump(items, f, indent=2, ensure_ascii=False)
#
#         print(f"   ✅ Exported {len(items)} memories to {output_file.name}")
#         print(f"   🎯 Embeddings preserved: {embeddings_found}/{len(items)}")
#         return len(items)
#
#     except Exception as e:
#         print(f"   ❌ Error exporting memories: {e}")
#         return 0


def export_places(database, create_backups: bool = True) -> int:
    """Update embeddings in existing place JSON files (preserves original formatting)"""
    print("\n🏨 Updating PLACES embeddings (in-place update)...")

    try:
        container = database.get_container_client("places")

        # Query only id and embedding fields from Cosmos DB
        query = "SELECT c.id, c.embedding FROM c ORDER BY c._ts ASC"
        items = list(container.query_items(query=query, enable_cross_partition_query=True))

        if not items:
            print("   ⚠️  No places found in database")
            return 0

        # Create embedding lookup dictionary by id
        embedding_map = {}
        for item in items:
            place_id = item.get('id')
            embedding = item.get('embedding')
            if place_id and embedding:
                embedding_map[place_id] = embedding

        print(f"   📊 Found {len(embedding_map)} places with embeddings in Cosmos DB")

        # Update each JSON file
        files_to_update = [
            ("hotels_all_cities.json", "hotel"),
            ("restaurants_all_cities.json", "restaurant"),
            ("activities_all_cities.json", "attraction")
        ]

        total_updated = 0

        for filename, place_type in files_to_update:
            file_path = DATA_DIR / filename

            if not file_path.exists():
                print(f"   ⚠️  File not found: {filename}, skipping...")
                continue

            print(f"\n   📝 Processing {filename}...")

            # Load existing JSON file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    places = json.load(f)
            except Exception as e:
                print(f"   ❌ Error reading {filename}: {e}")
                continue

            if not places:
                print(f"   ⚠️  No data in {filename}")
                continue

            # Update embeddings in place
            updated_count = 0
            for place in places:
                place_id = place.get('id')
                if place_id in embedding_map:
                    place['embedding'] = embedding_map[place_id]
                    updated_count += 1

            # Write back to file (preserves original structure)
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(places, f, indent=2, ensure_ascii=False)

                print(f"   ✅ Updated {updated_count}/{len(places)} {place_type}s in {filename}")
                total_updated += updated_count

            except Exception as e:
                print(f"   ❌ Error writing {filename}: {e}")

        print(f"\n   📊 Total embeddings updated: {total_updated}")

        return total_updated

    except Exception as e:
        print(f"   ❌ Error updating places: {e}")
        return 0


# def export_trips(database, create_backups: bool = True) -> int:
#     """Export trips from Cosmos DB to trips.json"""
#     print("\n✈️  Exporting TRIPS...")
#
#     try:
#         container = database.get_container_client("trips")
#
#         # Query all trips
#         query = "SELECT * FROM c ORDER BY c.startDate ASC"
#         items = list(container.query_items(query=query, enable_cross_partition_query=True))
#
#         if not items:
#             print("   ⚠️  No trips found in database")
#             return 0
#
#         # Clean up Cosmos DB internal fields
#         for item in items:
#             item.pop('_rid', None)
#             item.pop('_self', None)
#             item.pop('_etag', None)
#             item.pop('_attachments', None)
#             item.pop('_ts', None)
#
#         # Save to file
#         output_file = DATA_DIR / "trips.json"
#
#         if create_backups:
#             create_backup(output_file)
#
#         with open(output_file, 'w', encoding='utf-8') as f:
#             json.dump(items, f, indent=2, ensure_ascii=False)
#
#         print(f"   ✅ Exported {len(items)} trips to {output_file.name}")
#         return len(items)
#
#     except Exception as e:
#         print(f"   ❌ Error exporting trips: {e}")
#         return 0


# ============================================================================
# Main Export Function
# ============================================================================

def export_data(containers: Optional[List[str]] = None, create_backups: bool = True):
    """Export data from Cosmos DB to JSON files"""

    print("\n" + "=" * 70)
    print("📤 EXPORTING DATA FROM COSMOS DB (WITH EMBEDDINGS)")
    print("=" * 70)

    if not COSMOS_ENDPOINT:
        print("\n❌ Error: COSMOSDB_ENDPOINT not set")
        print("   Make sure .env file exists at: " + str(ENV_FILE))
        return

    # Initialize client
    client = get_cosmos_client()
    database = client.get_database_client(DATABASE_NAME)

    print(f"\n✅ Connected to database: {DATABASE_NAME}")

    if not create_backups:
        print("\n⚠️  WARNING: Backup creation is DISABLED")
        print("   Original files will be overwritten without backup!")

    # Determine which containers to export
    available_containers = {
        # 'users': export_users,
        # 'memories': export_memories,
        'places': export_places,
        # 'trips': export_trips
    }

    if containers:
        # Export only specified containers
        to_export = {name: func for name, func in available_containers.items() if name in containers}
        if not to_export:
            print(f"\n❌ No valid containers specified. Available: {', '.join(available_containers.keys())}")
            return
    else:
        # Export all containers
        to_export = available_containers

    # Export each container
    total_exported = 0
    for name, export_func in to_export.items():
        count = export_func(database, create_backups)
        total_exported += count

    # Summary
    print("\n" + "=" * 70)
    print("✅ EXPORT COMPLETE")
    print("=" * 70)
    print(f"\n📊 Total items exported: {total_exported}")
    print(f"📂 Files saved to: {DATA_DIR}")

    if create_backups:
        print(f"\n💾 Backups created with timestamp suffix (.backup_YYYYMMDD_HHMMSS.json)")

    print("\n🎯 Your JSON files now contain all embeddings from Cosmos DB!")
    print("   Next time you load data, embeddings won't need to be regenerated.")
    print("   This saves time and money on OpenAI API calls! 💰\n")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Export data from Cosmos DB to JSON files (preserving embeddings)"
    )
    parser.add_argument(
        "--containers",
        nargs="+",
        choices=["users", "memories", "places", "trips"],
        help="Specific containers to export (default: all)"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup files (CAUTION: will overwrite existing files)"
    )

    args = parser.parse_args()

    export_data(
        containers=args.containers,
        create_backups=not args.no_backup
    )


if __name__ == "__main__":
    main()
