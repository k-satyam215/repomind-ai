from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.core.logger import get_logger

logger = get_logger("RepoMind.API")

app = FastAPI(
    title="RepoMind AI",
    description="Autonomous Software Engineering Agent API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(router)


@app.get("/")
def root():
    return {"message": "RepoMind AI is running", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}
