FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (excluding files in .dockerignore)
COPY . .

# Make entrypoint executable
RUN chmod +x docker-entrypoint.sh

# Use entrypoint script
ENTRYPOINT ["./docker-entrypoint.sh"]

