from secrets import compare_digest

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.routes import router
from app.core.config import settings
from app.db.session import Base, engine, ensure_sqlite_schema
from app.ui import get_ui_html

app = FastAPI(title="Image-to-Cinematic-Video API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Idempotency-Key"],
)


@app.middleware("http")
async def production_api_lockdown(request: Request, call_next):
    """Stop anonymous public access until project-level authorization is implemented.

    Temporary single-instance access token; NOT a multi-tenant auth system.
    Health check remains accessible for orchestration.
    """
    if settings.app_env.lower() != "production" or request.url.path == "/api/v1/health":
        return await call_next(request)
    if not settings.api_access_token:
        return JSONResponse({"detail": "Production API token not configured"}, status_code=503)
    auth_header = request.headers.get("authorization") or ""
    if not auth_header.startswith("Bearer ") or not compare_digest(
        auth_header[len("Bearer "):], settings.api_access_token
    ):
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    return await call_next(request)


app.include_router(router)


@app.get("/", response_class=HTMLResponse)
@app.get("/ui", response_class=HTMLResponse)
def serve_ui():
    return get_ui_html()


@app.on_event("startup")
def startup():
    if settings.app_env.lower() == "production" and not settings.api_access_token:
        raise RuntimeError("Production mode requires API_ACCESS_TOKEN until tenant auth is implemented.")
    ensure_sqlite_schema(engine)
