#!/usr/bin/env python3
"""
Debug script to trace exactly where the database upload is going.
"""

import sys
import os
import json

# Add the external NLWeb project to the path
sys.path.insert(0, '/home/ivob/Projects/NLWebProjects/dev/NLWeb/code/python')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

try:
    from core.retriever import upload_documents, get_vector_db_client
    from data_loading.db_load_utils import prepare_documents_from_json
    from core.embedding import batch_get_embeddings
    from core.config import CONFIG
    from qdrant_client import QdrantClient
    print("✅ Successfully imported all modules")
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)

async def debug_upload():
    """Debug the upload process step by step"""
    print("=" * 60)
    print("Debugging Database Upload Process")
    print("=" * 60)
    
    # Check configuration
    print(f"📊 Write endpoint: {CONFIG.write_endpoint}")
    print(f"📊 Preferred embedding provider: {CONFIG.preferred_embedding_provider}")
    
    # Get the database client
    print("\n🔍 Getting database client...")
    client = get_vector_db_client()
    print(f"📊 Client type: {type(client)}")

    # Try to find the actual database path
    if hasattr(client, '_client'):
        print(f"📊 Internal client: {type(client._client)}")
        if hasattr(client._client, '_location'):
            print(f"📊 Database location: {client._client._location}")

    if hasattr(client, 'client'):
        print(f"📊 Client.client: {type(client.client)}")
        if hasattr(client.client, '_location'):
            print(f"📊 Actual database path: {client.client._location}")
        if hasattr(client.client, 'location'):
            print(f"📊 Client location: {client.client.location}")

    # Check all attributes to find the path
    print(f"📊 Client attributes: {[attr for attr in dir(client) if not attr.startswith('_')]}")

    # Try to get the configuration
    if hasattr(client, 'config'):
        print(f"📊 Client config: {client.config}")

    # Check if we can get the database path from CONFIG
    endpoint_config = CONFIG.retrieval_endpoints.get(CONFIG.write_endpoint, {})
    print(f"📊 Endpoint config: {endpoint_config}")
    if hasattr(endpoint_config, 'database_path'):
        print(f"📊 Configured database path: {endpoint_config.database_path}")

        # Resolve relative path
        import os
        nlweb_root = '/home/ivob/Projects/NLWebProjects/dev/NLWeb/code/python'
        resolved_path = os.path.join(nlweb_root, endpoint_config.database_path)
        resolved_path = os.path.normpath(resolved_path)
        print(f"📊 Resolved database path: {resolved_path}")

        # Check if this path exists and has data
        if os.path.exists(resolved_path):
            print(f"✅ Resolved path exists: {resolved_path}")
            try:
                direct_client = QdrantClient(path=resolved_path)
                collections = direct_client.get_collections()
                for collection in collections.collections:
                    collection_info = direct_client.get_collection(collection.name)
                    print(f"   Collection {collection.name}: {collection_info.points_count} points")
            except Exception as e:
                print(f"   Error checking resolved path: {e}")
        else:
            print(f"❌ Resolved path does not exist: {resolved_path}")
    
    # Load test data
    json_file = "data/json/www_dublingalwaygreenway_com.json"
    if not os.path.exists(json_file):
        print(f"❌ Test data not found: {json_file}")
        return
    
    with open(json_file, 'r') as f:
        json_data = json.load(f)
    
    print(f"\n📊 Found {len(json_data)} JSON objects")
    
    # Process one document
    test_obj = json_data[0]
    url = test_obj.get('url', '')
    json_str = json.dumps(test_obj)
    site = "debug_test"
    
    print(f"📊 Processing URL: {url}")
    
    # Prepare documents
    print("\n🔍 Preparing documents...")
    docs, total_chars = prepare_documents_from_json(url, json_str, site)
    print(f"📊 Prepared {len(docs)} documents, {total_chars} total characters")
    
    if docs:
        doc = docs[0]
        print(f"📊 Document keys: {list(doc.keys())}")
        
        # Generate embeddings
        print("\n🔍 Generating embeddings...")
        provider = CONFIG.preferred_embedding_provider
        provider_config = CONFIG.get_embedding_provider(provider)
        model = provider_config.model if provider_config else None
        
        texts = [doc["schema_json"]]
        embeddings = await batch_get_embeddings(texts, provider, model)
        print(f"📊 Generated {len(embeddings)} embeddings")
        print(f"📊 Embedding dimension: {len(embeddings[0]) if embeddings else 'N/A'}")
        
        # Add embedding to document
        doc["embedding"] = embeddings[0]
        
        # Upload to database
        print("\n🔍 Uploading to database...")
        print(f"📊 Document before upload: {list(doc.keys())}")
        
        # Try to upload
        try:
            result = await upload_documents([doc])
            print(f"✅ Upload result: {result}")
        except Exception as e:
            print(f"❌ Upload error: {e}")
            import traceback
            traceback.print_exc()
        
        # Check if data is in database
        print("\n🔍 Checking database after upload...")
        
        # Direct check with Qdrant client
        db_paths_to_check = [
            "/home/ivob/Projects/NLWebProjects/dev/NLWeb/data/db",
            "/home/ivob/Projects/NLWebProjects/dev/data/db",
            "../data/db",
            "data/db"
        ]
        
        for db_path in db_paths_to_check:
            if os.path.exists(db_path):
                print(f"📊 Checking database at: {db_path}")
                try:
                    direct_client = QdrantClient(path=db_path)
                    collections = direct_client.get_collections()
                    for collection in collections.collections:
                        collection_info = direct_client.get_collection(collection.name)
                        print(f"   Collection {collection.name}: {collection_info.points_count} points")
                except Exception as e:
                    print(f"   Error checking {db_path}: {e}")

async def main():
    """Main function"""
    await debug_upload()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
