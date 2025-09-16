#!/usr/bin/env python3
"""
Script to inspect the Qdrant database and verify uploaded data.
Provides commands to examine, modify, and delete collections.
"""

import sys
import os
import json
from datetime import datetime

# Add the external NLWeb project to the path
sys.path.insert(0, '/home/ivob/Projects/NLWebProjects/dev/NLWeb/code/python')

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    from core.config import CONFIG
    print("✅ Successfully imported Qdrant client and config")
except ImportError as e:
    print(f"❌ Error importing Qdrant modules: {e}")
    print("Make sure qdrant-client is installed: pip install qdrant-client")
    sys.exit(1)

# Database configuration - try multiple possible paths
DB_PATHS = [
    "/home/ivob/Projects/NLWebProjects/dev/NLWeb/code/data/db",  # This is where data is actually stored
    "/home/ivob/Projects/NLWebProjects/dev/NLWeb/data/db",
    "/home/ivob/Projects/NLWebProjects/dev/data/db",
    "../data/db"
]
COLLECTION_NAME = "nlweb_collection"

def get_qdrant_client():
    """Get Qdrant client instance - try multiple paths"""
    for db_path in DB_PATHS:
        if os.path.exists(db_path):
            try:
                client = QdrantClient(path=db_path)
                print(f"✅ Connected to database at: {db_path}")
                return client, db_path
            except Exception as e:
                print(f"❌ Error connecting to {db_path}: {e}")
                continue

    print(f"❌ Could not connect to any database path: {DB_PATHS}")
    return None, None

def inspect_database():
    """Inspect the Qdrant database and show basic information"""
    print("=" * 60)
    print("Qdrant Database Inspection")
    print("=" * 60)

    client, db_path = get_qdrant_client()
    if not client:
        return
    
    try:
        # Get collection info
        collections = client.get_collections()
        print(f"📊 Database path: {db_path}")
        print(f"📊 Number of collections: {len(collections.collections)}")
        
        for collection in collections.collections:
            print(f"\n🗂️  Collection: {collection.name}")
            
            # Get collection details
            collection_info = client.get_collection(collection.name)
            print(f"   📈 Vector count: {collection_info.points_count}")
            print(f"   📏 Vector size: {collection_info.config.params.vectors.size}")
            print(f"   📐 Distance metric: {collection_info.config.params.vectors.distance}")
            
            # Get some sample points
            if collection_info.points_count > 0:
                print(f"\n   🔍 Sample points:")
                points = client.scroll(
                    collection_name=collection.name,
                    limit=3,
                    with_payload=True,
                    with_vectors=False
                )[0]
                
                for i, point in enumerate(points, 1):
                    print(f"      Point {i}:")
                    print(f"         ID: {point.id}")
                    if point.payload:
                        # Show key payload fields
                        payload_keys = list(point.payload.keys())
                        print(f"         Payload keys: {payload_keys}")
                        
                        # Show specific fields if they exist
                        if 'url' in point.payload:
                            print(f"         URL: {point.payload['url']}")
                        if 'site' in point.payload:
                            print(f"         Site: {point.payload['site']}")
                        if 'name' in point.payload:
                            print(f"         Name: {point.payload['name'][:100]}...")
                        if '@type' in point.payload:
                            print(f"         Type: {point.payload['@type']}")
            else:
                print("   ⚠️  No points found in collection")
                
    except Exception as e:
        print(f"❌ Error inspecting database: {e}")
        import traceback
        traceback.print_exc()

def search_database(query_text="Dublin Galway Greenway", limit=5):
    """Search the database for similar content"""
    print("=" * 60)
    print(f"Searching Database for: '{query_text}'")
    print("=" * 60)
    
    client = get_qdrant_client()
    if not client:
        return
    
    try:
        # First check if collection exists and has points
        collection_info = client.get_collection(COLLECTION_NAME)
        if collection_info.points_count == 0:
            print("⚠️  Collection is empty - no points to search")
            return
        
        # For a real search, we'd need to generate embeddings for the query
        # For now, let's just show some points with filters
        print(f"🔍 Showing {limit} points from the collection:")
        
        points = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )[0]
        
        for i, point in enumerate(points, 1):
            print(f"\n📄 Document {i}:")
            print(f"   ID: {point.id}")
            if point.payload:
                if 'url' in point.payload:
                    print(f"   URL: {point.payload['url']}")
                if 'site' in point.payload:
                    print(f"   Site: {point.payload['site']}")
                if 'name' in point.payload:
                    print(f"   Name: {point.payload['name']}")
                if '@type' in point.payload:
                    print(f"   Type: {point.payload['@type']}")
                if 'schema_json' in point.payload:
                    # Parse and show some JSON content
                    try:
                        schema_data = json.loads(point.payload['schema_json'])
                        if 'headline' in schema_data:
                            print(f"   Headline: {schema_data['headline']}")
                        if 'description' in schema_data:
                            desc = schema_data['description'][:150] + "..." if len(schema_data['description']) > 150 else schema_data['description']
                            print(f"   Description: {desc}")
                    except:
                        pass
                        
    except Exception as e:
        print(f"❌ Error searching database: {e}")
        import traceback
        traceback.print_exc()

