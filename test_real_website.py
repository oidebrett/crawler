#!/usr/bin/env python3
"""
Test script to verify the complete pipeline using a real website.
Tests: https://www.dublingalwaygreenway.com/sitemap.xml
"""

import asyncio
import sys
import os
import shutil
import json
from datetime import datetime

# Add the code directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

from crawler import Crawler

async def clean_test_data():
    """Clean up any existing test data"""
    print("Cleaning up existing test data...")
    
    # Remove existing data for the test site
    test_site = "www_dublingalwaygreenway_com"
    
    dirs_to_clean = [
        f"data/json/{test_site}.json",
        f"data/urls/{test_site}.txt",
        f"data/status/{test_site}.json",
        f"data/docs/{test_site}"
    ]
    
    for path in dirs_to_clean:
        if os.path.exists(path):
            if os.path.isfile(path):
                os.remove(path)
                print(f"Removed file: {path}")
            elif os.path.isdir(path):
                shutil.rmtree(path)
                print(f"Removed directory: {path}")

async def test_sitemap_extraction():
    """Test sitemap URL extraction"""
    print("\n" + "="*60)
    print("Testing Sitemap URL Extraction")
    print("="*60)
    
    crawler = Crawler()
    
    # Test sitemap URL
    sitemap_url = "https://www.dublingalwaygreenway.com/sitemap.xml"
    
    try:
        # Extract URLs from sitemap
        urls = await crawler.extract_urls_from_sitemap(sitemap_url)
        
        print(f"Successfully extracted {len(urls)} URLs from sitemap")
        
        # Show first few URLs
        print("\nFirst 5 URLs:")
        for i, url in enumerate(urls[:5]):
            print(f"  {i+1}. {url}")
        
        if len(urls) > 5:
            print(f"  ... and {len(urls) - 5} more URLs")
            
        return urls
        
    except Exception as e:
        print(f"Error extracting URLs from sitemap: {e}")
        import traceback
        traceback.print_exc()
        return []

async def test_crawling_pipeline(urls, max_pages=5):
    """Test the complete crawling pipeline"""
    print("\n" + "="*60)
    print(f"Testing Complete Crawling Pipeline (max {max_pages} pages)")
    print("="*60)
    
    if not urls:
        print("No URLs to test with")
        return False
    
    # Limit URLs for testing
    test_urls = urls[:max_pages]
    
    crawler = Crawler()
    
    try:
        # Add URLs to crawler
        site_name = "www_dublingalwaygreenway_com"
        
        print(f"Adding {len(test_urls)} URLs to crawler for site: {site_name}")
        
        # Add URLs to the crawler's queue
        for url in test_urls:
            await crawler.url_queue.put((site_name, url))
        
        # Update site URLs tracking
        crawler.sites_urls[site_name] = test_urls
        
        print("Starting crawler workers...")
        
        # Start the crawler for a limited time
        crawler.running = True
        
        # Create session and start workers
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Start workers
            workers = []
            
            # Start URL processing workers
            for i in range(2):  # Use fewer workers for testing
                worker = asyncio.create_task(crawler.worker(session, i))
                workers.append(worker)
            
            # Start embeddings worker
            embeddings_worker = asyncio.create_task(crawler.embeddings_worker())
            workers.append(embeddings_worker)

            # Start database worker
            database_worker_task = asyncio.create_task(crawler.database_worker(0))
            workers.append(database_worker_task)
            
            # Let it run for a limited time
            print("Running crawler for 60 seconds...")
            await asyncio.sleep(60)
            
            # Stop the crawler
            print("Stopping crawler...")
            crawler.running = False
            
            # Cancel workers
            for worker in workers:
                worker.cancel()
            
            # Wait for workers to finish
            await asyncio.gather(*workers, return_exceptions=True)
        
        # Check results
        await check_results(site_name)
        
        return True
        
    except Exception as e:
        print(f"Error in crawling pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False

async def check_results(site_name):
    """Check the results of the crawling"""
    print("\n" + "="*60)
    print("Checking Results")
    print("="*60)
    
    # Check JSON file
    json_file = f"data/json/{site_name}.json"
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            json_data = json.load(f)
        print(f"✅ JSON file created: {len(json_data)} objects")
        
        # Show sample data
        if json_data:
            sample = json_data[0]
            print(f"   Sample object keys: {list(sample.keys())}")
            print(f"   Sample URL: {sample.get('url', 'N/A')}")
            print(f"   Sample @type: {sample.get('@type', 'N/A')}")
    else:
        print("❌ No JSON file created")
    
    # Check status file
    status_file = f"data/status/{site_name}.json"
    if os.path.exists(status_file):
        with open(status_file, 'r') as f:
            status_data = json.load(f)
        print(f"✅ Status file created: {len(status_data)} entries")
    else:
        print("❌ No status file created")
    
    # Check docs directory
    docs_dir = f"data/docs/{site_name}"
    if os.path.exists(docs_dir):
        doc_files = os.listdir(docs_dir)
        print(f"✅ Docs directory created: {len(doc_files)} files")
    else:
        print("❌ No docs directory created")

async def main():
    """Run all tests"""
    
    print("=" * 80)
    print("NLWeb Crawler Real Website Test")
    print("Testing with: https://www.dublingalwaygreenway.com/sitemap.xml")
    print("=" * 80)
    
    # Clean up existing data
    await clean_test_data()
    
    # Test sitemap extraction
    urls = await test_sitemap_extraction()
    
    if not urls:
        print("❌ Sitemap extraction failed, cannot continue")
        return 1
    
    # Test crawling pipeline
    success = await test_crawling_pipeline(urls, max_pages=3)
    
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    
    if success:
        print("✅ All tests completed successfully!")
        print("\nNext steps:")
        print("1. Check the data/ directory for generated files")
        print("2. Verify database integration is working")
        print("3. Scale up to crawl more pages")
        return 0
    else:
        print("❌ Some tests failed!")
        print("\nCheck the error messages above for details")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
