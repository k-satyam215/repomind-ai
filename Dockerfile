FROM python:3.11-slim

# Prevent python buffering
ENV PYTHONUNBUFFERED=1

# Set working dir
WORKDIR /app

# Install system deps (git needed for GitPython)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . .

# Python path fix
ENV PYTHONPATH=/app

# Upgrade pip
RUN pip install --upgrade pip

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Make startup script executable
RUN chmod +x start.sh

# Expose ports
EXPOSE 8000
EXPOSE 8501

# Start services
CMD ["sh", "start.sh"]