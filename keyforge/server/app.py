"""FastAPI Application Factory, Middleware Configuration, and Route Mounting."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from keyforge import __version__
from keyforge.server.config import settings
from keyforge.server.db.database import init_db
from keyforge.server.routes import (
    activations_router,
    audit_router,
    auth_router,
    health_router,
    keys_router,
    licenses_router,
    products_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database schema and seed default data
    init_db()
    yield
    # Shutdown logic if needed


app = FastAPI(
    title="KeyForge Universal Licensing Server",
    description="""
# KeyForge: Universal Adaptive Software Key & License Management Framework

A production-grade, universal, configurable licensing and key-management platform
supporting online/offline validation, Ed25519 asymmetric cryptography, dynamic profiles,
and multi-language client SDKs.
    """,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    # Normalize serverless /v1 paths if /api was stripped by gateway
    if request.scope.get("path", "").startswith("/v1/"):
        request.scope["path"] = "/api" + request.scope["path"]
    elif request.scope.get("path", "").startswith("/auth/"):
        request.scope["path"] = "/api/v1" + request.scope["path"]

    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Mount API Routes
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(keys_router)
app.include_router(licenses_router)
app.include_router(activations_router)
app.include_router(audit_router)

# Mount Dashboard static directory if present
dashboard_dir = Path(__file__).parent.parent / "dashboard"
if dashboard_dir.exists():
    app.mount("/dashboard/static", StaticFiles(directory=str(dashboard_dir)), name="dashboard_static")

    @app.get("/dashboard", include_in_schema=False)
    async def serve_dashboard():
        index_file = dashboard_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Admin Dashboard files are being generated"}


@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/docs")
