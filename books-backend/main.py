from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import auth, books, imports, lists, reading

app = FastAPI(title=settings.app_name, debug=settings.debug)


@app.middleware("http")
async def add_cover_cache_headers(request: Request, call_next):
    """Add long-lived cache headers for immutable cover uploads."""
    response = await call_next(request)
    covers_prefix = f"{settings.uploads_url_prefix}/covers/"
    if request.url.path.startswith(covers_prefix) and response.status_code == 200:
        response.headers.setdefault(
            "Cache-Control", "public, max-age=31536000, immutable"
        )
    return response


app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings.uploads_dir_path.mkdir(parents=True, exist_ok=True)
app.mount(
    settings.uploads_url_prefix,
    StaticFiles(directory=settings.uploads_dir_path),
    name="uploads",
)


@app.get("/")
async def root():
    return {"message": "Welcome to the Books API!"}


app.include_router(auth.router)
app.include_router(lists.router)
app.include_router(books.router)
app.include_router(reading.router)
app.include_router(imports.router)
