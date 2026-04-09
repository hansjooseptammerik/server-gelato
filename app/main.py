from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.api.webhooks import router as webhooks_router
from app.config import get_settings
from app.services.storage import storage_service

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

app = FastAPI(title='Server-Gelato', version='1.0.0')
app.include_router(webhooks_router)


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/public/print-files/{filename}')
async def public_print_file(filename: str) -> FileResponse:
    path = Path(storage_service.base_dir) / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail='File not found')
    return FileResponse(path=path, media_type='application/pdf', filename=filename)
