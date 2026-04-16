FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install deps first (layer caching)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create log and memory dirs
RUN mkdir -p logs repomind_memory

EXPOSE 8000
EXPOSE 8501

# Healthcheck for the FastAPI backend
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start both services; use exec form for signal handling
CMD ["bash", "-c", \
    "uvicorn backend.main:app --host 0.0.0.0 --port 8000 & \
     streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0 & \
     wait -n"]
