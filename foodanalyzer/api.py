"""FastAPI application: ``POST /analyze`` for multipart meal-photo uploads."""

from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()

import re
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from foodanalyzer import __version__
from foodanalyzer.config import get_settings
from foodanalyzer.core.analyzer import analyze_image
from foodanalyzer.errors import FoodAnalyzerError, ValidationError
from foodanalyzer.logging_config import configure_logging, get_logger
from foodanalyzer.services.ai_service import build_nutrition_provider
from foodanalyzer.storage import get_repository
from foodanalyzer.validation import validate_upload

_log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    app.state.settings = settings
    app.state.repository = await get_repository()
    # One shared cache/provider instance so the TTL cache actually accumulates.
    try:
        app.state.nutrition_provider = build_nutrition_provider(settings)
    except Exception as exc:  # provider not configured — analyze will report it
        _log.warning("nutrition provider not ready at startup: %s", exc)
        app.state.nutrition_provider = None
    _log.info("foodanalyzer API %s ready", __version__)
    try:
        yield
    finally:
        await app.state.repository.close()


app = FastAPI(title="AI Food Analyzer", version=__version__, lifespan=lifespan)


@app.exception_handler(FoodAnalyzerError)
async def _domain_error_handler(_: Request, exc: FoodAnalyzerError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"error": {"code": exc.code, "message": str(exc)}},
    )


@app.get("/health")
async def health() -> dict:
    repo = app.state.repository
    return {
        "status": "ok",
        "version": __version__,
        "storage": type(repo).__name__,
        "records": await repo.count(),
    }


@app.get("/history")
async def history(limit: int = 20) -> dict:
    limit = max(1, min(limit, 200))
    records = await app.state.repository.list_recent(limit=limit)
    return {"count": len(records), "items": [r.model_dump(mode="json") for r in records]}


@app.get("/history/{record_id}")
async def history_item(record_id: str) -> dict:
    record = await app.state.repository.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="record not found")
    return record.model_dump(mode="json")


@app.post("/analyze")
async def analyze(image: UploadFile = File(...)) -> JSONResponse:
    settings = app.state.settings
    data = await image.read()

    # Pre-flight validation (type, magic bytes, size) before touching the AI.
    detected = validate_upload(
        data,
        filename=image.filename,
        declared_content_type=image.content_type,
        max_size_bytes=settings.max_image_size_bytes,
    )

    suffix = ".png" if detected == "image/png" else ".jpg"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(image.filename or "meal").stem)[:60] or "meal"
    upload_dir = Path(settings.upload_dir)
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        upload_dir = Path(tempfile.gettempdir())
    tmp_path = upload_dir / f"{uuid.uuid4().hex}_{stem}{suffix}"
    tmp_path.write_bytes(data)

    try:
        result = await analyze_image(
            tmp_path,
            settings=settings,
            nutrition_provider=app.state.nutrition_provider,
            repository=app.state.repository,
            original_filename=image.filename or tmp_path.name,
            validate=False,  # already validated above
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    return JSONResponse(status_code=200, content=result.to_public_dict())


def run() -> None:
    """``foodanalyzer-api`` / ``python -m foodanalyzer.api`` — start uvicorn."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "foodanalyzer.api:app",
        host="0.0.0.0",
        port=settings.http_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
