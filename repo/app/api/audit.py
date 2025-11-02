"""
Contract audit endpoints with Groq LLM enhancement
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.db.crud import get_document_pages
from app.core.rule_engine import run_audit_rules
from app.core.llm_client import enhance_audit_with_llm  # NEW IMPORT
from app.schemas.responses import AuditResponse, AuditFinding
from app.logger import logger
from app.metrics import AUDIT_COUNT

router = APIRouter()


class AuditRequest(BaseModel):
    document_id: str
    use_llm_fallback: bool = True  # Changed default to True


@router.post("", response_model=AuditResponse)
async def audit(req: AuditRequest):
    """
    Audit contract for risky clauses
    
    Uses rule-based detection + optional Groq LLM enhancement
    """
    pages = await get_document_pages(req.document_id)
    
    if pages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    try:
        # Run rule-based audit
        findings = run_audit_rules(
            req.document_id,
            pages,
            use_llm_fallback=False  # LLM enhancement done separately
        )
        
        # Enhance with Groq LLM
        if req.use_llm_fallback:
            full_text = "\n\n".join(p.get("text", "") for p in pages)
            findings = enhance_audit_with_llm(full_text, findings)
        
        # Update metrics
        AUDIT_COUNT.inc()
        
        # Calculate risk score
        risk_score = calculate_risk_score(findings)
        
        logger.info(
            f"Audit completed for {req.document_id}: "
            f"{len(findings)} findings, risk score {risk_score:.1f} (LLM: {req.use_llm_fallback})"
        )
        
        # Format findings
        formatted_findings = [
            AuditFinding(**finding)
            for finding in findings
        ]
        
        return AuditResponse(
            document_id=req.document_id,
            findings=formatted_findings,
            total_findings=len(findings),
            risk_score=risk_score
        )
        
    except Exception as e:
        logger.error(f"Audit failed for {req.document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit failed: {str(e)}"
        )


def calculate_risk_score(findings: list) -> float:
    """Calculate overall risk score based on findings"""
    if not findings:
        return 0.0
    
    severity_weights = {
        "critical": 40,
        "high": 25,
        "medium": 15,
        "low": 5
    }
    
    total_score = sum(
        severity_weights.get(f.get("severity", "low"), 0)
        for f in findings
    )
    
    return min(100.0, total_score)