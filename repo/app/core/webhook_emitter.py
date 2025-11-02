"""
Webhook emission with HMAC signing and retry logic
"""
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.logger import logger
from app.metrics import WEBHOOK_CALLS


def maybe_emit_webhook(webhook_url: str, payload: Dict[str, Any], secret: Optional[str] = None):
    """
    Send webhook notification (legacy function for backward compatibility)
    
    Args:
        webhook_url: Target URL
        payload: JSON payload
        secret: Optional HMAC secret
    """
    try:
        _send_webhook(webhook_url, payload, secret)
    except Exception as e:
        logger.error(f"Webhook emission failed: {str(e)}")


def emit_event(event_type: str, payload: Dict[str, Any]):
    """
    Emit event to all registered webhooks
    
    Args:
        event_type: Event type (e.g., "ingest.completed")
        payload: Event payload
    """
    from app.api.webhooks import get_webhooks_for_event
    
    webhooks = get_webhooks_for_event(event_type)
    
    if not webhooks:
        logger.debug(f"No webhooks registered for event: {event_type}")
        return
    
    logger.info(f"Emitting event {event_type} to {len(webhooks)} webhooks")
    
    for webhook in webhooks:
        try:
            _send_webhook(
                webhook["url"],
                {"event": event_type, **payload},
                webhook.get("secret")
            )
        except Exception as e:
            logger.error(f"Failed to send webhook to {webhook['url']}: {str(e)}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def _send_webhook(url: str, payload: Dict[str, Any], secret: Optional[str] = None):
    """
    Send webhook with retry logic
    
    Args:
        url: Target URL
        payload: JSON payload
        secret: Optional HMAC secret for signing
    """
    try:
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ContractIntelligence/1.0"
        }
        
        # Sign payload if secret provided
        if secret:
            signature = _sign_payload(payload, secret)
            headers["X-Webhook-Signature"] = signature
        
        # Send request
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                url,
                json=payload,
                headers=headers
            )
            
            response.raise_for_status()
            
            WEBHOOK_CALLS.labels(status="success").inc()
            logger.info(f"Webhook sent successfully to {url}")
            
    except httpx.HTTPError as e:
        WEBHOOK_CALLS.labels(status="failure").inc()
        logger.error(f"Webhook HTTP error for {url}: {str(e)}")
        raise
    except Exception as e:
        WEBHOOK_CALLS.labels(status="failure").inc()
        logger.error(f"Webhook error for {url}: {str(e)}")
        raise


def _sign_payload(payload: Dict[str, Any], secret: str) -> str:
    """
    Create HMAC signature for webhook payload
    
    Args:
        payload: JSON payload
        secret: HMAC secret
        
    Returns:
        Hex-encoded HMAC signature
    """
    payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    return f"sha256={signature}"


def verify_webhook_signature(
    payload: Dict[str, Any],
    signature: str,
    secret: str
) -> bool:
    """
    Verify webhook signature
    
    Args:
        payload: JSON payload
        signature: Received signature
        secret: HMAC secret
        
    Returns:
        True if signature is valid
    """
    expected_signature = _sign_payload(payload, secret)
    return hmac.compare_digest(signature, expected_signature)