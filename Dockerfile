# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY code/ ./code/
COPY test_database_loading.py .

# Create data directory structure
RUN mkdir -p /app/data/json \
    && mkdir -p /app/data/json_with_embeddings \
    && mkdir -p /app/data/urls \
    && mkdir -p /app/data/status \
    && mkdir -p /app/data/docs

# Set environment variables
ENV PYTHONPATH=/app:/app/code
ENV PYTHONUNBUFFERED=1

# Create a non-root user
RUN useradd -m -u 1000 crawler && chown -R crawler:crawler /app
USER crawler

# Expose port for potential web interface
EXPOSE 8000

# Default command
CMD ["python", "code/crawler.py"]
