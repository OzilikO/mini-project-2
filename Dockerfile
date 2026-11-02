# Official Python 3.10 slim base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install required system dependencies for Azure Cognitiveservices Speech on Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libasound2 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt-get/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose port 5000
EXPOSE 5000

# Start Flask application
CMD ["python", "app.py"]
