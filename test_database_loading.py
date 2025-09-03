#!/usr/bin/env python3
"""
Test script to verify the database loading functionality works correctly.
"""

import asyncio
import sys
import os

# Add the code directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

from crawler import Crawler

async def test_database_loading():
    """Test the database loading functionality"""
    
    print("Testing database loading functionality...")
    
    # Create a crawler instance
    crawler = Crawler()
    
    # Test with the existing embeddings file
    embeddings_file = "data/embeddings/docs_digpangolin_com.json"
    site_name = "docs_digpangolin_com"
    
    if not os.path.exists(embeddings_file):
        print(f"Error: Embeddings file not found: {embeddings_file}")
        return False
    
    print(f"Testing with file: {embeddings_file}")
    print(f"Site: {site_name}")
    
    try:
        # Test the database loading function
        documents_loaded = await crawler.load_embeddings_to_database(
            file_path=embeddings_file,
            site=site_name,
            batch_size=10  # Small batch size for testing
        )
        
        print(f"Test completed successfully!")
        print(f"Documents loaded: {documents_loaded}")
        
        return True
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_json_loading():
    """Test the JSON data loading functionality"""
    
    print("\nTesting JSON data loading...")
    
    crawler = Crawler()
    site_name = "docs_digpangolin_com"
    
    try:
        url_to_json = crawler.load_json_data(site_name)
        
        print(f"Loaded {len(url_to_json)} JSON objects")
        
        # Show a sample
        if url_to_json:
            sample_url = list(url_to_json.keys())[0]
            sample_json = url_to_json[sample_url]
            print(f"Sample URL: {sample_url}")
            print(f"Sample JSON keys: {list(sample_json.keys())}")
            
        return True
        
    except Exception as e:
        print(f"JSON loading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    
    print("=" * 60)
    print("Database Loading Test Suite")
    print("=" * 60)
    
    # Test JSON loading first
    json_test_passed = await test_json_loading()
    
    # Test database loading
    db_test_passed = await test_database_loading()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print(f"JSON Loading Test: {'PASSED' if json_test_passed else 'FAILED'}")
    print(f"Database Loading Test: {'PASSED' if db_test_passed else 'FAILED'}")
    
    if json_test_passed and db_test_passed:
        print("All tests PASSED! ✅")
        return 0
    else:
        print("Some tests FAILED! ❌")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
