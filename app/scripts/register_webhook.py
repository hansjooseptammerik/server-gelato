from __future__ import annotations

import asyncio

from app.config import get_settings
from app.services.shopify_admin import shopify_admin_service


async def main() -> None:
    settings = get_settings()
    callback_url = f"{settings.PUBLIC_BASE_URL}/webhooks/shopify/orders-paid"
    webhook = await shopify_admin_service.register_orders_paid_webhook(callback_url)
    print('Webhook registered successfully:')
    print(webhook)


if __name__ == '__main__':
    asyncio.run(main())
