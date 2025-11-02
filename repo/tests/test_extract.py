"""
Tests for extraction endpoint
"""
import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_extract_not_found(async_client):
    """Test extraction with non-existent document"""
    response = await async_client.post(
        "/extract",
        json={"document_id": "non-existent-id"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_extract_success(async_client, sample_document_id):
    """Test successful extraction"""
    response = await async_client.post(
        "/extract",
        json={"document_id": sample_document_id}
    )
    assert response.status_code == 200
    data = response.json()
    assert "parties" in data
    assert "effective_date" in data
    assert "auto_renewal" in data