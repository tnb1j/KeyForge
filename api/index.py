"""Vercel Serverless Function Entry Point for KeyForge FastAPI Application."""

import os
import sys
from pathlib import Path

# Add project root directory to sys.path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Handle Vercel serverless read-only filesystem (fallback to /tmp/keyforge.db if no external DB provided)
if ("VERCEL" in os.environ or "AWS_LAMBDA_FUNCTION_NAME" in os.environ) and "KEYFORGE_DB_URL" not in os.environ:
    os.environ["KEYFORGE_DB_URL"] = "sqlite:////tmp/keyforge.db"

from keyforge.server.app import app
from keyforge.server.db.database import init_db

# Initialize database schema and seeds on serverless cold start
try:
    init_db()
except Exception as e:
    print(f"Warning: init_db failed on startup: {e}")

# Vercel ASGI handler expects 'app'
__all__ = ["app"]
