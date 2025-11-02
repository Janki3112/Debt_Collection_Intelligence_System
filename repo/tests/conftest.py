"""
Pytest fixtures for testing
"""
import pytest
import os
from reportlab.pdfgen import canvas
from io import BytesIO
import tempfile

@pytest.fixture
def sample_pdf_path():
    """Create a sample PDF for testing"""
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
        packet = BytesIO()
        can = canvas.Canvas(packet)
        can.drawString(100, 750, "MASTER SERVICE AGREEMENT")
        can.drawString(100, 700, "This agreement is between Alpha Inc and Beta LLC.")
        can.drawString(100, 650, "Effective Date: January 1, 2024")
        can.drawString(100, 600, "The contract will auto-renew unless either party gives 15 day notice.")
        can.drawString(100, 550, "Liability is unlimited for all claims.")
        can.drawString(100, 500, "Each party shall indemnify and hold harmless the other.")
        can.save()
        packet.seek(0)
        f.write(packet.getvalue())
        path = f.name
    
    yield path
    
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)

@pytest.fixture
async def sample_document_id(sample_pdf_path):
    """Ingest a sample document and return its ID"""
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    
    with open(sample_pdf_path, 'rb') as f:
        response = client.post(
            "/ingest",
            files=[("files", ("test.pdf", f, "application/pdf"))]
        )
    
    assert response.status_code == 201
    data = response.json()
    return data["document_ids"][0]