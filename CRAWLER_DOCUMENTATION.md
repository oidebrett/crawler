# NLWeb Crawler System Documentation

## Overview
This is a multi-site web crawling system with vector database integration. The system crawls websites based on their sitemaps, extracts structured data (schema.org JSON-LD), generates embeddings, and stores documents in a vector database for semantic search and analysis.

## Key Features
- **Asynchronous crawling** with configurable concurrency
- **Schema.org JSON-LD extraction** from web pages
- **Automatic embeddings generation** using OpenAI's text-embedding models
- **Vector database integration** with support for Qdrant and Azure Search
- **Docker containerization** for easy deployment
- **Real-time processing pipeline** from crawling to database storage
- **Sitemap-based URL discovery** with XML parsing
- **Batch processing** for efficient database operations

## Architecture Components

### 1. Crawler Backend (crawler.py)
- **Asynchronous crawler** using aiohttp with configurable worker pools
- **Multi-worker architecture**:
  - **URL workers**: Process URLs from queue with concurrent requests
  - **Embeddings worker**: Processes JSON data and saves to files
  - **Database worker**: Generates embeddings and uploads to vector database
- **Intelligent queuing**: Avoids consecutive calls to same website
- **Schema.org extraction**: Parses JSON-LD structured data from web pages
- **Real-time processing**: Direct pipeline from crawling to database storage

### 2. Database Integration
- **External NLWeb project integration**: Imports database utilities from adjacent project
- **Vector database support**: Qdrant and Azure Search integration
- **Embeddings generation**: OpenAI text-embedding models
- **Batch processing**: Efficient document preparation and upload
- **Document structure**: Complete documents with URL, JSON data, embeddings, and metadata

### 3. Docker Environment
- **Containerized deployment** with Docker and docker-compose
- **Development and production** configurations
- **Volume mounting** for data persistence and external project access
- **Environment variable** configuration for API keys and settings

## Directory Structure

```
crawler/
├── code/                    # Application source code
│   ├── crawler.py          # Main crawler implementation
│   ├── db_load.py          # Database loading utilities (copied from NLWeb)
│   └── qdrant_load.py      # Qdrant-specific loading functions
├── data/                   # Data storage directory
│   ├── json/               # Schema.org JSON-LD data
│   │   └── {site_name}.json
│   ├── docs/               # Crawled HTML content
│   │   └── {site_name}/
│   ├── status/             # Crawl status per site
│   │   └── {site_name}.json
│   └── urls/               # URL lists per site (if used)
│       └── {site_name}.txt
├── tbd_reference_code/     # Reference implementation examples
├── test_*.py               # Test scripts
├── docker-compose.yml      # Docker production setup
├── docker-compose.dev.yml  # Docker development setup
├── Dockerfile              # Container definition
├── docker-run.sh           # Docker helper script
├── requirements.txt        # Python dependencies
└── .env.example           # Environment variables template
```

### Directory Details:

