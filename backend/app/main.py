from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.videos import router as videos_router
from app.core.db import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ClipCut Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (HTML frontend)
frontend_dir = Path(__file__).parent.parent.parent / "index.html"
if frontend_dir.exists():
    # Create a simple route for the frontend
    from fastapi.responses import FileResponse
    @app.get("/")
    async def root():
        return FileResponse(frontend_dir)

app.include_router(videos_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
