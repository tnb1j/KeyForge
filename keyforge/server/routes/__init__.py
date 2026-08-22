"""KeyForge API Route Definitions."""

from keyforge.server.routes.activations import router as activations_router
from keyforge.server.routes.audit_routes import router as audit_router
from keyforge.server.routes.auth_routes import router as auth_router
from keyforge.server.routes.health import router as health_router
from keyforge.server.routes.keys import router as keys_router
from keyforge.server.routes.licenses import router as licenses_router
from keyforge.server.routes.products import router as products_router

__all__ = [
    "health_router",
    "auth_router",
    "products_router",
    "keys_router",
    "licenses_router",
    "activations_router",
    "audit_router",
]
