from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from app.config import get_settings
from app.services.pipeline import pipeline_service
from app.utils.hmac_verify import verify_shopify_hmac

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/webhooks/shopify', tags=['shopify-webhooks'])
settings = get_settings()


async def _process_order_in_background(order: dict[str, Any]) -> None:
    try:
        result = await pipeline_service.process_paid_order(order)
        logger.info('Order %s processed: %s', order.get('id'), result)
    except Exception:
        logger.exception('Failed processing Shopify paid order %s', order.get('id'))


@router.post('/orders-paid')
async def orders_paid_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_shopify_hmac_sha256: str | None = Header(default=None),
    x_shopify_topic: str | None = Header(default=None),
    x_shopify_shop_domain: str | None = Header(default=None),
) -> dict[str, str]:
    raw_body = await request.body()
    if not verify_shopify_hmac(raw_body, x_shopify_hmac_sha256, settings.SHOPIFY_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail='Invalid Shopify webhook HMAC')

    if x_shopify_shop_domain and x_shopify_shop_domain != settings.SHOPIFY_SHOP:
        raise HTTPException(status_code=400, detail='Unexpected shop domain')

    try:
        order_payload = json.loads(raw_body.decode('utf-8'))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f'Invalid JSON payload: {exc}') from exc

    logger.info(
        'Accepted Shopify webhook topic=%s shop=%s order_id=%s',
        x_shopify_topic,
        x_shopify_shop_domain,
        order_payload.get('id'),
    )
    background_tasks.add_task(_process_order_in_background, order_payload)
    return {'status': 'accepted'}
