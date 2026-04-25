import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import ingest, analysis, recommendations, illumio, settings as settings_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Mosaic — initializing database")
    await init_db()
    logger.info("Database ready")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Mosaic — Infoblox DNS Policy Accelerator for Illumio",
    description="Convert DNS history into Illumio microsegmentation policy in minutes, not months.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(analysis.router)
app.include_router(recommendations.router)
app.include_router(illumio.router)
app.include_router(settings_router.router)
app.include_router(settings_router._subnet_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mosaic-backend"}


@app.get("/")
async def root():
    return {
        "service": "Mosaic",
        "description": "Infoblox DNS Policy Accelerator for Illumio",
        "docs": "/docs",
    }
