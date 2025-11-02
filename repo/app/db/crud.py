"""
Async CRUD operations for database
"""
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.db.models import Document, Page, Chunk
from app.db.session import async_session_factory
from app.logger import logger


async def create_document_with_pages(
    document_id: str,
    filename: str,
    file_path: str,
    pages: List[Dict]
):
    """
    Create document and its pages in database
    
    Args:
        document_id: Document UUID
        filename: Original filename
        file_path: Path to stored file
        pages: List of page dicts with page_no and text
    """
    async with async_session_factory() as session:
        try:
            # Create document
            doc = Document(
                id=document_id,
                filename=filename,
                file_path=file_path,
                uploaded_at=datetime.utcnow()
            )
            session.add(doc)
            
            # Create pages
            for page_data in pages:
                page = Page(
                    document_id=document_id,
                    page_no=page_data["page_no"],
                    text=page_data.get("text", "")
                )
                session.add(page)
            
            await session.commit()
            logger.info(f"Created document {document_id} with {len(pages)} pages")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create document {document_id}: {e}")
            raise


async def create_chunks(chunks_data: List[Dict]) -> List[int]:
    """
    Batch create chunks
    
    Args:
        chunks_data: List of chunk dicts
        
    Returns:
        List of chunk IDs
    """
    async with async_session_factory() as session:
        try:
            chunk_objects = []
            for chunk_data in chunks_data:
                chunk = Chunk(
                    document_id=chunk_data["document_id"],
                    page_no=chunk_data["page_no"],
                    char_start=chunk_data["char_start"],
                    char_end=chunk_data["char_end"],
                    text=chunk_data["text"]
                )
                chunk_objects.append(chunk)
                session.add(chunk)
            
            await session.commit()
            
            # Get IDs
            chunk_ids = [chunk.id for chunk in chunk_objects]
            logger.info(f"Created {len(chunk_ids)} chunks")
            
            return chunk_ids
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create chunks: {e}")
            raise


async def get_document(document_id: str) -> Optional[Dict]:
    """Get document metadata"""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            return None
        
        return {
            "id": doc.id,
            "filename": doc.filename,
            "file_path": doc.file_path,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
        }


async def get_document_pages(document_id: str) -> Optional[List[Dict]]:
    """Get all pages for a document"""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Page)
            .where(Page.document_id == document_id)
            .order_by(Page.page_no)
        )
        pages = result.scalars().all()
        
        if not pages:
            return None
        
        return [
            {
                "page_no": page.page_no,
                "text": page.text
            }
            for page in pages
        ]


async def list_documents(limit: int = 100, offset: int = 0) -> List[Dict]:
    """List all documents with pagination"""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Document)
            .order_by(Document.uploaded_at.desc())
            .limit(limit)
            .offset(offset)
        )
        docs = result.scalars().all()
        
        return [
            {
                "id": doc.id,
                "filename": doc.filename,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
            }
            for doc in docs
        ]


async def delete_document(document_id: str) -> bool:
    """Delete document and all associated data"""
    async with async_session_factory() as session:
        try:
            # Delete chunks
            await session.execute(
                delete(Chunk).where(Chunk.document_id == document_id)
            )
            
            # Delete pages
            await session.execute(
                delete(Page).where(Page.document_id == document_id)
            )
            
            # Delete document
            result = await session.execute(
                delete(Document).where(Document.id == document_id)
            )
            
            await session.commit()
            
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Deleted document {document_id}")
            
            return deleted
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise


async def get_db_stats() -> Dict[str, int]:
    """
    Get database statistics
    
    Returns:
        Dictionary with document, page, and chunk counts
    """
    async with async_session_factory() as session:
        try:
            # Count documents
            doc_result = await session.execute(select(func.count(Document.id)))
            doc_count = doc_result.scalar() or 0
            
            # Count pages
            page_result = await session.execute(select(func.count(Page.id)))
            page_count = page_result.scalar() or 0
            
            # Count chunks
            chunk_result = await session.execute(select(func.count(Chunk.id)))
            chunk_count = chunk_result.scalar() or 0
            
            return {
                "documents": doc_count,
                "pages": page_count,
                "chunks": chunk_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get DB stats: {e}")
            return {
                "documents": 0,
                "pages": 0,
                "chunks": 0
            }