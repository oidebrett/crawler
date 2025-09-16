import os
import json
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import hashlib
from datetime import datetime
import threading
import time
import random
import logging
from collections import deque

import sys
# Add the root of the external project to the system path
sys.path.append('/home/ivob/Projects/NLWebProjects/dev/NLWeb/code/python')

# Now you can import the get_embedding function
# But this requires additional pip installs
# pip install -r requirements.txt
# pyyaml>=6.0.1
# python-dotenv>=1.0.0
# openai>=1.12.0

from core.embedding import get_embedding

# Import database loading functions from external project
try:
    # Import from external project
    from core.retriever import upload_documents, get_vector_db_client
    from data_loading.db_load_utils import prepare_documents_from_json
    from core.embedding import batch_get_embeddings
    from core.config import CONFIG
    EXTERNAL_DB_AVAILABLE = True
    print("Successfully imported external database modules")
except ImportError as e:
    # Fallback to local implementations if external project not available
    EXTERNAL_DB_AVAILABLE = False
    print(f"Warning: External database modules not available: {e}")
    print("Database functionality will be limited.")

    # Create dummy functions to prevent errors
    async def upload_documents(documents, **kwargs):
        print(f"MOCK: Would upload {len(documents)} documents to database")
        return len(documents)

    def get_vector_db_client(**kwargs):
        print("MOCK: Would return database client")
        return None

    async def batch_get_embeddings(texts, provider=None, model=None):
        print(f"MOCK: Would generate embeddings for {len(texts)} texts")
        return [[0.1] * 1536 for _ in texts]  # Mock embeddings

    def prepare_documents_from_json(url, json_str, site):
        print(f"MOCK: Would prepare documents from JSON for {url}")
        return [], 0

    class CONFIG:
        preferred_embedding_provider = "mock"
        def get_embedding_provider(self, provider):
            class MockProvider:
                model = "mock-model"
            return MockProvider()

