from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.services.shopify_auth import shopify_auth_service


class ShopifyAdminService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        token = await shopify_auth_service.get_access_token()
        url = f'https://{self.settings.SHOPIFY_SHOP}/admin/api/{self.settings.SHOPIFY_API_VERSION}/graphql.json'
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json={'query': query, 'variables': variables or {}},
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Shopify-Access-Token': token,
                },
            )
            response.raise_for_status()
            payload = response.json()
        if payload.get('errors'):
            raise RuntimeError(f"Shopify GraphQL errors: {payload['errors']}")
        return payload['data']

    async def register_orders_paid_webhook(self, callback_url: str) -> dict[str, Any]:
        mutation = '''
        mutation RegisterWebhook($topic: WebhookSubscriptionTopic!, $callbackUrl: URL!) {
          webhookSubscriptionCreate(
            topic: $topic
            webhookSubscription: {
              callbackUrl: $callbackUrl
              format: JSON
            }
          ) {
            userErrors {
              field
              message
            }
            webhookSubscription {
              id
              topic
              endpoint {
                __typename
                ... on WebhookHttpEndpoint {
                  callbackUrl
                }
              }
            }
          }
        }
        '''
        data = await self.graphql(
            mutation,
            {
                'topic': self.settings.SHOPIFY_WEBHOOK_TOPIC,
                'callbackUrl': callback_url,
            },
        )
        result = data['webhookSubscriptionCreate']
        if result['userErrors']:
            raise RuntimeError(f"Webhook registration failed: {result['userErrors']}")
        return result['webhookSubscription']

    async def list_webhooks(self) -> list[dict[str, Any]]:
        query = '''
        query ExistingWebhooks {
          webhookSubscriptions(first: 50) {
            edges {
              node {
                id
                topic
                endpoint {
                  __typename
                  ... on WebhookHttpEndpoint {
                    callbackUrl
                  }
                }
              }
            }
          }
        }
        '''
        data = await self.graphql(query)
        return [edge['node'] for edge in data['webhookSubscriptions']['edges']]


shopify_admin_service = ShopifyAdminService()
