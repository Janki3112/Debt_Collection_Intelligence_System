"""
Text chunking with overlapping windows
"""
from typing import List, Dict, Any
from app.logger import logger
from app.metrics import CHUNK_COUNT

# Configuration
CHUNK_SIZE = 1500  # characters
OVERLAP = 300      # characters

async def chunk_and_store(document_id: str, pages: List[dict]) -> List[Dict[str, Any]]:
    """
    Create overlapping chunks from document pages
    
    Args:
        document_id: Document UUID
        pages: List of page dicts with page_no and text
        
    Returns:
        List of chunk dicts with metadata
    """
    from app.db.crud import create_chunks
    
    chunks_data = []
    
    for page in pages:
        text = page.get("text", "") or ""
        page_no = page["page_no"]
        
        if not text.strip():
            continue
        
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + CHUNK_SIZE, text_len)
            chunk_text = text[start:end]
            
            # Skip empty or very short chunks
            if len(chunk_text.strip()) < 50:
                break
            
            chunk = {
                "document_id": document_id,
                "page_no": page_no,
                "char_start": start,
                "char_end": end,
                "text": chunk_text
            }
            
            chunks_data.append(chunk)
            
            # Break if we've reached the end
            if end == text_len:
                break
            
            # Move start position with overlap
            start = end - OVERLAP
    
    # Batch insert chunks
    if chunks_data:
        chunk_ids = await create_chunks(chunks_data)
        
        # Add IDs to chunks
        for i, chunk_id in enumerate(chunk_ids):
            chunks_data[i]["chunk_id"] = chunk_id
        
        # Update metrics
        CHUNK_COUNT.inc(len(chunks_data))
        
        logger.info(
            f"Created {len(chunks_data)} chunks for document {document_id}"
        )
    
    return chunks_data