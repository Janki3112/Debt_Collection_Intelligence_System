"""
Tests for extraction endpoint
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_extract_not_found():
    """Test extraction with non-existent document"""
    response = client.post(
        "/extract",
        json={"document_id": "non-existent-id"}
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_extract_success(sample_document_id):
    """Test successful extraction"""
    response = client.post(
        "/extract",
        json={"document_id": sample_document_id}
    )
    assert response.status_code == 200
    data = response.json()
    assert "parties" in data
    assert "effective_date" in data
    assert "auto_renewal" in data