"""
Structured field extraction from contracts
"""
import re
from typing import List, Dict, Any, Optional

from app.logger import logger


def extract_structured_fields(document_id: str, pages: List[Dict]) -> Dict[str, Any]:
    """
    Extract structured fields from contract pages
    
    Args:
        document_id: Document UUID
        pages: List of page dicts with text
        
    Returns:
        Dict with extracted fields
    """
    full_text = "\n\n".join(p.get("text", "") for p in pages if p.get("text"))
    
    if not full_text.strip():
        logger.warning(f"No text in document {document_id}")
        return _empty_extraction(document_id)
    
    logger.info(f"Extracting structured fields from document {document_id}")
    
    return {
        "document_id": document_id,
        "parties": _extract_parties(full_text),
        "effective_date": _extract_effective_date(full_text),
        "term": _extract_term(full_text),
        "governing_law": _extract_governing_law(full_text),
        "payment_terms": _extract_payment_terms(full_text),
        "termination": _extract_termination(full_text),
        "auto_renewal": _check_auto_renewal(full_text),
        "confidentiality": _check_confidentiality(full_text),
        "indemnity": _check_indemnity(full_text),
        "liability_cap": _extract_liability_cap(full_text),
        "signatories": _extract_signatories(full_text)
    }


def _empty_extraction(document_id: str) -> Dict[str, Any]:
    """Return empty extraction result"""
    return {
        "document_id": document_id,
        "parties": [],
        "effective_date": None,
        "term": None,
        "governing_law": None,
        "payment_terms": None,
        "termination": None,
        "auto_renewal": False,
        "confidentiality": False,
        "indemnity": False,
        "liability_cap": None,
        "signatories": []
    }


def _extract_parties(text: str) -> List[str]:
    """Extract party names"""
    parties = []
    
    patterns = [
        r'between\s+([A-Z][A-Za-z\s&,\.]+?)(?:\s+and\s+|\s*,\s*and\s+)([A-Z][A-Za-z\s&,\.]+?)(?:\s*[,\.\(]|\s+hereinafter)',
        r'parties:\s*([A-Z][^,\n]+),?\s*and\s*([A-Z][^,\n]+)',
        r'AGREEMENT.*?between\s+([A-Z][A-Za-z\s&,\.]+?)\s+\("[\w\s]+"\)\s+and\s+([A-Z][A-Za-z\s&,\.]+?)\s+\("[\w\s]+"\)'
    ]
    
    for pattern in patterns:
        matches = re.search(pattern, text, re.IGNORECASE)
        if matches:
            parties.extend([m.strip() for m in matches.groups() if m])
            break
    
    return parties[:10]  # Limit to 10 parties


def _extract_effective_date(text: str) -> Optional[str]:
    """Extract effective date"""
    patterns = [
        r'effective\s+date[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'effective\s+as\s+of\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'dated\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None


def _extract_term(text: str) -> Optional[str]:
    """Extract contract term/duration"""
    patterns = [
        r'term\s+of\s+(\d+\s+(?:year|month|day)s?)',
        r'period\s+of\s+(\d+\s+(?:year|month|day)s?)',
        r'duration\s+of\s+(\d+\s+(?:year|month|day)s?)',
        r'for\s+a\s+term\s+of\s+(\d+\s+(?:year|month|day)s?)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None


def _extract_governing_law(text: str) -> Optional[str]:
    """Extract governing law jurisdiction"""
    patterns = [
        r'governed\s+by\s+the\s+laws\s+of\s+([^,\.\n]{5,50})',
        r'laws\s+of\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+shall\s+govern',
        r'jurisdiction:\s*([A-Z][^,\.\n]{3,50})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None


def _extract_payment_terms(text: str) -> Optional[str]:
    """Extract payment terms"""
    pattern = r'payment\s+terms?:?\s*([^\n]{10,200})'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        return match.group(1).strip()
    
    # Try alternative
    pattern = r'invoice.*?due.*?(\d+\s+days?)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return f"Due within {match.group(1)}"
    
    return None


def _extract_termination(text: str) -> Optional[str]:
    """Extract termination clause summary"""
    pattern = r'termination[:\.\s]+([^\n]{20,300})'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        return match.group(1).strip()[:200]  # Limit length
    
    return None


def _check_auto_renewal(text: str) -> bool:
    """Check if contract has auto-renewal"""
    patterns = [
        r'auto(?:matically)?\s*renew',
        r'automatic\s*renewal',
        r'renew\s*automatically'
    ]
    
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _check_confidentiality(text: str) -> bool:
    """Check if contract has confidentiality clause"""
    patterns = [
        r'confidential',
        r'non-disclosure',
        r'proprietary\s+information'
    ]
    
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _check_indemnity(text: str) -> bool:
    """Check if contract has indemnity clause"""
    patterns = [
        r'indemnif',
        r'hold\s+harmless'
    ]
    
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _extract_liability_cap(text: str) -> Optional[Dict[str, Any]]:
    """Extract liability cap if present"""
    pattern = r'liability.*?(?:limited\s+to|not\s+exceed|cap\s+of)\s*\$?([\d,]+(?:\.\d{2})?)\s*(million|thousand|USD|dollars)?'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        amount_str = match.group(1).replace(',', '')
        multiplier_str = match.group(2) or ''
        
        try:
            amount = float(amount_str)
            
            # Apply multiplier
            if 'million' in multiplier_str.lower():
                amount *= 1_000_000
            elif 'thousand' in multiplier_str.lower():
                amount *= 1_000
            
            return {
                "amount": amount,
                "currency": "USD"
            }
        except ValueError:
            pass
    
    return None


def _extract_signatories(text: str) -> List[Dict[str, Any]]:
    """Extract signatory information"""
    signatories = []
    
    # Look for signature blocks
    patterns = [
        r'(?:signed|by):\s*([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s*,\s*([A-Za-z\s]+))?',
        r'Name:\s*([A-Z][a-z]+\s+[A-Z][a-z]+).*?Title:\s*([A-Za-z\s]+)',
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.DOTALL):
            name = match.group(1).strip()
            title = match.group(2).strip() if len(match.groups()) > 1 and match.group(2) else None
            
            signatories.append({
                "name": name,
                "title": title
            })
    
    return signatories[:10]  # Limit to 10 signatories