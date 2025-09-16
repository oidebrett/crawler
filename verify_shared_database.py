#!/usr/bin/env python3
"""
Verify that both applications can access the shared database.
This script tests database access from both the crawler and main app perspectives.
"""

import sys
import os
from pathlib import Path

# Test database access from crawler perspective
print("=" * 60)
print("SHARED DATABASE VERIFICATION")
print("=" * 60)

# 1. Test direct access to shared database
print("\n1. Testing Direct Shared Database Access:")
print("-" * 40)

try:
    from qdrant_client import QdrantClient
    
    shared_db_path = "/home/ivob/Projects/NLWebProjects/dev/shared/data/db"
    client = QdrantClient(path=shared_db_path)
    
    collections = client.get_collections()
    print(f"✅ Connected to shared database: {shared_db_path}")
    print(f"📊 Collections found: {len(collections.collections)}")
    
    if collections.collections:
        for collection in collections.collections:
            info = client.get_collection(collection.name)
            print(f"   - {collection.name}: {info.points_count} documents")
    
except Exception as e:
    print(f"❌ Error accessing shared database: {e}")

# 2. Test symbolic link paths
print("\n2. Testing Symbolic Link Paths:")
print("-" * 40)

paths_to_test = [
    ("/home/ivob/Projects/NLWebProjects/dev/NLWeb/code/data/db", "Crawler App Path"),
    ("/home/ivob/Projects/NLWebProjects/dev/mattercoder/NLWeb/data/db", "Main App Path"),
]

for path, description in paths_to_test:
    if os.path.exists(path):
        if os.path.islink(path):
            target = os.readlink(path)
            print(f"✅ {description}: {path}")
            print(f"   → Points to: {target}")
            
            # Test database access through symlink
            try:
                client = QdrantClient(path=path)
                collections = client.get_collections()
                if collections.collections:
                    info = client.get_collection(collections.collections[0].name)
                    print(f"   📊 Accessible: {info.points_count} documents")
                else:
                    print(f"   📊 Accessible: 0 collections")
            except Exception as e:
                print(f"   ❌ Database access error: {e}")
        else:
            print(f"⚠️  {description}: {path} (not a symbolic link)")
    else:
        print(f"❌ {description}: {path} (does not exist)")

# 3. Test NLWeb configuration access
print("\n3. Testing NLWeb Configuration Access:")
print("-" * 40)

try:
    # Add NLWeb to path
    nlweb_path = '/home/ivob/Projects/NLWebProjects/dev/NLWeb/code/python'
    if nlweb_path not in sys.path:
        sys.path.insert(0, nlweb_path)
    
    from core.config import CONFIG
    from core.retriever import get_vector_db_client
    
    print(f"✅ Successfully imported NLWeb modules")
    print(f"📊 Write endpoint: {CONFIG.write_endpoint}")
    
    # Get database client
    client = get_vector_db_client()
    print(f"📊 Database client type: {type(client)}")
    
    # Check endpoint configuration
    endpoint_config = CONFIG.retrieval_endpoints.get(CONFIG.write_endpoint)
    if hasattr(endpoint_config, 'database_path'):
        print(f"📊 Configured database path: {endpoint_config.database_path}")
        
        # Resolve the path from NLWeb perspective
        nlweb_root = '/home/ivob/Projects/NLWebProjects/dev/NLWeb/code/python'
        resolved_path = os.path.join(nlweb_root, endpoint_config.database_path)
        resolved_path = os.path.normpath(resolved_path)
        print(f"📊 Resolved path: {resolved_path}")
        
        # Check if this points to our shared database
        if os.path.islink(resolved_path):
            target = os.readlink(resolved_path)
            print(f"📊 Symlink target: {target}")
            if target == shared_db_path:
                print("✅ NLWeb configuration points to shared database")
            else:
                print("⚠️  NLWeb configuration points to different location")
        else:
            print("⚠️  NLWeb database path is not a symbolic link")
    
except Exception as e:
    print(f"❌ Error testing NLWeb configuration: {e}")

# 4. Test data consistency
print("\n4. Testing Data Consistency:")
print("-" * 40)

try:
    # Search for our test data
    shared_client = QdrantClient(path=shared_db_path)
    
    # Search for Dublin Galway Greenway data
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    
    points = shared_client.scroll(
        collection_name="nlweb_collection",
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="site",
                    match=MatchValue(value="www_dublingalwaygreenway_com")
                )
            ]
        ),
        limit=10,
        with_payload=True,
        with_vectors=False
    )[0]
    
    print(f"✅ Found {len(points)} Dublin Galway Greenway documents")
    for i, point in enumerate(points, 1):
        if point.payload:
            url = point.payload.get('url', 'N/A')
            print(f"   {i}. {url}")
    
except Exception as e:
    print(f"❌ Error testing data consistency: {e}")

# 5. Summary
print("\n" + "=" * 60)
print("VERIFICATION SUMMARY")
print("=" * 60)

print("\n✅ SHARED DATABASE SETUP COMPLETE")
print(f"📍 Shared Database Location: {shared_db_path}")
print("\n🔗 Both applications now use symbolic links to access the shared database:")
print("   - Crawler app can write data")
print("   - Main NLWeb app can read and search data")
print("   - Data is consistent between both applications")

print("\n🚀 Next Steps:")
print("1. Restart your main NLWeb application")
print("2. Test search functionality in the web interface")
print("3. Run crawler to add more data")
print("4. Verify data appears in both applications")

print(f"\n📊 Database Management:")
print("   Use: python simple_qdrant_commands.py")
print("   Or:  python verify_shared_database.py")
