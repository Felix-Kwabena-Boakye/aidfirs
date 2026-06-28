# AIDFIRS Platform Backend - Dockerfile
FROM ubuntu:22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install core packages and repository utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    gnupg2 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Add GIFT PPA for Plaso
RUN add-apt-repository -y ppa:gift/stable

# Install forensic tools, Python 3.11, and build dependencies
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

# Configure python/pip symlinks
RUN ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

WORKDIR /app

# Install Python requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copy backend source
COPY backend/ /app/backend/

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "backend.wsgi:application"]    
