from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.connection import Base, engine
from backend.api import (
    settings as settings_api,
    runs as runs_api,
    opportunities as opportunities_api,
    clusters as clusters_api,
    evidence as evidence_api,
    ideas as ideas_api,
    exports as exports_api,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run the synchronous create_all in a thread so it doesn't block the
    # uvicorn event loop and cause all incoming requests to hang.
    import asyncio
    await asyncio.to_thread(Base.metadata.create_all, engine)
    yield

app = FastAPI(
    title="Reddit Opportunity Miner API",
    description="Backend API for Reddit Opportunity Miner",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(settings_api.router)
app.include_router(runs_api.router)
app.include_router(opportunities_api.router)
app.include_router(clusters_api.router)
app.include_router(evidence_api.router)
app.include_router(ideas_api.router)
app.include_router(exports_api.router)

@app.get("/")
def read_root():
    return {"status": "ok", "app": "Reddit Opportunity Miner API"}
