from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import get_settings


@dataclass
class TokenCache:
    access_token: str | None = None
    expires_at: datetime | None = None


class ShopifyAuthService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._cache = TokenCache(access_token=None, expires_at=None)

    async def get_access_token(self, force_refresh: bool = False) -> str:
        if not force_refresh and self._cache.access_token and self._cache.expires_at:
            if datetime.now(timezone.utc) < (self._cache.expires_at - timedelta(minutes=5)):
                return self._cache.access_token

        endpoint = f'https://{self.settings.SHOPIFY_SHOP}/admin/oauth/access_token'
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.settings.SHOPIFY_CLIENT_ID,
            'client_secret': self.settings.SHOPIFY_CLIENT_SECRET,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                endpoint,
                data=data,
                headers={'Accept': 'application/json'},
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()

        token = payload['access_token']
        expires_in = int(payload.get('expires_in', 86399))
        self._cache.access_token = token
        self._cache.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        return token


shopify_auth_service = ShopifyAuthService()
