"""
Request schemas for API endpoints
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List


class AskRequest(BaseModel):
    """Request schema for ask endpoint"""
    question: str = Field(..., min_length=1, max_length=1000, description="Question to ask")
    
    # FIXED: Support both singular and plural for backward compatibility
    document_id: Optional[str] = Field(None, description="Single document ID (legacy)")
    document_ids: Optional[List[str]] = Field(None, description="Filter by specific document IDs")
    
    top_k: int = Field(3, ge=1, le=10, description="Number of chunks to retrieve")
    use_search_enrichment: bool = Field(False, description="Enrich answer with external search")
    
    @field_validator('question')
    @classmethod
    def question_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty')
        return v.strip()
    
    @model_validator(mode='after')
    def normalize_document_ids(self):
        """
        Convert single document_id to list, ensuring document_ids is always a list or None
        Priority: document_ids > document_id
        """
        # If document_ids is already provided, use it
        if self.document_ids is not None:
            return self
        
        # Otherwise, convert document_id to list if provided
        if self.document_id:
            self.document_ids = [self.document_id]
        
        return self


class ExtractRequest(BaseModel):
    """Request schema for extract endpoint"""
    document_id: str = Field(..., description="Document ID to extract from")
    use_llm: bool = Field(True, description="Use Groq LLM for extraction")


class AuditRequest(BaseModel):
    """Request schema for audit endpoint"""
    document_id: str = Field(..., description="Document ID to audit")
    use_llm_fallback: bool = Field(True, description="Use Groq LLM for enhanced detection")