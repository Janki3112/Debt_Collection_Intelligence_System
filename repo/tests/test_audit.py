"""
Tests for audit endpoint
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_audit_finds_issues(sample_document_id):
    """Test audit finds risky clauses"""
    response = client.post(
        "/audit",
        json={
            "document_id": sample_document_id,
            "use_llm_fallback": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "findings" in data
    assert "risk_score" in data
    assert isinstance(data["findings"], list)