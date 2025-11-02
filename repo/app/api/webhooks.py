"""
Webhook management endpoints
"""
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.logger import logger

router = APIRouter()

# In-memory webhook registry (in production, use database)
webhook_registry: Dict[str, dict] = {}

class WebhookConfig(BaseModel):
    """Webhook configuration"""
    url: HttpUrl
    events: List[str]  # e.g., ["ingest.completed", "extract.completed"]
    secret: Optional[str] = None
    enabled: bool = True

class WebhookResponse(BaseModel):
    """Webhook registration response"""
    webhook_id: str
    url: str
    events: List[str]
    enabled: bool
    created_at: str

@router.post("/register", response_model=WebhookResponse)
async def register_webhook(config: WebhookConfig):
    """
    Register a new webhook endpoint
    
    Events available:
    - ingest.completed
    - ingest.failed
    - extract.completed
    - ask.completed
    - audit.completed
    """
    webhook_id = str(uuid.uuid4())
    
    webhook_data = {
        "webhook_id": webhook_id,
        "url": str(config.url),
        "events": config.events,
        "secret": config.secret,
        "enabled": config.enabled,
        "created_at": datetime.utcnow().isoformat()
    }
    
    webhook_registry[webhook_id] = webhook_data
    
    logger.info(f"Webhook registered: {webhook_id} for events {config.events}")
    
    return WebhookResponse(**webhook_data)

@router.get("/list", response_model=List[WebhookResponse])
async def list_webhooks():
    """List all registered webhooks"""
    return [
        WebhookResponse(**{k: v for k, v in wh.items() if k != "secret"})
        for wh in webhook_registry.values()
    ]

@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(webhook_id: str):
    """Get webhook details"""
    if webhook_id not in webhook_registry:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    webhook = webhook_registry[webhook_id]
    return WebhookResponse(**{k: v for k, v in webhook.items() if k != "secret"})

@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete a webhook"""
    if webhook_id not in webhook_registry:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    del webhook_registry[webhook_id]
    logger.info(f"Webhook deleted: {webhook_id}")
    
    return {"message": "Webhook deleted successfully"}

@router.put("/{webhook_id}/toggle")
async def toggle_webhook(webhook_id: str, enabled: bool = Body(..., embed=True)):
    """Enable or disable a webhook"""
    if webhook_id not in webhook_registry:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    webhook_registry[webhook_id]["enabled"] = enabled
    logger.info(f"Webhook {webhook_id} {'enabled' if enabled else 'disabled'}")
    
    return {"message": f"Webhook {'enabled' if enabled else 'disabled'}"}

def get_webhooks_for_event(event: str) -> List[dict]:
    """Get all enabled webhooks subscribed to an event"""
    return [
        wh for wh in webhook_registry.values()
        if wh["enabled"] and event in wh["events"]
    ]