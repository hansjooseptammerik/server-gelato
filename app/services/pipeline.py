from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.services.gelato import gelato_service
from app.services.pdf_builder import pdf_builder_service
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

BOOKS_INDEX_PATH = Path(__file__).resolve().parent.parent / 'book_configs' / 'books.json'
BOOK_CONFIGS_DIR = Path(__file__).resolve().parent.parent / 'book_configs'


class PipelineService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _load_books_index(self) -> dict[str, Any]:
        with open(BOOKS_INDEX_PATH, 'r', encoding='utf-8') as fh:
            return json.load(fh)

    def _find_child_name(self, line_item: dict[str, Any]) -> str | None:
        props = line_item.get('properties') or []
        for prop in props:
            key = (prop.get('name') or '').strip().lower()
            value = (prop.get('value') or '').strip()
            if not value:
                continue
            if key in {'child name', "child's name", 'name', 'personalized_name'}:
                return value
        return None

    def _find_book_handle(self, line_item: dict[str, Any]) -> str | None:
        props = line_item.get('properties') or []
        for prop in props:
            key = (prop.get('name') or '').strip().lower()
            value = (prop.get('value') or '').strip()
            if not value:
                continue

            if key in {'_personalizer_book', 'personalizer_book', 'book_handle', 'handle'}:
                if value.endswith('-1'):
                    value = value[:-2]
                return value

        fallback = (line_item.get('handle') or '').strip()
        if fallback:
            return fallback

        return None

    def _build_shipping_address(self, order: dict[str, Any]) -> dict[str, Any]:
        shipping = order.get('shipping_address') or {}
        first_name = shipping.get('first_name') or order.get('customer', {}).get('first_name') or ''
        last_name = shipping.get('last_name') or order.get('customer', {}).get('last_name') or ''
        email = order.get('email') or order.get('contact_email') or ''
        return {
            'companyName': shipping.get('company') or '',
            'firstName': first_name,
            'lastName': last_name,
            'addressLine1': shipping.get('address1') or '',
            'addressLine2': shipping.get('address2') or '',
            'city': shipping.get('city') or '',
            'state': shipping.get('province_code') or shipping.get('province') or '',
            'postCode': shipping.get('zip') or '',
            'country': shipping.get('country_code') or shipping.get('country') or '',
            'email': email,
            'phone': shipping.get('phone') or order.get('phone') or '',
        }

    async def process_paid_order(self, order: dict[str, Any]) -> dict[str, Any]:
        books_index = self._load_books_index()
        items_payload: list[dict[str, Any]] = []

        for line_item in order.get('line_items', []):
            handle = self._find_book_handle(line_item) or ''

            if self.settings.allowed_product_handles and handle not in self.settings.allowed_product_handles:
                logger.info('Skipping line item with disallowed handle: %s', handle)
                continue

            book_meta = books_index.get(handle)
            if not book_meta:
                logger.info('Skipping line item with unknown handle: %s', handle)
                continue

            child_name = self._find_child_name(line_item)
            if not child_name:
                logger.info('Skipping line item without child name: %s', line_item.get('id'))
                continue

            config_path = BOOK_CONFIGS_DIR / book_meta['config_file']
            with open(config_path, 'r', encoding='utf-8') as fh:
                book_config = json.load(fh)

            page_count = len(book_config.get('pages') or [])
            if page_count <= 0:
                logger.info('Skipping line item with empty page config: %s', line_item.get('id'))
                continue

            pdf_path = storage_service.next_pdf_path(prefix=f"order-{order.get('id')}-item-{line_item.get('id')}")
            await pdf_builder_service.build_book_pdf(
                child_name=child_name,
                config_path=config_path,
                output_path=pdf_path,
            )

            pdf_url = storage_service.public_url_for(pdf_path)

            item_payload = {
                'itemReferenceId': str(line_item.get('id')),
                'productUid': book_meta['gelato_product_uid'],
                'files': [
                    {
                        'type': 'default',
                        'url': pdf_url,
                    }
                ],
                'pageCount': page_count,
                'quantity': int(line_item.get('quantity', 1)),
            }
            items_payload.append(item_payload)

        if not items_payload:
            logger.info('No printable personalized items found in order %s', order.get('id'))
            return {'skipped': True, 'reason': 'no printable personalized items'}

        gelato_payload = {
            'orderType': 'order',
            'orderReferenceId': str(order.get('id')),
            'customerReferenceId': str(order.get('customer', {}).get('id') or order.get('email') or order.get('id')),
            'currency': order.get('currency') or self.settings.GELATO_CURRENCY,
            'items': items_payload,
            'shipmentMethodUid': self.settings.GELATO_SHIPMENT_METHOD_UID,
            'shippingAddress': self._build_shipping_address(order),
        }

        result = await gelato_service.create_order(gelato_payload)

        return {
            'skipped': False,
            'gelato_request': gelato_payload,
            'gelato_response': result,
        }


pipeline_service = PipelineService()
