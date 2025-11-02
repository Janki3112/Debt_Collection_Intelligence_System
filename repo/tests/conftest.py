"""
Pytest fixtures for testing
"""
import pytest
import pytest_asyncio
import os
from reportlab.pdfgen import canvas
from io import BytesIO
import tempfile
import asyncio
from httpx import AsyncClient
from app.main import app


# Fix for Windows + Python 3.8 event loop issues
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
    
    if os.path.exists(path):
        os.unlink(path)


@pytest_asyncio.fixture
async def sample_document_id(sample_pdf_path):
    """Ingest a sample document and return its ID"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with open(sample_pdf_path, 'rb') as f:
            response = await client.post(
                "/ingest",
                files=[("files", ("test.pdf", f, "application/pdf"))]
            )
        
        assert response.status_code == 201
        data = response.json()
        return data["document_ids"][0]


@pytest_asyncio.fixture
async def async_client():
    """Provide an async HTTP client for testing"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client