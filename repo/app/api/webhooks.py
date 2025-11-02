"""
Webhook management endpoints
"""
import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.logger import logger

router = APIRouter()

# In-memory webhook registry (use database in production)
_webhook_registry: List[Dict[str, Any]] = []
_event_log: List[Dict[str, Any]] = []


class WebhookRegister(BaseModel):
    """Register a webhook URL"""
    url: HttpUrl = Field(..., description="Webhook URL to receive events")
    events: List[str] = Field(
        default=["*"],
        description="Event types to subscribe to (e.g., 'ingest.completed', 'extract.completed')"
    )
    description: Optional[str] = Field(None, description="Description of this webhook")


class WebhookEvent(BaseModel):
    """Incoming webhook event (for testing)"""
    event_type: str = Field(..., description="Type of event")
    document_id: Optional[str] = Field(None, description="Related document ID")
    status: str = Field(..., description="Event status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


def get_webhooks_for_event(event_type: str) -> List[Dict[str, Any]]:
    """
    Get all webhooks registered for a specific event type
    
    Args:
        event_type: Event type to filter by (e.g., 'ingest.completed')
        
    Returns:
        List of webhook configurations that match the event type
    """
    matching_webhooks = []
    
    for webhook in _webhook_registry:
        # Skip disabled webhooks
        if not webhook.get("enabled", True):
            continue
        
        # Check if webhook subscribes to this event
        events = webhook.get("events", [])
        
        # Match if subscribed to all events ("*") or specific event
        if "*" in events or event_type in events:
            matching_webhooks.append(webhook)
    
    return matching_webhooks


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_webhook(webhook: WebhookRegister):
    """
    Register a webhook URL to receive events
    
    Example events:
    - ingest.completed
    - extract.completed
    - audit.completed
    - ask.completed
    """
    webhook_id = str(uuid.uuid4())
    
    webhook_data = {
        "id": webhook_id,
        "url": str(webhook.url),
        "events": webhook.events,
        "description": webhook.description,
        "created_at": datetime.utcnow().isoformat(),
        "enabled": True
    }
    
    _webhook_registry.append(webhook_data)
    
    logger.info(f"Webhook registered: {webhook_id} -> {webhook.url}")
    
    return {
        "webhook_id": webhook_id,
        "url": webhook.url,
        "events": webhook.events,
        "message": "Webhook registered successfully"
    }


@router.get("/webhooks")
async def list_webhooks():
    """List all registered webhooks"""
    return {
        "webhooks": _webhook_registry,
        "count": len(_webhook_registry)
    }


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete a webhook"""
    global _webhook_registry
    
    original_count = len(_webhook_registry)
    _webhook_registry = [w for w in _webhook_registry if w["id"] != webhook_id]
    
    if len(_webhook_registry) == original_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )
    
    logger.info(f"Webhook deleted: {webhook_id}")
    
    return {"message": "Webhook deleted successfully"}


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook_event(event: WebhookEvent):
    """
    Receive and log webhook events (for testing)
    
    This endpoint simulates receiving events from external services
    """
    event_id = str(uuid.uuid4())
    
    event_data = {
        "id": event_id,
        "type": event.event_type,
        "document_id": event.document_id,
        "status": event.status,
        "metadata": event.metadata,
        "received_at": datetime.utcnow().isoformat()
    }
    
    _event_log.append(event_data)
    
    logger.info(
        f"Webhook event received: {event.event_type} "
        f"(doc: {event.document_id}, status: {event.status})"
    )
    
    return {
        "event_id": event_id,
        "status": "received",
        "timestamp": event_data["received_at"],
        "message": f"Event '{event.event_type}' logged successfully"
    }


@router.get("/events")
async def list_events(limit: int = 50):
    """List recent webhook events"""
    return {
        "events": _event_log[-limit:],
        "count": len(_event_log)
    }


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """Get details of a specific event"""
    for event in _event_log:
        if event["id"] == event_id:
            return event
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Event not found"
    )