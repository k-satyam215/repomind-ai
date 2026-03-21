FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# copy project
COPY . .

# upgrade pip
RUN pip install --upgrade pip

# install deps
RUN pip install --no-cache-dir -r requirements.txt

# expose ports
EXPOSE 8000
EXPOSE 8501

# start both services
CMD ["bash", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port 8000 & streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0"]