from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class GelatoService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def create_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.settings.DRY_RUN:
            logger.info('DRY_RUN enabled, skipping Gelato order creation: %s', payload)
            return {'dry_run': True, 'payload': payload}

        url = f"{self.settings.GELATO_API_BASE.rstrip('/')}/v4/orders"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    'X-API-KEY': self.settings.GELATO_API_KEY,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
            )
            response.raise_for_status()
            return response.json()


gelato_service = GelatoService()
