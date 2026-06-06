from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.api.routes import router as api_router
from app.database.database import init_db

app = FastAPI(
    title="Paytm AI Hackathon API",
    version="0.1.0",
)


@app.on_event("startup")
async def on_startup():
    await init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_permissions_policy(request: Request, call_next):
    response = await call_next(request)
    response.headers["Permissions-Policy"] = "camera=(*), microphone=(*)"
    return response

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Serve the built React client
CLIENT_DIST = Path(__file__).resolve().parent.parent.parent / "client" / "dist"

if CLIENT_DIST.exists():
    app.mount("/assets", StaticFiles(directory=CLIENT_DIST / "assets"), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(CLIENT_DIST / "index.html")

    @app.exception_handler(404)
    async def spa_fallback(request: Request, exc: StarletteHTTPException):
        # Don't serve SPA for API routes — let them return proper JSON errors
        if request.url.path.startswith("/api"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Not found"}, status_code=404)
        return FileResponse(CLIENT_DIST / "index.html")
