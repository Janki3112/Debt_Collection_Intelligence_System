"""
Extract endpoint with improved LLM field parsing
"""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
import re
import json

from app.schemas.requests import ExtractRequest
from app.schemas.responses import ExtractResponse, SignatoryInfo, LiabilityCap
from app.db.session import async_session
from app.db.models import Document, Page
from app.core.extractor import extract_structured_fields
from app.core.llm_client import extract_fields_with_llm
from app.logger import logger

router = APIRouter()


def parse_llm_extraction(llm_fields: dict, rule_based: dict) -> dict:
    """
    Parse and merge LLM extraction with rule-based extraction
    Handles various LLM output formats robustly
    """
    merged = rule_based.copy()
    
    for key, value in llm_fields.items():
        if not value or value in ['Not found', 'N/A', 'None', '']:
            continue
        
        # Handle parties (convert string to list)
        if key == 'parties':
            if isinstance(value, str):
                # Split by common delimiters
                parties = re.split(r'[,;&]|\band\b', value)
                parties = [p.strip() for p in parties if p.strip()]
                # Filter out template placeholders
                parties = [p for p in parties if not re.match(r'\[.*?\]', p)]
                if parties:
                    merged['parties'] = parties
            elif isinstance(value, list):
                merged['parties'] = value
        
        # Handle booleans
        elif key in ['auto_renewal', 'confidentiality', 'indemnity']:
            if isinstance(value, str):
                value_lower = value.lower()
                if value_lower in ['yes', 'true', '1', 'present', 'included']:
                    merged[key] = True
                elif value_lower in ['no', 'false', '0', 'absent', 'not found']:
                    merged[key] = False
            elif isinstance(value, bool):
                merged[key] = value
        
        # Handle liability cap
        elif key == 'liability_cap':
            if isinstance(value, str) and value.lower() != 'not found':
                # Try to extract amount and currency
                amount_match = re.search(r'[\$£€]?([\d,]+(?:\.\d+)?)', value)
                currency_match = re.search(r'(USD|GBP|EUR|INR)', value, re.IGNORECASE)
                
                if amount_match:
                    amount_str = amount_match.group(1).replace(',', '')
                    try:
                        amount = float(amount_str)
                        currency = currency_match.group(1).upper() if currency_match else 'USD'
                        merged['liability_cap'] = {
                            'amount': amount,
                            'currency': currency
                        }
                    except ValueError:
                        pass
        
        # Handle simple strings
        elif key in ['effective_date', 'term', 'governing_law', 'payment_terms', 'termination']:
            if isinstance(value, str) and value.lower() not in ['not found', 'n/a', 'none']:
                merged[key] = value
        
        # Handle signatories
        elif key == 'signatories':
            if isinstance(value, str):
                # Try to parse signatories from string
                names = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+)', value)
                if names:
                    merged['signatories'] = [{'name': name, 'title': None} for name in names]
            elif isinstance(value, list):
                merged['signatories'] = value
    
    return merged


@router.post("", response_model=ExtractResponse)
async def extract(req: ExtractRequest):
    """
    Extract structured fields from a document
    
    Uses both rule-based extraction and Groq LLM for enhanced accuracy.
    """
    try:
        # Fetch document
        async with async_session() as session:
            result = await session.execute(
                select(Document).where(Document.id == req.document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document {req.document_id} not found"
                )
            
            # Get all pages
            pages_result = await session.execute(
                select(Page).where(Page.document_id == req.document_id).order_by(Page.page_no)
            )
            pages = pages_result.scalars().all()
            
            if not pages:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No pages found for document"
                )
        
        # Combine all page text
        full_text = "\n\n".join([page.text for page in pages])
        
        # Rule-based extraction
        logger.info(f"Extracting fields from document {req.document_id}")
        extracted = extract_structured_fields(req.document_id, [{"text": page.text} for page in pages])

        
        # LLM enhancement if enabled
        if req.use_llm:
            try:
                logger.info("Enhancing extraction with Groq LLM")
                llm_fields = extract_fields_with_llm(full_text)
                
                if llm_fields:
                    # Parse and merge LLM fields
                    extracted = parse_llm_extraction(llm_fields, extracted)
                    logger.info(f"LLM enhanced extraction with {len(llm_fields)} fields")
            
            except Exception as e:
                logger.warning(f"LLM extraction failed, using rule-based only: {e}")
        
        # Ensure proper data types for response
        response_data = {
            "document_id": req.document_id,
            "parties": extracted.get("parties", []),
            "effective_date": extracted.get("effective_date"),
            "term": extracted.get("term"),
            "governing_law": extracted.get("governing_law"),
            "payment_terms": extracted.get("payment_terms"),
            "termination": extracted.get("termination"),
            "auto_renewal": extracted.get("auto_renewal", False),
            "confidentiality": extracted.get("confidentiality", False),
            "indemnity": extracted.get("indemnity", False),
            "signatories": []
        }
        
        # Handle liability cap
        if extracted.get("liability_cap"):
            cap = extracted["liability_cap"]
            if isinstance(cap, dict):
                response_data["liability_cap"] = LiabilityCap(
                    amount=cap.get("amount", 0),
                    currency=cap.get("currency", "USD")
                )
        
        # Handle signatories
        if extracted.get("signatories"):
            sigs = extracted["signatories"]
            if isinstance(sigs, list):
                response_data["signatories"] = [
                    SignatoryInfo(
                        name=sig.get("name", sig) if isinstance(sig, dict) else sig,
                        title=sig.get("title") if isinstance(sig, dict) else None
                    )
                    for sig in sigs
                ]
        
        logger.info(f"Extraction complete: {len(response_data['parties'])} parties, "
                   f"{len(response_data['signatories'])} signatories")
        
        return ExtractResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed: {str(e)}"
        )