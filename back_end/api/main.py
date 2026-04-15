import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from ml_library.utils.plugins import load_plugins

load_plugins("ml_library.data")
load_plugins("ml_library.model")
load_plugins("ml_library.utils.nodes.basic")

from back_end.api.routes import (
    workflow_router,
    training_router,
    recommendations_router,
    models_router,
    config_router,
    nodes_router,
)

app = FastAPI(
    title="Product Recommendation API",
    version="1.0.0",
    description="B2B Product Recommendation System with Node-based Workflow Execution"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/")
async def serve_index():
    index_path = Path("static/index.html")
    if index_path.exists():
        return FileResponse("static/index.html")
    return {"message": "Product Recommendation API"}


@app.get("/favicon.ico")
async def serve_favicon():
    favicon_path = Path("static/favicon.ico")
    if favicon_path.exists():
        return FileResponse("static/favicon.ico")
    return {"message": "No favicon"}


app.include_router(nodes_router)
app.include_router(config_router)
app.include_router(training_router)
app.include_router(recommendations_router)
app.include_router(models_router)
app.include_router(workflow_router)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')