def count_by_site():
    """Count documents by site"""
    print("=" * 60)
    print("Document Count by Site")
    print("=" * 60)

    client, db_path = get_qdrant_client()
    if not client:
        return
    
    try:
        collection_info = client.get_collection(COLLECTION_NAME)
        if collection_info.points_count == 0:
            print("⚠️  Collection is empty")
            return
        
        # Get all points and count by site
        points = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=10000,  # Adjust if you have more documents
            with_payload=True,
            with_vectors=False
        )[0]
        
        site_counts = {}
        type_counts = {}
        
        for point in points:
            if point.payload:
                site = point.payload.get('site', 'unknown')
                doc_type = point.payload.get('@type', 'unknown')
                
                site_counts[site] = site_counts.get(site, 0) + 1
                type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        
        print("📊 Documents by Site:")
        for site, count in sorted(site_counts.items()):
            print(f"   {site}: {count} documents")
        
        print("\n📊 Documents by Type:")
        for doc_type, count in sorted(type_counts.items()):
            print(f"   {doc_type}: {count} documents")
            
    except Exception as e:
        print(f"❌ Error counting documents: {e}")

def delete_collection(collection_name=COLLECTION_NAME):
    """Delete a collection (use with caution!)"""
    print("=" * 60)
    print(f"⚠️  WARNING: Deleting Collection '{collection_name}'")
    print("=" * 60)
    
    response = input(f"Are you sure you want to delete collection '{collection_name}'? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Operation cancelled")
        return
    
    client = get_qdrant_client()
    if not client:
        return
    
    try:
        client.delete_collection(collection_name)
        print(f"✅ Collection '{collection_name}' deleted successfully")
    except Exception as e:
        print(f"❌ Error deleting collection: {e}")

def delete_by_site(site_name):
    """Delete all documents from a specific site"""
    print("=" * 60)
    print(f"⚠️  WARNING: Deleting documents from site '{site_name}'")
    print("=" * 60)
    
    response = input(f"Are you sure you want to delete all documents from site '{site_name}'? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Operation cancelled")
        return
    
    client = get_qdrant_client()
    if not client:
        return
    
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        # Delete points with matching site
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="site",
                        match=MatchValue(value=site_name)
                    )
                ]
            )
        )
        print(f"✅ Documents from site '{site_name}' deleted successfully")
    except Exception as e:
        print(f"❌ Error deleting documents: {e}")

def main():
    """Main function with command-line interface"""
    if len(sys.argv) < 2:
        print("Qdrant Database Inspector")
        print("=" * 40)
        print("Usage:")
        print("  python inspect_qdrant_database.py inspect")
        print("  python inspect_qdrant_database.py search [query]")
        print("  python inspect_qdrant_database.py count")
        print("  python inspect_qdrant_database.py delete_collection [collection_name]")
        print("  python inspect_qdrant_database.py delete_site <site_name>")
        print()
        print("Examples:")
        print("  python inspect_qdrant_database.py inspect")
        print("  python inspect_qdrant_database.py search 'Dublin Galway'")
        print("  python inspect_qdrant_database.py count")
        print("  python inspect_qdrant_database.py delete_site www_dublingalwaygreenway_com")
        return
    
    command = sys.argv[1].lower()
    
    if command == "inspect":
        inspect_database()
    elif command == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else "Dublin Galway Greenway"
        search_database(query)
    elif command == "count":
        count_by_site()
    elif command == "delete_collection":
        collection_name = sys.argv[2] if len(sys.argv) > 2 else COLLECTION_NAME
        delete_collection(collection_name)
    elif command == "delete_site":
        if len(sys.argv) < 3:
            print("❌ Error: Please specify site name")
            print("Usage: python inspect_qdrant_database.py delete_site <site_name>")
            return
        site_name = sys.argv[2]
        delete_by_site(site_name)
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: inspect, search, count, delete_collection, delete_site")

if __name__ == "__main__":
    main()