1. **data/json/** - Aggregates all schema.org JSON-LD data found on each site
2. **data/docs/** - Stores crawled HTML pages organized by site
3. **data/status/** - JSON files tracking crawl progress and statistics
4. **code/** - Contains the main application logic and database integration
5. **tbd_reference_code/** - Reference implementations for embeddings and database operations

## Processing Pipeline

### 1. URL Discovery and Crawling
- **Sitemap extraction**: Parses XML sitemaps to discover URLs
- **Concurrent crawling**: Processes multiple URLs simultaneously with aiohttp
- **Schema.org extraction**: Identifies and extracts JSON-LD structured data
- **Content storage**: Saves both raw HTML and structured JSON data

### 2. Embeddings Generation
- **Text preparation**: Combines structured data fields into embedding-ready text
- **OpenAI integration**: Uses text-embedding models for vector generation
- **Batch processing**: Processes multiple documents efficiently

### 3. Database Integration
- **Document preparation**: Creates complete documents with metadata
- **Vector database upload**: Stores documents with embeddings in Qdrant/Azure Search
- **Real-time processing**: Direct pipeline from JSON files to database

### 4. Queue Management
- **URL queue**: Manages URLs to be crawled
- **Embeddings queue**: Handles JSON data for processing
- **Database queue**: Manages files ready for database upload

## Implementation Details

### Key Features:
1. **Asynchronous Architecture**: Uses asyncio with configurable worker pools
2. **Real-time Processing**: Direct pipeline from crawling to database storage
3. **Schema.org Extraction**: Comprehensive JSON-LD structured data parsing
4. **Vector Database Integration**: Automatic embeddings generation and storage
5. **Docker Containerization**: Easy deployment and development setup
6. **External Project Integration**: Imports database utilities from NLWeb project

### Processing Flow:
1. **URL Discovery**: Extract URLs from sitemaps using XML parsing
2. **Concurrent Crawling**:
   - Fetch page content with aiohttp
   - Extract schema.org JSON-LD data
   - Save HTML to docs/{site_name}/
   - Queue JSON data for embeddings processing
3. **Embeddings Processing**:
   - Prepare text from structured data
   - Generate embeddings using OpenAI API
   - Save JSON data to files
   - Queue files for database upload
4. **Database Upload**:
   - Load JSON data and generate embeddings
   - Create complete documents with metadata
   - Upload to vector database in batches

## Current Implementation Status

### ✅ Completed Features:
- **Asynchronous crawler architecture** with worker pools
- **Schema.org JSON-LD extraction** from web pages
- **Sitemap XML parsing** with URL discovery
- **Vector database integration** with embeddings generation
- **Docker containerization** with development and production setups
- **External project integration** for database utilities
- **Real-time processing pipeline** from crawling to database
- **Batch processing** for efficient database operations
- **Comprehensive testing** with real website validation
- **Complete documentation** and usage instructions

### 🔧 Recent Improvements:
- **Fixed database integration** to process JSON files directly instead of embeddings files
- **Added sitemap extraction** functionality for URL discovery
- **Implemented Docker setup** with proper volume mounting
- **Created test scripts** for validation and debugging
- **Updated processing pipeline** to follow reference code patterns
- **Added comprehensive error handling** and logging

## Usage Instructions

### Prerequisites
1. **Environment Setup**:
   ```bash
   # Copy environment template
   cp .env.example .env

   # Edit .env with your API keys
   # OPENAI_API_KEY=your_openai_api_key_here
   ```

2. **External Project Setup**:
   - Ensure NLWeb project is available at the configured path
   - Update docker-compose.yml volume mounts if needed

### Docker Usage (Recommended)

1. **Development Environment**:
   ```bash
   # Start development environment
   ./docker-run.sh dev

   # Or manually:
   docker-compose -f docker-compose.dev.yml up --build
   ```

2. **Production Environment**:
   ```bash
   # Start production environment
   ./docker-run.sh prod

   # Or manually:
   docker-compose up --build -d
   ```

3. **Testing**:
   ```bash
   # Run tests
   ./docker-run.sh test

   # Test with real website
   ./docker-run.sh shell
   python test_real_website.py
   ```

### Direct Python Usage

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Crawler**:
   ```bash
   # Test with real website
   python test_real_website.py

   # Test database integration
   python test_database_integration.py

   # Run main crawler (programmatic usage)
   python code/app.py
   ```

### Testing with Real Websites

The system has been tested with https://www.dublingalwaygreenway.com/sitemap.xml:

```bash
# Run the complete test
python test_real_website.py

# Expected output:
# ✅ Sitemap extraction: 84 URLs discovered
# ✅ Crawling: 3 pages processed
# ✅ JSON extraction: Schema.org data extracted
# ✅ Database integration: Documents uploaded with embeddings
```

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: Required for embeddings generation
- `GOOGLE_MAPS_API_KEY`: Optional for location-based features
- `DATA_DIR`: Data storage directory (default: ./data)
- `NLWEB_EXTERNAL_PATH`: Path to external NLWeb project

### Docker Configuration
- **Development**: Uses live code mounting for development
- **Production**: Optimized for deployment with minimal overhead
- **Data Persistence**: Data directory is mounted to host for persistence

## Shared Database Architecture

The crawler and main NLWeb application now use a **shared database architecture** to ensure data consistency and cross-application compatibility.

### Common Database Location

Both applications access the same Qdrant database through a shared location:

```
/home/ivob/Projects/NLWebProjects/dev/shared/data/db
```

### Application Database Paths

Each application uses symbolic links to access the shared database:

- **Crawler App**: `/home/ivob/Projects/NLWebProjects/dev/NLWeb/code/data/db` → shared location
- **Main NLWeb App**: `/home/ivob/Projects/NLWebProjects/dev/mattercoder/NLWeb/data/db` → shared location

### Setup Process

Run the automated setup script to configure the shared database:

```bash
cd /home/ivob/Projects/NLWebProjects/dev/crawler
./shared-database-setup.sh
```

This script:
1. Creates the shared database directory
2. Copies existing data to the shared location
3. Creates symbolic links from both applications
4. Sets appropriate permissions
5. Verifies the setup

### Docker Configuration

#### Local Development
Both applications mount the shared database:
```yaml
volumes:
  - /home/ivob/Projects/NLWebProjects/dev/shared/data/db:/app/shared/data/db
```

#### Multi-Service Deployment
Use the shared docker-compose configuration:
```bash
cd /home/ivob/Projects/NLWebProjects/dev
docker-compose -f shared-docker-compose.yml up
```

This provides:
- **Shared Qdrant Server**: Centralized database service on port 6333
- **Crawler Service**: Processes and uploads data
- **Main NLWeb Service**: Provides search interface on port 8910
- **Data Persistence**: Shared volumes for database storage

### Troubleshooting

If the main NLWeb app cannot see crawler data:

1. **Verify Setup**: `./shared-database-setup.sh`
2. **Check Database**: `python simple_qdrant_commands.py`
3. **Restart Applications**: Both apps need restart after setup

## Architecture Benefits

- **Scalable**: Asynchronous processing with configurable worker pools
- **Reliable**: Comprehensive error handling and retry logic
- **Flexible**: Supports multiple vector database backends
- **Maintainable**: Clean separation of concerns and modular design
- **Testable**: Comprehensive test suite with real website validation
- **Deployable**: Docker containerization for consistent environments
- **Cross-Compatible**: Shared database ensures data consistency between applications

#### Inspection Commands:

# Run the inspection script
cd /home/ivob/Projects/NLWebProjects/dev/crawler
python simple_qdrant_commands.py


# Basic info
show_collections()                    # List all collections
show_collection_info()               # Show collection details
count_by_site()                      # Count documents by site

# Search and browse
search_by_site('www_dublingalwaygreenway_com')  # Find documents from specific site
show_sample_data()                   # Show sample documents
show_dublin_galway_data()           # Show your uploaded data

#### Modification Commands:

# Delete operations
delete_by_site('site_name')          # Delete all documents from a site
delete_collection()                  # Delete entire collection

# Recreation
recreate_collection()                # Recreate collection with correct settings

#### Quick Usage Examples:


# Or use individual commands in Python:
python -c "
import sys; sys.path.insert(0, '/home/ivob/Projects/NLWebProjects/dev/NLWeb/code/python')
from simple_qdrant_commands import *
show_dublin_galway_data()
"

#### Direct Qdrant Client Usage:

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Connect to shared database
client = QdrantClient(path="/home/ivob/Projects/NLWebProjects/dev/shared/data/db")

# Get collection info
info = client.get_collection("nlweb_collection")
print(f"Points: {info.points_count}")

# Search by site
points = client.scroll(
    collection_name="nlweb_collection",
    scroll_filter=Filter(must=[FieldCondition(key="site", match=MatchValue(value="www_dublingalwaygreenway_com"))]),
    limit=10,
    with_payload=True
)[0]

# Delete by site
client.delete(
    collection_name="nlweb_collection",
    points_selector=Filter(must=[FieldCondition(key="site", match=MatchValue(value="site_to_delete"))])
)