"""
Request schemas for API endpoints
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List


class AskRequest(BaseModel):
    """Request schema for ask endpoint"""
    question: str = Field(..., min_length=1, max_length=1000, description="Question to ask")
    document_ids: Optional[List[str]] = Field(None, description="Filter by specific document IDs")
    top_k: int = Field(3, ge=1, le=10, description="Number of chunks to retrieve")
    use_search_enrichment: bool = Field(False, description="Enrich answer with external search")  # NEW
    
    @validator('question')
    def question_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty')
        return v.strip()


class ExtractRequest(BaseModel):
    """Request schema for extract endpoint"""
    document_id: str = Field(..., description="Document ID to extract from")
    use_llm: bool = Field(True, description="Use Groq LLM for extraction")  # NEW


class AuditRequest(BaseModel):
    """Request schema for audit endpoint"""
    document_id: str = Field(..., description="Document ID to audit")
    use_llm_fallback: bool = Field(True, description="Use Groq LLM for enhanced detection")  # Changed default