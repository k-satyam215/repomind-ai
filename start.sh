#!/bin/sh

echo "Starting FastAPI..."
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

sleep 3

echo "Starting Streamlit..."
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0