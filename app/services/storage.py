from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.config import get_settings


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_dir: Path = self.settings.STORAGE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def next_pdf_path(self, prefix: str = 'print') -> Path:
        filename = f'{prefix}-{uuid4().hex}.pdf'
        return self.base_dir / filename

    def public_url_for(self, path: Path) -> str:
        return f'{self.settings.PUBLIC_BASE_URL}/public/print-files/{path.name}'


storage_service = StorageService()