class Crawler:

    async def extract_urls_from_sitemap(self, sitemap_url):
        """Extract URLs from a sitemap XML file."""
        print(f"Extracting URLs from sitemap: {sitemap_url}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(sitemap_url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to fetch sitemap: HTTP {response.status}")

                    content = await response.text()

                    # Parse XML content
                    from bs4 import BeautifulSoup
                    try:
                        soup = BeautifulSoup(content, 'xml')
                    except Exception:
                        # Fallback to lxml or html parser
                        try:
                            soup = BeautifulSoup(content, 'lxml')
                        except Exception:
                            soup = BeautifulSoup(content, 'html.parser')

                    urls = []

                    # Look for <url><loc> elements (standard sitemap format)
                    for url_elem in soup.find_all('url'):
                        loc_elem = url_elem.find('loc')
                        if loc_elem and loc_elem.text:
                            urls.append(loc_elem.text.strip())

                    # If no URLs found, try looking for <loc> elements directly
                    if not urls:
                        for loc_elem in soup.find_all('loc'):
                            if loc_elem.text:
                                urls.append(loc_elem.text.strip())

                    # Remove duplicates while preserving order
                    seen = set()
                    unique_urls = []
                    for url in urls:
                        if url not in seen:
                            seen.add(url)
                            unique_urls.append(url)

                    print(f"Extracted {len(unique_urls)} unique URLs from sitemap")
                    return unique_urls

        except Exception as e:
            print(f"Error extracting URLs from sitemap: {e}")
            raise

    async def process_json_file_with_embeddings(self, json_file_path, site, batch_size=100):
        """
        Process a JSON file, generate embeddings, and upload to database.
        This follows the pattern from the reference code.
        """
        if not EXTERNAL_DB_AVAILABLE:
            print("Database functionality not available - external modules not imported")
            return 0

        print(f"Processing JSON file with embeddings: {json_file_path} for site {site}")

        try:
            # Load JSON data
            with open(json_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            # Handle both array and single object
            if isinstance(json_data, list):
                items = json_data
            else:
                items = [json_data]

            print(f"Found {len(items)} JSON objects to process")

            total_documents_uploaded = 0

            # Process in batches
            for i in range(0, len(items), batch_size):
                batch_items = items[i:i+batch_size]
                documents_to_upload = []

                # Prepare documents for each item in the batch
                for item in batch_items:
                    url = item.get('url', '')
                    if not url:
                        print(f"Skipping item without URL: {item.keys()}")
                        continue

                    # Convert item to JSON string
                    json_str = json.dumps(item)

                    # Prepare documents using the external function
                    docs, _ = prepare_documents_from_json(url, json_str, site)
                    documents_to_upload.extend(docs)

                if documents_to_upload:
                    # Get embedding provider configuration
                    provider = CONFIG.preferred_embedding_provider
                    provider_config = CONFIG.get_embedding_provider(provider)
                    model = provider_config.model if provider_config else None

                    # Extract texts for embedding
                    texts = [doc["schema_json"] for doc in documents_to_upload]

                    print(f"Generating embeddings for batch of {len(texts)} documents")

                    # Generate embeddings
                    embeddings = await batch_get_embeddings(texts, provider, model)

                    # Add embeddings to documents
                    for j, doc in enumerate(documents_to_upload):
                        if j < len(embeddings):
                            doc["embedding"] = embeddings[j]

                    # Upload to database
                    print(f"Uploading batch of {len(documents_to_upload)} documents to database")
                    await upload_documents(documents_to_upload)

                    total_documents_uploaded += len(documents_to_upload)
                    print(f"Successfully uploaded {len(documents_to_upload)} documents")

                # Small delay to avoid overwhelming the system
                await asyncio.sleep(1)

            print(f"Successfully processed {json_file_path}: {total_documents_uploaded} documents uploaded")
            return total_documents_uploaded

        except Exception as e:
            print(f"Error processing JSON file {json_file_path}: {e}")
            import traceback
            traceback.print_exc()
            return 0

    async def database_worker(self, worker_id: int):
        """
        Worker that processes JSON files and uploads to database with embeddings.
        This follows the pattern from the reference code.
        """
        print(f"Database worker {worker_id} started")
        while self.running:
            try:
                # Get a file path from the database queue
                file_path = await self.database_queue.get()

                print(f"Database worker {worker_id} is processing JSON file: {file_path}")

                # Extract site name from the file path
                # Assuming file path is like: data/json/site_name.json
                site_name = os.path.basename(file_path).replace('.json', '')

                try:
                    # Process the JSON file with embeddings and upload to database
                    documents_loaded = await self.process_json_file_with_embeddings(
                        json_file_path=file_path,
                        site=site_name,
                        batch_size=100
                    )
                    print(f"Successfully processed {documents_loaded} documents from {file_path}")

                except Exception as e:
                    print(f"Error processing {file_path}: {str(e)}")
                    import traceback
                    traceback.print_exc()

                # Signal that the task is done
                self.database_queue.task_done()

            except asyncio.CancelledError:
                print(f"Database worker {worker_id} cancelled.")
                break
            except Exception as e:
                print(f"An error occurred in database worker {worker_id}: {e}")
                import traceback
                traceback.print_exc()

        print(f"Database worker {worker_id} stopped.")
    def __init__(self):
        self.url_queue = asyncio.Queue()
        self.sites_urls = {}  # site_name: [urls]
        self.sites_status = {}  # site_name: status_dict
        self.last_crawled = {}  # domain: timestamp
        self.crawled_urls = {}  # site_name: set of crawled urls
        self.running = True
        self.session = None
        self.MAX_CONCURRENT = 10
        self.MIN_DELAY_SAME_SITE = 1.0  # seconds between requests to same site
        self.log_file = os.path.join('logs', 'crawler.log')
        self.error_log_file = os.path.join('logs', 'error.log')
        self.setup_logging()
        self.loop = None  # Will be set in run()
        self.pending_urls = []  # Store URLs until loop is ready
        self.domain_backoff = {}  # domain: backoff_until_timestamp
        self.site_errors = {}  # site_name: {error_code: count}
        self.deleted_sites = set()  # Track deleted sites
        self.site_queues = {}  # site_name: list of URLs
        self.last_site_index = 0  # For round-robin
        self.json_keys = {}  # site_name: set of JSON object URLs (keys)
        self.json_type_counts = {}  # site_name: {type: count}
        self.embeddings_queue = asyncio.Queue()  # Queue for embedding processing
        self.database_queue = asyncio.Queue() # Queue for database processing

        self.processed_embeddings = {}  # site_name: set of processed JSON keys
        # Chrome user agent
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def setup_logging(self):
        """Set up logging configuration."""
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        # Create a custom formatter
        formatter = logging.Formatter('%(asctime)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        
        # File handler for general logs
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(formatter)
        
        # File handler for error logs
        error_formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        error_handler = logging.FileHandler(self.error_log_file)
        error_handler.setFormatter(error_formatter)
        
        # Configure main logger
        self.logger = logging.getLogger('crawler')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        
        # Configure error logger
        self.error_logger = logging.getLogger('crawler_errors')
        self.error_logger.setLevel(logging.ERROR)
        self.error_logger.addHandler(error_handler)
        # Removed console handler to suppress terminal output
        
    def get_site_name(self, url):
        """Extract site name from URL."""
        parsed = urlparse(url)
        return parsed.netloc.replace('.', '_')
    
    def get_domain(self, url):
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc
    
    def url_to_filename(self, url):
        """Convert URL to safe filename."""
        return hashlib.md5(url.encode()).hexdigest() + '.html'
    
    def load_crawled_urls(self, site_name):
        """Load set of already crawled URLs for a site."""
        if site_name not in self.crawled_urls:
            self.crawled_urls[site_name] = set()
            docs_dir = os.path.join('data', 'docs', site_name)
            if os.path.exists(docs_dir):
                for filename in os.listdir(docs_dir):
                    if filename.endswith('.html'):
                        self.crawled_urls[site_name].add(filename)
    
    def load_json_keys(self, site_name):
        """Load set of JSON object keys (URLs) for a site."""
        if site_name not in self.json_keys:
            self.json_keys[site_name] = set()
            keys_file = os.path.join('data', 'keys', f"{site_name}.txt")
            if os.path.exists(keys_file):
                with open(keys_file, 'r') as f:
                    for line in f:
                        key = line.strip()
                        if key:
                            self.json_keys[site_name].add(key)
    
    def save_json_key(self, site_name, key):
        """Save a JSON object key to the keys file."""
        if site_name not in self.json_keys:
            self.json_keys[site_name] = set()
        
        if key not in self.json_keys[site_name]:
            self.json_keys[site_name].add(key)
            keys_dir = os.path.join('data', 'keys')
            os.makedirs(keys_dir, exist_ok=True)
            keys_file = os.path.join(keys_dir, f"{site_name}.txt")
            with open(keys_file, 'a') as f:
                f.write(key + '\n')
    
    def update_json_type_count(self, site_name, type_name):
        """Update count for a JSON type."""
        if site_name not in self.json_type_counts:
            self.json_type_counts[site_name] = {}
        
        # Handle case where @type is a list
        if isinstance(type_name, list):
            # Count each type in the list
            for t in type_name:
                if t not in self.json_type_counts[site_name]:
                    self.json_type_counts[site_name][t] = 0
                self.json_type_counts[site_name][t] += 1
        else:
            # Single type
            if type_name not in self.json_type_counts[site_name]:
                self.json_type_counts[site_name][type_name] = 0
            self.json_type_counts[site_name][type_name] += 1
    
    def is_crawled(self, site_name, url):
        """Check if URL has already been crawled."""
        self.load_crawled_urls(site_name)
        filename = self.url_to_filename(url)
        return filename in self.crawled_urls[site_name]
    
    def url_monitor_thread(self):
        """Thread that monitors the urls directory for changes."""
        # Suppressed: print("URL monitor thread started")
        last_check = {}
        
        while self.running:
            try:
                # Clean up deleted sites from last_check
                for site in list(last_check.keys()):
                    if site in self.deleted_sites:
                        del last_check[site]
                
                urls_dir = os.path.join('data', 'urls')
                if os.path.exists(urls_dir):
                    for filename in os.listdir(urls_dir):
                        if filename.endswith('.txt'):
                            filepath = os.path.join('data', 'urls', filename)
                            site_name = filename[:-4]
                            
                            # Skip deleted sites
                            if site_name in self.deleted_sites:
                                continue
                            
                            # Check if file is new or modified
                            mtime = os.path.getmtime(filepath)
                            if site_name not in last_check or mtime > last_check[site_name]:
                                last_check[site_name] = mtime
                                
                                # Read URLs from file
                                with open(filepath, 'r') as f:
                                    urls = [line.strip() for line in f if line.strip()]
                                
                                self.sites_urls[site_name] = urls
                                # Suppressed: print(f"Loaded {len(urls)} URLs for site {site_name}")
                                
                                # Skip if site has been deleted
                                if site_name not in self.deleted_sites:
                                    # Check if sitemap processing is complete
                                    status = self.get_site_status(site_name)
                                    if not status.get('sitemap_processed', False):
                                        # Sitemap still being processed, skip for now
                                        continue
                                    
                                    # Load existing JSON keys for this site
                                    self.load_json_keys(site_name)
                                    
                                    # Load existing JSON type counts from status
                                    if 'json_stats' in status and 'type_counts' in status['json_stats']:
                                        self.json_type_counts[site_name] = status['json_stats']['type_counts'].copy()
                                    
                                    # Initialize site queue if needed
                                    if site_name not in self.site_queues:
                                        self.site_queues[site_name] = []
                                    
                                    # Add new URLs to site-specific queue
                                    new_urls = []
                                    for url in urls:
                                        if not self.is_crawled(site_name, url):
                                            new_urls.append(url)
                                    
                                    if new_urls:
                                        self.site_queues[site_name].extend(new_urls)
                                        # Suppressed: print(f"Added {len(new_urls)} new URLs to {site_name} queue")
                
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                # Suppressed: print(f"Error in URL monitor thread: {e}")
                time.sleep(5)
    
    def load_processed_embeddings(self, site_name):
        """Load set of already processed embeddings for a site."""
        if site_name not in self.processed_embeddings:
            self.processed_embeddings[site_name] = set()
            embeddings_file = os.path.join('data', 'embeddings', f"{site_name}.json")
            if os.path.exists(embeddings_file):
                try:
                    with open(embeddings_file, 'r') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            # Extract keys from embeddings data
                            self.processed_embeddings[site_name] = {item['key'] for item in data if 'key' in item}
                except Exception:
                    pass
    
    def embeddings_monitor_thread(self):
        """Thread that monitors JSON files and queues items for embedding processing."""
        last_check = {}
        
        while self.running:
            try:
                json_dir = os.path.join('data', 'json')
                if os.path.exists(json_dir):
                    for filename in os.listdir(json_dir):
                        if filename.endswith('.json'):
                            filepath = os.path.join(json_dir, filename)
                            site_name = filename[:-5]
                            
                            # Skip deleted sites
                            if site_name in self.deleted_sites:
                                continue
                            
                            # Check if file is new or modified
                            mtime = os.path.getmtime(filepath)
                            if site_name not in last_check or mtime > last_check[site_name]:
                                last_check[site_name] = mtime
                                
                                # Load processed embeddings for this site
                                self.load_processed_embeddings(site_name)
                                
                                # Read JSON file and find items needing embeddings
                                try:
                                    with open(filepath, 'r') as f:
                                        json_objects = json.load(f)
                                    
                                    # Find objects that haven't been processed
                                    unprocessed = []
                                    for obj in json_objects:
                                        if 'url' in obj and obj['url'] not in self.processed_embeddings[site_name]:
                                            unprocessed.append(obj)
                                    
                                    if unprocessed:
                                        # Queue them for processing in batches
                                        for i in range(0, len(unprocessed), 100):
                                            batch = unprocessed[i:i+100]
                                            # Add to queue (will be processed by async worker)
                                            if self.loop:
                                                asyncio.run_coroutine_threadsafe(
                                                    self.embeddings_queue.put((site_name, batch)),
                                                    self.loop
                                                )
                                except Exception as e:
                                    self.error_logger.error(f"Error processing JSON for embeddings | {site_name} | {str(e)}")
                
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.error_logger.error(f"Error in embeddings monitor thread | {str(e)}")
                time.sleep(30)
    
    def get_site_status(self, site_name):
        """Get current status for a site."""
        status_file = os.path.join('data', 'status', f"{site_name}.json")
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                status = json.load(f)
                # Ensure sitemap_processed field exists
                if 'sitemap_processed' not in status:
                    status['sitemap_processed'] = True  # Default to true for compatibility
                return status
        return {'paused': False, 'total_urls': 0, 'crawled_urls': 0, 'sitemap_processed': True}
    
    async def get_next_url(self):
        """Get next URL using round-robin across sites."""
        # First, try to get from the main queue
        try:
            return await asyncio.wait_for(self.url_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            pass
        
        # If main queue is empty, use round-robin from site queues
        if not self.site_queues:
            return None
        
        # Get list of sites with URLs
        active_sites = [site for site, urls in self.site_queues.items() 
                        if urls and site not in self.deleted_sites]
        
        if not active_sites:
            return None
        
        # Round-robin through sites
        for _ in range(len(active_sites)):
            self.last_site_index = (self.last_site_index + 1) % len(active_sites)
            site_name = active_sites[self.last_site_index]
            
            if self.site_queues[site_name]:
                url = self.site_queues[site_name].pop(0)
                return (site_name, url)
        
        return None
    
    def delete_site(self, site_name):
        """Mark a site as deleted to stop crawling its URLs."""
        self.deleted_sites.add(site_name)
        # Remove from sites_urls if present
        if site_name in self.sites_urls:
            del self.sites_urls[site_name]
        # Remove from crawled_urls if present
        if site_name in self.crawled_urls:
            del self.crawled_urls[site_name]
        # Remove from site_errors if present
        if site_name in self.site_errors:
            del self.site_errors[site_name]
        # Remove from site_queues if present
        if site_name in self.site_queues:
            del self.site_queues[site_name]
        # Remove from json_keys if present
        if site_name in self.json_keys:
            del self.json_keys[site_name]
        # Remove from json_type_counts if present
        if site_name in self.json_type_counts:
            del self.json_type_counts[site_name]
        # Suppressed: print(f"Site {site_name} marked for deletion in crawler")
    
    def track_error(self, site_name, error_code):
        """Track error counts per site."""
        if site_name not in self.site_errors:
            self.site_errors[site_name] = {}
        
        error_str = str(error_code)
        if error_str not in self.site_errors[site_name]:
            self.site_errors[site_name][error_str] = 0
        
        self.site_errors[site_name][error_str] += 1
    
    def update_site_status(self, site_name, crawled_count=None):
        """Update site status."""
        status_file = os.path.join('data', 'status', f"{site_name}.json")
        status = self.get_site_status(site_name)
        
        if crawled_count is not None:
            status['crawled_urls'] = crawled_count
        
        # Add error counts
        if site_name in self.site_errors:
            status['errors'] = self.site_errors[site_name]
        
        # Add JSON type statistics
        if site_name in self.json_type_counts:
            type_counts = self.json_type_counts[site_name]
            total_objects = sum(type_counts.values())
            status['json_stats'] = {
                'total_objects': total_objects,
                'type_counts': type_counts
            }
        
        status['last_updated'] = datetime.now().isoformat()
        
        os.makedirs(os.path.join('data', 'status'), exist_ok=True)
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2)
    
    def extract_json_key(self, json_obj):
        """Extract the key (URL) from a JSON object."""
        if isinstance(json_obj, dict):
            # Check @id first as it's the standard JSON-LD identifier
            if '@id' in json_obj:
                return json_obj['@id']
            # Also check url attribute
            elif 'url' in json_obj:
                return json_obj['url']
        return None
    
    def extract_schema_org(self, html, url, site_name):
        """Extract schema.org JSON-LD from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        schema_data = []
        
        # Load existing keys for this site
        self.load_json_keys(site_name)
        
        # Find all JSON-LD script tags
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                
                # Check if this object (or objects in array/graph) already exists
                new_objects = []
                
                if isinstance(data, list):
                    # Array of objects
                    for item in data:
                        key = self.extract_json_key(item)
                        if key and key not in self.json_keys.get(site_name, set()):
                            new_objects.append(item)
                            self.save_json_key(site_name, key)
                        elif not key:
                            # No key, include it
                            new_objects.append(item)
                    
                    if new_objects:
                        # If multiple objects, we need to handle differently
                        if len(new_objects) > 1:
                            # For arrays, keep the original structure but flatten
                            flattened = {
                                'url': url,
                                'timestamp': datetime.now().isoformat(),
                                'items': new_objects
                            }
                            schema_data.append(flattened)
                            # Track type counts for each item
                            for obj in new_objects:
                                if '@type' in obj:
                                    self.update_json_type_count(site_name, obj['@type'])
                        else:
                            # Single object - flatten it
                            flattened = {
                                'url': url,
                                'timestamp': datetime.now().isoformat()
                            }
                            flattened.update(new_objects[0])
                            schema_data.append(flattened)
                            # Track type count
                            if '@type' in new_objects[0]:
                                self.update_json_type_count(site_name, new_objects[0]['@type'])
                        
                elif isinstance(data, dict):
                    if '@graph' in data:
                        # Handle @graph objects - save each item individually
                        for item in data['@graph']:
                            key = self.extract_json_key(item)
                            if key and key not in self.json_keys.get(site_name, set()):
                                self.save_json_key(site_name, key)
                                # Flatten the structure
                                flattened = {
                                    'url': url,
                                    'timestamp': datetime.now().isoformat()
                                }
                                flattened.update(item)
                                schema_data.append(flattened)
                                # Track type count
                                if '@type' in item:
                                    self.update_json_type_count(site_name, item['@type'])
                            elif not key:
                                # No key, include it
                                # Flatten the structure
                                flattened = {
                                    'url': url,
                                    'timestamp': datetime.now().isoformat()
                                }
                                flattened.update(item)
                                schema_data.append(flattened)
                                # Track type count
                                if '@type' in item:
                                    self.update_json_type_count(site_name, item['@type'])
                    else:
                        # Single object
                        key = self.extract_json_key(data)
                        if key and key not in self.json_keys.get(site_name, set()):
                            self.save_json_key(site_name, key)
                            # Flatten the structure
                            flattened = {
                                'url': url,
                                'timestamp': datetime.now().isoformat()
                            }
                            flattened.update(data)
                            schema_data.append(flattened)
                            # Track type count
                            if '@type' in data:
                                self.update_json_type_count(site_name, data['@type'])
                        elif not key:
                            # No key, include it
                            # Flatten the structure
                            flattened = {
                                'url': url,
                                'timestamp': datetime.now().isoformat()
                            }
                            flattened.update(data)
                            schema_data.append(flattened)
                            # Track type count
                            if '@type' in data:
                                self.update_json_type_count(site_name, data['@type'])
                            
            except json.JSONDecodeError:
                pass
        
        # --- If nothing was found, try to synthesize ---
        if not schema_data:
            synthesized = self.synthesize_schema(soup, url)
            if synthesized:
                schema_data.append(synthesized)

        return schema_data

    def synthesize_schema(self, soup, url):
        """Build a basic JSON-LD object from meta tags / OG tags."""
        title = soup.title.string.strip() if soup.title else None

        desc = None
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag and desc_tag.get("content"):
            desc = desc_tag["content"]

        # OpenGraph fallbacks
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = title or og_title.get("content")

        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            desc = desc or og_desc.get("content")

        image = None
        og_image = soup.find("meta", property="og:image")
        if og_image:
            image = og_image.get("content")

        # Basic heuristic for type
        schema_type = "Article" if soup.find("meta", property="article:published_time") else "WebPage"

        synthesized = {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "@context": "https://schema.org",
            "@type": schema_type,
            "headline": title,
            "description": desc,
        }
        if image:
            synthesized["image"] = image

        # Add publication info if present
        pub_date = soup.find("meta", property="article:published_time")
        if pub_date:
            synthesized["datePublished"] = pub_date.get("content")

        author = soup.find("meta", property="article:author")
        if author:
            synthesized["author"] = {"@type": "Person", "name": author.get("content")}

        return synthesized
    
    def save_schema_org(self, site_name, schema_data):
        """Save schema.org data to JSON file."""
        if not schema_data:
            return
        
        json_dir = os.path.join('data', 'json')
        os.makedirs(json_dir, exist_ok=True)
        
        json_file = os.path.join(json_dir, f"{site_name}.json")
        
        # Load existing data
        existing_data = []
        if os.path.exists(json_file):
            with open(json_file, 'r') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = []
        
        # Append new data
        existing_data.extend(schema_data)
        
        # Save back
        with open(json_file, 'w') as f:
            json.dump(existing_data, f, indent=2)
    
    def save_page(self, site_name, url, html):
        """Save crawled page to docs directory."""
        docs_dir = os.path.join('data', 'docs', site_name)
        os.makedirs(docs_dir, exist_ok=True)
        
        filename = self.url_to_filename(url)
        filepath = os.path.join(docs_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        # Update crawled URLs cache
        if site_name not in self.crawled_urls:
            self.crawled_urls[site_name] = set()
        self.crawled_urls[site_name].add(filename)
    
    async def can_crawl_domain(self, domain):
        """Check if enough time has passed since last crawl to this domain."""
        current_time = time.time()
        
        # Check if domain is in backoff period
        if domain in self.domain_backoff:
            if current_time < self.domain_backoff[domain]:
                # Still in backoff period
                return False
            else:
                # Backoff period expired
                del self.domain_backoff[domain]
        
        # Check regular rate limit
        if domain in self.last_crawled:
            elapsed = current_time - self.last_crawled[domain]
            if elapsed < self.MIN_DELAY_SAME_SITE:
                # Wait for the remaining time to ensure minimum delay
                wait_time = self.MIN_DELAY_SAME_SITE - elapsed
                await asyncio.sleep(wait_time)
        else:
            # First request to this domain, no need to wait
            pass
        
        # Update last crawled time AFTER the request completes
        # This will be done in fetch_url after successful request
        return True
    
    async def fetch_url(self, session, site_name, url):
        """Fetch a single URL."""
        try:
            # Check if site has been deleted
            if site_name in self.deleted_sites:
                # Don't process URLs from deleted sites
                return
            
            # Check if site is paused
            status = self.get_site_status(site_name)
            if status.get('paused', False):
                # Put URL back in site queue
                if site_name not in self.site_queues:
                    self.site_queues[site_name] = []
                self.site_queues[site_name].append(url)
                return
            
            # Check if already crawled
            if self.is_crawled(site_name, url):
                return
            
            # Rate limit per domain
            domain = self.get_domain(url)
            if not await self.can_crawl_domain(domain):
                # Domain is in backoff, put URL back in queue
                await self.url_queue.put((site_name, url))
                return
            
            # Fetch the page
            async with session.get(url, timeout=30, headers=self.headers) as response:
                content_length = response.headers.get('Content-Length', 'N/A')
                
                # Update last crawled time for this domain after request completes
                self.last_crawled[domain] = time.time()
                
                if response.status == 200:
                    html = await response.text()
                    
                    # Log successful fetch
                    self.logger.info(f"{url} | {response.status} | {len(html) if content_length == 'N/A' else content_length}")
                    
                    # Extract schema.org
                    schema_data = self.extract_schema_org(html, url, site_name)
                    if schema_data:
                        self.save_schema_org(site_name, schema_data)
                    
                    # Save page
                    self.save_page(site_name, url, html)
                    
                    # Update status
                    crawled_count = len(self.crawled_urls.get(site_name, set()))
                    self.update_site_status(site_name, crawled_count)
                    
                    # Suppressed: print(f"Crawled: {url}")
                else:
                    # Log failed fetch
                    self.logger.info(f"{url} | {response.status} | {content_length}")
                    # Log to error log
                    self.error_logger.error(f"HTTP {response.status} | {site_name} | {url}")
                    
                    # Track error
                    self.track_error(site_name, response.status)
                    self.update_site_status(site_name)
                    
                    # Handle 429 Too Many Requests
                    if response.status == 429:
                        # Apply backoff for this domain
                        backoff_time = random.uniform(3, 7)  # Random 3-7 seconds
                        self.domain_backoff[domain] = time.time() + backoff_time
                        # Suppressed: print(f"Rate limited on {domain}, backing off for {backoff_time:.1f} seconds")
                        
                        # Put URL back in site queue to retry later
                        if site_name not in self.site_queues:
                            self.site_queues[site_name] = []
                        self.site_queues[site_name].append(url)
                    
        except asyncio.TimeoutError:
            self.logger.info(f"{url} | TIMEOUT | 0")
            self.error_logger.error(f"TIMEOUT | {site_name} | {url}")
            self.track_error(site_name, 'TIMEOUT')
            self.update_site_status(site_name)
        except Exception as e:
            self.logger.info(f"{url} | ERROR | 0")
            self.error_logger.error(f"ERROR | {site_name} | {url} | {str(e)}")
            self.track_error(site_name, 'ERROR')
            self.update_site_status(site_name)
    
    async def worker(self, session, worker_id):
        """Worker that processes URLs from the queue."""
        while self.running:
            try:
                # Get next URL using round-robin
                result = await self.get_next_url()
                
                if result:
                    site_name, url = result
                    await self.fetch_url(session, site_name, url)
                else:
                    # No URLs available, wait a bit
                    await asyncio.sleep(1)
                
            except Exception as e:
                # Suppressed: print(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)

    async def database_worker(self, worker_id: int):
        """
        Worker that loads documents with embeddings into the vector database.
        """
        print(f"Database worker {worker_id} started")
        while self.running:
            try:
                # Get a file path from the database queue
                file_path = await self.database_queue.get()

                print(f"Database worker {worker_id} is processing embeddings file: {file_path}")

                # Extract site name from the file path
                # Assuming file path is like: data/embeddings/site_name/file.json
                site_name = os.path.basename(os.path.dirname(file_path))

                try:
                    # Process the JSON file with embeddings and upload to database
                    documents_loaded = await self.process_json_file_with_embeddings(
                        json_file_path=file_path,
                        site=site_name,
                        batch_size=100
                    )
                    print(f"Successfully processed {documents_loaded} documents from {file_path}")

                except Exception as e:
                    print(f"Error loading {file_path} to database: {str(e)}")
                    import traceback
                    traceback.print_exc()

                # Signal that the task is done
                self.database_queue.task_done()

            except asyncio.CancelledError:
                print(f"Database worker {worker_id} cancelled.")
                break
            except Exception as e:
                print(f"An error occurred in database worker {worker_id}: {e}")
                import traceback
                traceback.print_exc()

        print(f"Database worker {worker_id} stopped.")

    def prepare_text_for_embedding(self, json_obj):
        """Prepare text from JSON object for embedding."""
        # Extract key fields based on @type
        text_parts = []
        
        # Add type if present
        if '@type' in json_obj:
            obj_type = json_obj['@type']
            if isinstance(obj_type, list):
                text_parts.append(f"Type: {', '.join(obj_type)}")
            else:
                text_parts.append(f"Type: {obj_type}")
        
        # Add name/title
        if 'name' in json_obj:
            text_parts.append(f"Name: {json_obj['name']}")
        elif 'headline' in json_obj:
            text_parts.append(f"Headline: {json_obj['headline']}")
        
        # Add description
        if 'description' in json_obj:
            text_parts.append(f"Description: {json_obj['description']}")
        
        # For recipes, add ingredients
        if 'recipeIngredient' in json_obj and isinstance(json_obj['recipeIngredient'], list):
            ingredients = ', '.join(json_obj['recipeIngredient'][:10])  # First 10 ingredients
            text_parts.append(f"Ingredients: {ingredients}")
        
        # For articles, add article body (truncated)
        if 'articleBody' in json_obj:
            body = json_obj['articleBody'][:500]  # First 500 chars
            text_parts.append(f"Content: {body}")
        
        # Combine all parts
        return '\n'.join(text_parts)
    
    async def embeddings_worker(self):
        """Worker that processes embeddings queue and triggers database processing."""
        while self.running:
            try:
                # Get batch from queue with timeout
                site_name, batch = await asyncio.wait_for(
                    self.embeddings_queue.get(),
                    timeout=5.0
                )

                # Save JSON data to file (without embeddings)
                await self.save_json_data(site_name, batch)

                # Update processed set
                keys = [obj.get('url', '') for obj in batch if obj.get('url')]
                if site_name not in self.processed_embeddings:
                    self.processed_embeddings[site_name] = set()
                self.processed_embeddings[site_name].update(keys)

                self.logger.info(f"Saved {len(batch)} JSON objects for {site_name}, queued for database processing")

            except asyncio.TimeoutError:
                # No items in queue, continue
                pass
            except Exception as e:
                self.error_logger.error(f"Embeddings worker error | {str(e)}")
                await asyncio.sleep(1)
    
    async def save_json_data(self, site_name, batch):
        """Save JSON data to file and queue for database processing."""
        json_dir = os.path.join('data', 'json')
        if not os.path.exists(json_dir):
            os.makedirs(json_dir)

        json_file = os.path.join(json_dir, f"{site_name}.json")

        # Load existing JSON data
        existing_data = []
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    existing_data = json.load(f)
            except Exception:
                pass

        # Add new JSON objects with timestamp
        for obj in batch:
            # Add timestamp if not present
            if 'timestamp' not in obj:
                obj['timestamp'] = datetime.now().isoformat()
            existing_data.append(obj)

        # Write back to file
        with open(json_file, 'w') as f:
            json.dump(existing_data, f, indent=2)

        # Add the JSON file to the database queue for processing
        self.database_queue.put_nowait(json_file)

    def requeue_urls(self):
        """Requeue URLs with domain diversity."""
        # Group URLs by domain
        domain_urls = {}
        temp_queue = []
        
        # Empty current queue
        while not self.url_queue.empty():
            try:
                item = self.url_queue.get_nowait()
                temp_queue.append(item)
            except asyncio.QueueEmpty:
                break
        
        # Group by domain
        for site_name, url in temp_queue:
            domain = self.get_domain(url)
            if domain not in domain_urls:
                domain_urls[domain] = []
            domain_urls[domain].append((site_name, url))
        
        # Interleave URLs from different domains
        while domain_urls:
            domains = list(domain_urls.keys())
            random.shuffle(domains)
            
            for domain in domains:
                if domain in domain_urls and domain_urls[domain]:
                    item = domain_urls[domain].pop(0)
                    if self.loop:
                        asyncio.run_coroutine_threadsafe(
                            self.url_queue.put(item),
                            self.loop
                        )
                    else:
                        self.pending_urls.append(item)
                    
                    if not domain_urls[domain]:
                        del domain_urls[domain]
    
    async def periodic_requeue(self):
        """Periodically requeue URLs to ensure domain diversity."""
        while self.running:
            await asyncio.sleep(30)  # Every 30 seconds
            self.requeue_urls()
    
    async def run(self):
        """Main crawler loop."""
        # Set the event loop
        self.loop = asyncio.get_event_loop()
        
        # Start URL monitor thread
        monitor_thread = threading.Thread(target=self.url_monitor_thread)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Start embeddings monitor thread
        embeddings_thread = threading.Thread(target=self.embeddings_monitor_thread)
        embeddings_thread.daemon = True
        embeddings_thread.start()
        
        # Process any pending URLs that were added before loop was ready
        # (No longer needed with site queues)
        
        # Create aiohttp session
        connector = aiohttp.TCPConnector(limit=self.MAX_CONCURRENT)
        async with aiohttp.ClientSession(connector=connector) as session:
            self.session = session
            
            # Start workers
            workers = []
            for i in range(self.MAX_CONCURRENT):
                worker = asyncio.create_task(self.worker(session, i))
                workers.append(worker)
            
            # Start embeddings worker
            embeddings_worker = asyncio.create_task(self.embeddings_worker())
            workers.append(embeddings_worker)

            # Start database worker
            database_worker_task = asyncio.create_task(self.database_worker(0)) # Using worker_id 0
            workers.append(database_worker_task)

            # Wait for all workers
            await asyncio.gather(*workers, return_exceptions=True)
    
    def start(self):
        """Start the crawler."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self.run())
        except KeyboardInterrupt:
            # Suppressed: print("\nShutting down crawler...")
            self.running = False
        finally:
            self.loop.close()

if __name__ == '__main__':
    # This file is not meant to be run directly
    # The crawler is started from app.py
    print("Please run app.py instead of running crawler.py directly")