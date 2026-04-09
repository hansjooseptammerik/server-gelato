from __future__ import annotations

import base64
import hashlib
import hmac



def verify_shopify_hmac(raw_body: bytes, received_hmac: str | None, secret: str) -> bool:
    if not received_hmac:
        return False
    digest = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).digest()
    encoded = base64.b64encode(digest).decode('utf-8')
    return hmac.compare_digest(encoded, received_hmac)
