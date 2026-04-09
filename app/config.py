from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore',
    )

    APP_ENV: str = 'production'
    PUBLIC_BASE_URL: str
    STORAGE_DIR: Path = Path('/var/data/book-pdfs')
    LOG_LEVEL: str = 'INFO'

    SHOPIFY_SHOP: str
    SHOPIFY_CLIENT_ID: str
    SHOPIFY_CLIENT_SECRET: str
    SHOPIFY_WEBHOOK_SECRET: str
    SHOPIFY_API_VERSION: str = '2026-04'
    SHOPIFY_WEBHOOK_TOPIC: str = 'ORDERS_PAID'

    GELATO_API_KEY: str
    GELATO_API_BASE: str = 'https://order.gelatoapis.com'
    GELATO_SHIPMENT_METHOD_UID: str = 'standard'
    GELATO_CURRENCY: str = 'USD'

    ALLOWED_PRODUCT_HANDLES: str = ''
    DRY_RUN: bool = False

    @field_validator('PUBLIC_BASE_URL')
    @classmethod
    def normalize_public_base_url(cls, value: str) -> str:
        return value.rstrip('/')

    @property
    def allowed_product_handles(self) -> List[str]:
        if not self.ALLOWED_PRODUCT_HANDLES.strip():
            return []
        return [x.strip() for x in self.ALLOWED_PRODUCT_HANDLES.split(',') if x.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return settings
