"""
Document ingestion endpoints with validation and error handling
"""
import uuid
import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import List, Optional
from datetime import datetime

from app.core.pdf_extractor import extract_pdf_pages
from app.db.crud import create_document_with_pages
from app.core.chunker import chunk_and_store
from app.core.embeddings import ensure_index_and_add
from app.schemas.responses import IngestResponse, DocumentInfo
from app.core.webhook_emitter import maybe_emit_webhook, emit_event
from app.logger import logger
from app.metrics import INGEST_COUNT, INGEST_PAGES

router = APIRouter()

# Configuration
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "50")) * 1024 * 1024  # Convert to bytes
ALLOWED_EXTENSIONS = {".pdf"}

def validate_file(file: UploadFile) -> None:
    """
    Validate uploaded file
    
    Args:
        file: Uploaded file
        
    Raises:
        HTTPException: If validation fails
    """
    # Check extension
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check content type
    if file.content_type not in ["application/pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content type. Must be application/pdf"
        )

@router.post("", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_files(
    files: List[UploadFile] = File(..., description="PDF files to ingest"),
    webhook_url: Optional[str] = Form(None, description="Optional webhook URL for completion notification")
):
    """
    Ingest one or more PDF documents
    
    Process:
    1. Validate files
    2. Extract text from PDFs
    3. Store metadata and pages in database
    4. Create overlapping chunks
    5. Generate embeddings and update FAISS index
    6. Send webhook notification (if provided)
    
    Returns:
        Document IDs and metadata
    """
    # Validate file count
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 files per request"
        )
    
    created_docs = []
    storage_path = os.getenv("STORAGE_PATH", "./storage")
    os.makedirs(storage_path, exist_ok=True)
    
    for file in files:
        try:
            # Validate file
            validate_file(file)
            
            # Read contents
            contents = await file.read()
            
            # Check file size
            if len(contents) > MAX_FILE_SIZE:
                logger.warning(f"File {file.filename} exceeds size limit")
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File size exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit"
                )
            
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Save file to storage
            file_path = os.path.join(storage_path, f"{doc_id}_{file.filename}")
            with open(file_path, "wb") as fh:
                fh.write(contents)
            
            logger.info(f"Processing document: {file.filename} (ID: {doc_id})")
            
            # Extract pages
            pages = extract_pdf_pages(file_path)
            
            if not pages:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"No text extracted from {file.filename}"
                )
            
            # Store in database
            await create_document_with_pages(doc_id, file.filename, file_path, pages)
            
            # Create chunks and store
            chunks = await chunk_and_store(doc_id, pages)
            
            # Add to embeddings index
            ensure_index_and_add(chunks)
            
            # Update metrics
            INGEST_COUNT.inc()
            INGEST_PAGES.inc(len(pages))
            
            created_docs.append(
                DocumentInfo(
                    document_id=doc_id,
                    filename=file.filename,
                    pages=len(pages)
                )
            )
            
            logger.info(
                f"Document {doc_id} ingested successfully: "
                f"{len(pages)} pages, {len(chunks)} chunks"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to process {file.filename}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process {file.filename}: {str(e)}"
            )
    
    # Prepare response
    response = IngestResponse(
        document_ids=[doc.document_id for doc in created_docs],
        meta=created_docs
    )
    
    # Send webhook notification (legacy)
    if webhook_url:
        payload = {
            "event": "ingest.completed",
            "timestamp": datetime.utcnow().isoformat(),
            "documents": [doc.dict() for doc in created_docs]
        }
        maybe_emit_webhook(webhook_url, payload)
    
    # Emit event to registered webhooks
    emit_event("ingest.completed", {
        "timestamp": datetime.utcnow().isoformat(),
        "documents": [doc.dict() for doc in created_docs]
    })
    
    return response

@router.get("/documents")
async def list_documents(limit: int = 100, offset: int = 0):
    """
    List all ingested documents
    
    Args:
        limit: Maximum number of documents to return
        offset: Number of documents to skip
    """
    from app.db.crud import list_documents as db_list_documents
    
    documents = await db_list_documents(limit=limit, offset=offset)
    return {"documents": documents, "count": len(documents)}

@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    """
    Get document metadata and pages
    """
    from app.db.crud import get_document, get_document_pages
    
    doc = await get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    pages = await get_document_pages(document_id)
    
    return {
        **doc,
        "pages": pages,
        "page_count": len(pages) if pages else 0
    }

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and all associated data
    """
    from app.db.crud import delete_document as db_delete_document
    
    deleted = await db_delete_document(document_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    logger.info(f"Document {document_id} deleted")
    
    return {"message": "Document deleted successfully"}