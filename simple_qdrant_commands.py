#!/usr/bin/env python3
"""
Simple Python commands to examine, modify, and delete collections from Qdrant database.
"""

import sys
import os

# Add the external NLWeb project to the path
sys.path.insert(0, '/home/ivob/Projects/NLWebProjects/dev/NLWeb/code/python')

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Database path where data is actually stored (now shared)
DB_PATH = "/home/ivob/Projects/NLWebProjects/dev/shared/data/db"
COLLECTION_NAME = "nlweb_collection"

def get_client():
    """Get Qdrant client"""
    return QdrantClient(path=DB_PATH)

# Basic inspection commands
def show_collections():
    """Show all collections"""
    client = get_client()
    collections = client.get_collections()
    print("Collections:")
    for collection in collections.collections:
        info = client.get_collection(collection.name)
        print(f"  {collection.name}: {info.points_count} points")

def show_collection_info():
    """Show detailed collection information"""
    client = get_client()
    info = client.get_collection(COLLECTION_NAME)
    print(f"Collection: {COLLECTION_NAME}")
    print(f"  Points: {info.points_count}")
    print(f"  Vector size: {info.config.params.vectors.size}")
    print(f"  Distance: {info.config.params.vectors.distance}")

def count_by_site():
    """Count documents by site"""
    client = get_client()
    points = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=10000,
        with_payload=True,
        with_vectors=False
    )[0]
    
    site_counts = {}
    for point in points:
        if point.payload:
            site = point.payload.get('site', 'unknown')
            site_counts[site] = site_counts.get(site, 0) + 1
    
    print("Documents by site:")
    for site, count in sorted(site_counts.items()):
        print(f"  {site}: {count}")

def search_by_site(site_name):
    """Search for documents from a specific site"""
    client = get_client()
    
    # Use scroll with filter to find documents from specific site
    points = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="site",
                    match=MatchValue(value=site_name)
                )
            ]
        ),
        limit=100,
        with_payload=True,
        with_vectors=False
    )[0]
    
    print(f"Documents from site '{site_name}':")
    for i, point in enumerate(points, 1):
        print(f"  {i}. ID: {point.id}")
        if point.payload:
            print(f"     URL: {point.payload.get('url', 'N/A')}")
            print(f"     Name: {point.payload.get('name', 'N/A')[:100]}...")

def delete_by_site(site_name):
    """Delete all documents from a specific site"""
    client = get_client()
    
    # Delete points with matching site
    result = client.delete(
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
    print(f"Deleted documents from site '{site_name}': {result}")

def delete_collection():
    """Delete the entire collection"""
    client = get_client()
    client.delete_collection(COLLECTION_NAME)
    print(f"Deleted collection '{COLLECTION_NAME}'")

def recreate_collection():
    """Recreate collection with correct settings"""
    from qdrant_client.models import Distance, VectorParams
    
    client = get_client()
    
    # Delete if exists
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing collection '{COLLECTION_NAME}'")
    except:
        pass
    
    # Create new collection
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=1536,  # OpenAI embedding size
            distance=Distance.COSINE
        )
    )
    print(f"Created collection '{COLLECTION_NAME}' with 1536-dimensional vectors")

# Example usage functions
def show_dublin_galway_data():
    """Show our Dublin Galway Greenway data"""
    print("Dublin Galway Greenway Data:")
    search_by_site("www_dublingalwaygreenway_com")

def show_sample_data():
    """Show sample data from database"""
    client = get_client()
    points = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=5,
        with_payload=True,
        with_vectors=False
    )[0]
    
    print("Sample documents:")
    for i, point in enumerate(points, 1):
        print(f"  {i}. Site: {point.payload.get('site', 'N/A')}")
        print(f"     URL: {point.payload.get('url', 'N/A')}")
        print(f"     Name: {point.payload.get('name', 'N/A')[:80]}...")
        print()

if __name__ == "__main__":
    print("Qdrant Database Commands")
    print("=" * 40)
    print()
    
    # Show basic info
    print("1. Collection Info:")
    show_collection_info()
    print()
    
    print("2. Count by Site:")
    count_by_site()
    print()
    
    print("3. Dublin Galway Greenway Data:")
    show_dublin_galway_data()
    print()
    
    print("4. Sample Data:")
    show_sample_data()
    
    print("\nAvailable functions:")
    print("- show_collections()")
    print("- show_collection_info()")
    print("- count_by_site()")
    print("- search_by_site('site_name')")
    print("- delete_by_site('site_name')")
    print("- delete_collection()")
    print("- recreate_collection()")
    print("- show_dublin_galway_data()")
    print("- show_sample_data()")
    
    print(f"\nDatabase path: {DB_PATH}")
    print(f"Collection name: {COLLECTION_NAME}")
