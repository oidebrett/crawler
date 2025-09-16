#!/bin/bash

# Shared Database Setup Script for NLWeb Crawler and Main App
# This script creates a shared database location and configures both apps to use it

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}NLWeb Shared Database Setup${NC}"
echo "=" * 50

# Define paths
SHARED_DB_PATH="/home/ivob/Projects/NLWebProjects/dev/shared/data/db"
CRAWLER_DB_PATH="/home/ivob/Projects/NLWebProjects/dev/NLWeb/code/data/db"
MAIN_APP_DB_PATH="/home/ivob/Projects/NLWebProjects/dev/mattercoder/NLWeb/data/db"

# Create shared database directory
echo -e "${BLUE}1. Creating shared database directory...${NC}"
mkdir -p "$SHARED_DB_PATH"
echo "✅ Created: $SHARED_DB_PATH"

# Copy existing data if it exists
if [ -d "$CRAWLER_DB_PATH" ] && [ "$(ls -A $CRAWLER_DB_PATH)" ]; then
    echo -e "${BLUE}2. Copying existing database data...${NC}"
    cp -r "$CRAWLER_DB_PATH"/* "$SHARED_DB_PATH/"
    echo "✅ Copied data from: $CRAWLER_DB_PATH"
else
    echo -e "${YELLOW}2. No existing database data found${NC}"
fi

# Create symlinks for both applications
echo -e "${BLUE}3. Creating symbolic links...${NC}"

# For main app
MAIN_APP_DATA_DIR="$(dirname "$MAIN_APP_DB_PATH")"
mkdir -p "$MAIN_APP_DATA_DIR"
if [ -L "$MAIN_APP_DB_PATH" ] || [ -d "$MAIN_APP_DB_PATH" ]; then
    rm -rf "$MAIN_APP_DB_PATH"
fi
ln -s "$SHARED_DB_PATH" "$MAIN_APP_DB_PATH"
echo "✅ Created symlink: $MAIN_APP_DB_PATH -> $SHARED_DB_PATH"

# For crawler app (backup existing and create symlink)
if [ -d "$CRAWLER_DB_PATH" ] && [ ! -L "$CRAWLER_DB_PATH" ]; then
    mv "$CRAWLER_DB_PATH" "${CRAWLER_DB_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ Backed up existing crawler database"
fi
if [ -L "$CRAWLER_DB_PATH" ]; then
    rm "$CRAWLER_DB_PATH"
fi
CRAWLER_DATA_DIR="$(dirname "$CRAWLER_DB_PATH")"
mkdir -p "$CRAWLER_DATA_DIR"
ln -s "$SHARED_DB_PATH" "$CRAWLER_DB_PATH"
echo "✅ Created symlink: $CRAWLER_DB_PATH -> $SHARED_DB_PATH"

# Set permissions
echo -e "${BLUE}4. Setting permissions...${NC}"
chmod -R 755 "$SHARED_DB_PATH"
echo "✅ Set permissions on shared database"

# Verify setup
echo -e "${BLUE}5. Verifying setup...${NC}"
if [ -L "$MAIN_APP_DB_PATH" ] && [ -L "$CRAWLER_DB_PATH" ]; then
    echo "✅ Both applications now point to shared database"
    echo "   Shared DB: $SHARED_DB_PATH"
    echo "   Main App: $MAIN_APP_DB_PATH -> $(readlink $MAIN_APP_DB_PATH)"
    echo "   Crawler:  $CRAWLER_DB_PATH -> $(readlink $CRAWLER_DB_PATH)"
else
    echo -e "${RED}❌ Setup verification failed${NC}"
    exit 1
fi

# Check if database has data
if [ -f "$SHARED_DB_PATH/meta.json" ]; then
    echo -e "${GREEN}✅ Database contains data and is ready to use${NC}"
else
    echo -e "${YELLOW}⚠️  Database is empty - will be created when first used${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Shared database setup complete!${NC}"
echo ""
echo "Both applications will now use the same Qdrant database at:"
echo "  $SHARED_DB_PATH"
echo ""
echo "Next steps:"
echo "1. Restart both applications"
echo "2. Test that data is visible in both apps"
echo "3. Use Docker setup for containerized deployment"
