"""
Response schemas for API endpoints
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class DocumentInfo(BaseModel):
    """Document metadata"""
    document_id: str
    filename: str
    pages: int

class IngestResponse(BaseModel):
    """Response from ingest endpoint"""
    document_ids: List[str]
    meta: List[DocumentInfo]
    message: str = "Documents ingested successfully"

class SignatoryInfo(BaseModel):
    """Signatory information"""
    name: str
    title: Optional[str] = None

class LiabilityCap(BaseModel):
    """Liability cap information"""
    amount: float
    currency: str = "USD"

class ExtractResponse(BaseModel):
    """Response from extract endpoint"""
    document_id: str
    parties: List[str] = Field(default_factory=list)
    effective_date: Optional[str] = None
    term: Optional[str] = None
    governing_law: Optional[str] = None
    payment_terms: Optional[str] = None
    termination: Optional[str] = None
    auto_renewal: bool = False
    confidentiality: bool = False
    indemnity: bool = False
    liability_cap: Optional[LiabilityCap] = None
    signatories: List[SignatoryInfo] = Field(default_factory=list)

class SourceCitation(BaseModel):
    """Source citation for answers"""
    document_id: str
    page: int
    char_start: int
    char_end: int
    text_snippet: Optional[str] = None

class AskResponse(BaseModel):
    """Response from ask endpoint"""
    answer: str
    sources: List[SourceCitation]
    confidence: Optional[float] = None
    model_used: str = "extractive"

class AuditFinding(BaseModel):
    """Individual audit finding"""
    rule: str
    severity: str  # critical, high, medium, low
    explain: str
    evidence: str
    page_numbers: Optional[List[int]] = None

class AuditResponse(BaseModel):
    """Response from audit endpoint"""
    document_id: str
    findings: List[AuditFinding]
    total_findings: int
    risk_score: Optional[float] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())