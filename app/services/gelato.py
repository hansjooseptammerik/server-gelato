from __future__ import annotations

import logging
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class GelatoService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def create_order(self, payload: dict) -> dict:
        headers = {
            "X-API-KEY": self.settings.GELATO_API_KEY,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.settings.GELATO_API_BASE}/v4/orders",
                json=payload,
                headers=headers,
            )

            if response.is_error:
                logger.error("Gelato order create failed: status=%s", response.status_code)
                logger.error("Gelato request payload: %s", payload)

                try:
                    logger.error("Gelato response JSON: %s", response.json())
                except Exception:
                    logger.error("Gelato response text: %s", response.text)

                response.raise_for_status()

            return response.json()


gelato_service = GelatoService()
