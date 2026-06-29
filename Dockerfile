FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    software-properties-common \
    gnupg2 \
    curl \
    ca-certificates

RUN add-apt-repository -y ppa:gift/stable

RUN apt-get update && apt-get install -y \
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
    redis-tools

RUN ln -sf /usr/bin/python3.11 /usr/bin/python
RUN ln -sf /usr/bin/python3.11 /usr/bin/python3
RUN ln -sf /usr/bin/pip3 /usr/bin/pip

# Django project root
WORKDIR /app

# Copy backend project
COPY backend/ .

RUN pip install --upgrade pip setuptools wheel

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["sh","-c","gunicorn backend.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
