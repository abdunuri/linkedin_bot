FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    wget \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright
RUN pip install playwright && \
    playwright install chromium && \
    playwright install-deps

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

# Environment variables
ENV TOGETHER_API_KEY=${TOGETHER_API_KEY}
ENV HEADLESS=true
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]