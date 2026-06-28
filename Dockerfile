# AIDFIRS Platform Backend - Production Dockerfile

FROM ubuntu:22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Ensure Python output is logged properly
ENV PYTHONUNBUFFERED=1

# Install core system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    gnupg2 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Add GIFT PPA for Plaso (forensic timeline tools)
RUN add-apt-repository -y ppa:gift/stable

# Install Python + forensic dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3-pip \
    python3-setuptools \
    build-essential \
    sleuthkit \
    testdisk \
    libimage-exiftool-perl \
    plaso-tools \
    ffmpeg \
    libmagic1 \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Make python default point to python3.11
RUN ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Set working directory
WORKDIR /app

# Upgrade pip (important for Render builds)
RUN pip install --upgrade pip setuptools wheel

# Copy requirements first (for caching)
COPY backend/requirements.txt /app/requirements.txt

# Install dependencies (FIXED)
RUN pip install --no-cache-dir -r requirements.txt

# Copy full backend code
COPY backend/ /app/backend/

# Expose port
EXPOSE 8000

# Start server (Render compatible)
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} backend.wsgi:application"]
