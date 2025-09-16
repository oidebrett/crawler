#!/usr/bin/env python3
"""
Script to fix the Qdrant collection with the correct vector size for OpenAI embeddings.
"""

import sys
import os

# Add the external NLWeb project to the path
sys.path.insert(0, '/home/ivob/Projects/NLWebProjects/dev/NLWeb/code/python')

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    from core.config import CONFIG
    print("✅ Successfully imported Qdrant client and config")
except ImportError as e:
    print(f"❌ Error importing Qdrant modules: {e}")
    sys.exit(1)

# Database configuration
DB_PATH = "/home/ivob/Projects/NLWebProjects/dev/NLWeb/data/db"
COLLECTION_NAME = "nlweb_collection"
OPENAI_EMBEDDING_SIZE = 1536  # OpenAI text-embedding-ada-002 and text-embedding-3-small

def get_qdrant_client():
    """Get Qdrant client instance"""
    try:
        client = QdrantClient(path=DB_PATH)
        return client
    except Exception as e:
        print(f"❌ Error connecting to Qdrant database: {e}")
        return None

def check_current_collection():
    """Check the current collection configuration"""
    print("=" * 60)
    print("Checking Current Collection Configuration")
    print("=" * 60)
    
    client = get_qdrant_client()
    if not client:
        return None
    
    try:
        collections = client.get_collections()
        print(f"📊 Number of collections: {len(collections.collections)}")
        
        for collection in collections.collections:
            if collection.name == COLLECTION_NAME:
                collection_info = client.get_collection(collection.name)
                print(f"🗂️  Collection: {collection.name}")
                print(f"   📈 Vector count: {collection_info.points_count}")
                print(f"   📏 Vector size: {collection_info.config.params.vectors.size}")
                print(f"   📐 Distance metric: {collection_info.config.params.vectors.distance}")
                return collection_info
        
        print(f"❌ Collection '{COLLECTION_NAME}' not found")
        return None
        
    except Exception as e:
        print(f"❌ Error checking collection: {e}")
        return None

def recreate_collection():
    """Recreate the collection with the correct vector size"""
    print("=" * 60)
    print("Recreating Collection with Correct Vector Size")
    print("=" * 60)
    
    client = get_qdrant_client()
    if not client:
        return False
    
    try:
        # Check if collection exists
        try:
            existing_collection = client.get_collection(COLLECTION_NAME)
            print(f"⚠️  Collection '{COLLECTION_NAME}' exists with vector size {existing_collection.config.params.vectors.size}")
            
            if existing_collection.config.params.vectors.size == OPENAI_EMBEDDING_SIZE:
                print(f"✅ Collection already has correct vector size ({OPENAI_EMBEDDING_SIZE})")
                return True
            
            # Ask for confirmation to delete
            response = input(f"Delete existing collection and recreate with size {OPENAI_EMBEDDING_SIZE}? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Operation cancelled")
                return False
            
            # Delete existing collection
            client.delete_collection(COLLECTION_NAME)
            print(f"🗑️  Deleted existing collection '{COLLECTION_NAME}'")
            
        except Exception:
            print(f"📝 Collection '{COLLECTION_NAME}' does not exist, creating new one")
        
        # Create new collection with correct vector size
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=OPENAI_EMBEDDING_SIZE,
                distance=Distance.COSINE
            )
        )
        
        print(f"✅ Created collection '{COLLECTION_NAME}' with vector size {OPENAI_EMBEDDING_SIZE}")
        
        # Verify the collection
        new_collection = client.get_collection(COLLECTION_NAME)
        print(f"✅ Verified: Collection has vector size {new_collection.config.params.vectors.size}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error recreating collection: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_config():
    """Check the embedding configuration"""
    print("=" * 60)
    print("Checking Embedding Configuration")
    print("=" * 60)
    
    try:
        print(f"📊 Preferred embedding provider: {CONFIG.preferred_embedding_provider}")
        provider_config = CONFIG.get_embedding_provider(CONFIG.preferred_embedding_provider)
        if provider_config:
            print(f"📊 Model: {provider_config.model}")
            print(f"📊 Provider config: {provider_config}")
        else:
            print("❌ No provider config found")
            
        print(f"📊 Write endpoint: {CONFIG.write_endpoint}")
        
        # Check if the write endpoint is configured correctly
        if hasattr(CONFIG, 'retrieval_endpoints'):
            if CONFIG.write_endpoint in CONFIG.retrieval_endpoints:
                endpoint_config = CONFIG.retrieval_endpoints[CONFIG.write_endpoint]
                print(f"📊 Write endpoint config: {endpoint_config}")
            else:
                print(f"❌ Write endpoint '{CONFIG.write_endpoint}' not found in retrieval_endpoints")
        
    except Exception as e:
        print(f"❌ Error checking config: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    print("Qdrant Collection Fixer")
    print("=" * 40)
    
    # Check current configuration
    check_config()
    
    # Check current collection
    current_collection = check_current_collection()
    
    if current_collection:
        current_size = current_collection.config.params.vectors.size
        if current_size != OPENAI_EMBEDDING_SIZE:
            print(f"\n⚠️  Vector size mismatch!")
            print(f"   Current: {current_size}")
            print(f"   Required: {OPENAI_EMBEDDING_SIZE}")
            print(f"   This explains why uploads appear successful but no data is stored.")
            
            # Recreate collection
            if recreate_collection():
                print(f"\n✅ Collection fixed! You can now upload data successfully.")
            else:
                print(f"\n❌ Failed to fix collection.")
        else:
            print(f"\n✅ Collection has correct vector size ({OPENAI_EMBEDDING_SIZE})")
    else:
        print(f"\n📝 No collection found, creating new one...")
        if recreate_collection():
            print(f"\n✅ Collection created successfully!")
        else:
            print(f"\n❌ Failed to create collection.")

if __name__ == "__main__":
    main()
