from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.v1 import api_router
from .core.config import get_settings
from .core.errors import DomainError
from .repositories import prisma as prisma_repo
from pathlib import Path


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await prisma_repo.connect()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    try:
        yield
    finally:
        await prisma_repo.disconnect()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="会员制购物网站课程设计 API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.code, content={"detail": exc.message})


@app.middleware("http")
async def request_context(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


app.include_router(api_router, prefix=settings.api_prefix)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir, check_dir=False), name="uploads")


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
