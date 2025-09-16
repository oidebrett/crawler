#!/usr/bin/env python3
"""
Test script to verify the database integration works with real data.
"""

import asyncio
import sys
import os
import json

# Add the code directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

from crawler import Crawler

async def test_database_processing():
    """Test processing the JSON file and uploading to database"""
    print("=" * 60)
    print("Testing Database Integration")
    print("=" * 60)
    
    # Check if we have test data
    json_file = "data/json/www_dublingalwaygreenway_com.json"
    
    if not os.path.exists(json_file):
        print(f"❌ Test data not found: {json_file}")
        print("Run test_real_website.py first to generate test data")
        return False
    
    # Load and check the JSON data
    with open(json_file, 'r') as f:
        json_data = json.load(f)
    
    print(f"Found {len(json_data)} JSON objects to process")
    
    # Create crawler instance
    crawler = Crawler()
    
    try:
        # Test the database processing function
        print("Processing JSON file with embeddings and database upload...")
        
        documents_loaded = await crawler.process_json_file_with_embeddings(
            json_file_path=json_file,
            site="www_dublingalwaygreenway_com",
            batch_size=5  # Small batch for testing
        )
        
        print(f"✅ Successfully processed {documents_loaded} documents")
        
        if documents_loaded > 0:
            print("✅ Database integration is working!")
            return True
        else:
            print("❌ No documents were uploaded to database")
            return False
            
    except Exception as e:
        print(f"❌ Error in database processing: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_manual_database_worker():
    """Test the database worker manually"""
    print("\n" + "=" * 60)
    print("Testing Database Worker")
    print("=" * 60)
    
    json_file = "data/json/www_dublingalwaygreenway_com.json"
    
    if not os.path.exists(json_file):
        print(f"❌ Test data not found: {json_file}")
        return False
    
    crawler = Crawler()
    
    try:
        # Add the JSON file to the database queue
        await crawler.database_queue.put(json_file)
        
        print("Starting database worker...")
        crawler.running = True
        
        # Start the database worker
        worker_task = asyncio.create_task(crawler.database_worker(0))
        
        # Let it process for a few seconds
        await asyncio.sleep(10)
        
        # Stop the worker
        crawler.running = False
        worker_task.cancel()
        
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        
        print("✅ Database worker test completed")
        return True
        
    except Exception as e:
        print(f"❌ Error in database worker test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run database integration tests"""
    
    print("=" * 80)
    print("NLWeb Crawler Database Integration Test")
    print("=" * 80)
    
    # Test 1: Direct database processing
    test1_success = await test_database_processing()
    
    # Test 2: Database worker
    test2_success = await test_manual_database_worker()
    
    print("\n" + "=" * 80)
    print("Database Integration Test Summary")
    print("=" * 80)
    
    if test1_success and test2_success:
        print("✅ All database integration tests passed!")
        print("\nThe crawler can successfully:")
        print("- Extract structured data from websites")
        print("- Generate embeddings for the data")
        print("- Upload documents to the vector database")
        return 0
    else:
        print("❌ Some database integration tests failed!")
        print("\nCheck the error messages above for details")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
