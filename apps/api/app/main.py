from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

import os

from app.api.routes import router
from app.db.session import Base, engine
from app.ui import get_ui_html
from app.workers.render_worker import start_embedded_worker, stop_embedded_worker

app = FastAPI(title="Image-to-Cinematic-Video API", version="0.1.0")
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
    Base.metadata.create_all(engine)
    if os.getenv("ENABLE_EMBEDDED_WORKER", "true").lower() in ("true", "1", "yes"):
        start_embedded_worker()


@app.on_event("shutdown")
def shutdown():
    stop_embedded_worker()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
