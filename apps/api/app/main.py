from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.routes import router
from app.db.session import Base, engine, ensure_sqlite_schema
from app.ui import get_ui_html

app = FastAPI(title="Image-to-Cinematic-Video API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/", response_class=HTMLResponse)
@app.get("/ui", response_class=HTMLResponse)
def serve_ui():
    return get_ui_html()


@app.on_event("startup")
def startup():
    ensure_sqlite_schema(engine)

