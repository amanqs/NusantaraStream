# Dockerfile untuk Nusantara Stream Telegram Music Bot
FROM python:3.11-slim

# Pasang FFmpeg, build-essential, git, dan pustaka pendukung
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Atur working directory
WORKDIR /app

# Salin requirements dan pasang pustaka
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh kode aplikasi
COPY . .

# Buat direktori temporary dan cache
RUN mkdir -p downloads cache

# Jalankan bot
CMD ["python", "main.py"]
