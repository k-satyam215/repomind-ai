from fastapi import FastAPI
from src.api.routes import router

app = FastAPI(
    title="RepoMind AI",
    version="1.0"
)

app.include_router(router)

@app.get("/")
def root():
    return {"message": "RepoMind AI running"}