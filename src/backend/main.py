import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is available for absolute imports (src.backend.*)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.api.routes import health_router, router  # noqa: E402
from src.backend.config import get_settings  # noqa: E402
from src.backend.observability.tracing import TracingMiddleware  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    from src.backend.observability.langfuse_client import (
        LangfuseTracingConfig,
        configure_langfuse_tracing,
        shutdown_langfuse,
    )

    configure_langfuse_tracing(
        LangfuseTracingConfig(
            enabled=settings.langfuse_enabled,
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            environment=settings.langfuse_environment,
            service_name="alosm-backend",
        )
    )
    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    if settings.app_env != "production":
        try:
            from src.backend.db.base import get_engine
            from src.backend.db.models import Base

            engine = get_engine()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("Database schema verified/initialized.")
        except Exception as exc:
            print(f"Database schema initialization notice: {exc}")
    else:
        print("Production: skipping create_all, use Alembic migrations.")
        if settings.database_url.startswith(("postgres://", "postgresql://", "postgresql+")):
            try:
                from sqlalchemy import text

                from src.backend.db.base import get_engine

                engine = get_engine()
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                print("Database warmup OK.")
            except Exception as exc:
                print(f"Database warmup notice: {exc}")
    try:
        yield
    finally:
        shutdown_langfuse(settings.langfuse_flush_timeout_seconds)
        print("Shutting down...")


app = FastAPI(
    title="AI20K Agent",
    description="AI Agent built with LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(TracingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
app.include_router(health_router)
