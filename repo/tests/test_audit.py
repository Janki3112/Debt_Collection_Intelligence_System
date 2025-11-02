"""
Tests for audit endpoint
"""
import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_audit_finds_issues(async_client, sample_document_id):
    """Test audit finds risky clauses"""
    response = await async_client.post(
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