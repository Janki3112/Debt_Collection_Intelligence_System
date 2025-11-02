"""
Rule-based contract audit engine
"""
import re
from typing import List, Dict, Any

from app.logger import logger


def run_audit_rules(
    document_id: str,
    pages: List[Dict],
    use_llm_fallback: bool = False
) -> List[Dict[str, Any]]:
    """
    Run audit rules on document pages
    
    Args:
        document_id: Document ID
        pages: List of page dicts with 'page_no' and 'text'
        use_llm_fallback: Whether to use LLM for unclear cases
        
    Returns:
        List of findings with severity and evidence
    """
    findings = []
    
    # Combine all text for full-document analysis
    full_text = "\n".join(page.get("text", "") for page in pages)
    full_text_lower = full_text.lower()
    
    # Rule 1: Auto-renewal with short notice period
    findings.extend(_check_auto_renewal(pages, full_text_lower))
    
    # Rule 2: Unlimited liability
    findings.extend(_check_unlimited_liability(pages, full_text_lower))
    
    # Rule 3: Broad indemnity clauses
    findings.extend(_check_broad_indemnity(pages, full_text_lower))
    
    # Rule 4: Missing termination clauses
    findings.extend(_check_missing_termination(pages, full_text_lower))
    
    # Rule 5: Unfavorable payment terms
    findings.extend(_check_payment_terms(pages, full_text_lower))
    
    # Rule 6: Non-compete clauses
    findings.extend(_check_non_compete(pages, full_text_lower))
    
    # Rule 7: Unilateral modification rights
    findings.extend(_check_unilateral_modification(pages, full_text_lower))
    
    logger.info(f"Audit found {len(findings)} issues in document {document_id}")
    
    return findings


def _check_auto_renewal(pages: List[Dict], full_text: str) -> List[Dict]:
    """Check for auto-renewal with insufficient notice period"""
    findings = []
    
    # Pattern: auto-renewal with notice period
    auto_renewal_patterns = [
        r'auto(?:matic)?(?:ally)?\s+renew',
        r'automatically\s+extend',
        r'shall\s+renew',
        r'will\s+renew'
    ]
    
    for pattern in auto_renewal_patterns:
        if re.search(pattern, full_text, re.IGNORECASE):
            # Check notice period
            notice_match = re.search(
                r'(\d+)\s*day[s]?\s+(?:notice|written\s+notice|prior\s+notice)',
                full_text,
                re.IGNORECASE
            )
            
            if notice_match:
                days = int(notice_match.group(1))
                if days < 30:
                    # Find page numbers
                    page_numbers = _find_text_pages(pages, pattern)
                    
                    findings.append({
                        "rule": "auto_renewal_short_notice",
                        "severity": "high",
                        "explain": f"Contract has auto-renewal with only {days} days notice period (recommended: 30+ days)",
                        "evidence": notice_match.group(0),
                        "page_numbers": page_numbers
                    })
            else:
                # Auto-renewal found but no notice period mentioned
                page_numbers = _find_text_pages(pages, pattern)
                
                findings.append({
                    "rule": "auto_renewal_no_notice",
                    "severity": "critical",
                    "explain": "Contract has auto-renewal clause without specified notice period",
                    "evidence": "Auto-renewal clause found without notice period details",
                    "page_numbers": page_numbers
                })
            
            break  # Only report once
    
    return findings


def _check_unlimited_liability(pages: List[Dict], full_text: str) -> List[Dict]:
    """Check for unlimited liability"""
    findings = []
    
    # Check for liability caps first
    has_cap = bool(re.search(
        r'liabilit(?:y|ies)\s+(?:is|shall\s+be)?\s+limited\s+to',
        full_text,
        re.IGNORECASE
    ))
    
    if not has_cap:
        # Check for unlimited liability language
        unlimited_patterns = [
            r'unlimited\s+liabilit',
            r'liabilit(?:y|ies).*without\s+limit',
            r'no\s+limitation.*liabilit'
        ]
        
        for pattern in unlimited_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                page_numbers = _find_text_pages(pages, pattern)
                
                findings.append({
                    "rule": "unlimited_liability",
                    "severity": "critical",
                    "explain": "Contract contains unlimited liability provisions",
                    "evidence": "Unlimited liability language found",
                    "page_numbers": page_numbers
                })
                break
    
    return findings


def _check_broad_indemnity(pages: List[Dict], full_text: str) -> List[Dict]:
    """Check for overly broad indemnity clauses"""
    findings = []
    
    # Look for indemnity clauses
    indemnity_patterns = [
        r'shall\s+indemnify',
        r'agree[s]?\s+to\s+indemnify',
        r'indemnify.*hold\s+harmless'
    ]
    
    for pattern in indemnity_patterns:
        matches = list(re.finditer(pattern, full_text, re.IGNORECASE))
        
        if matches:
            # Check if indemnity includes third-party claims
            has_third_party = bool(re.search(
                r'third[\s-]party\s+claim',
                full_text,
                re.IGNORECASE
            ))
            
            # Check if indemnity includes indirect damages
            has_indirect = bool(re.search(
                r'indirect.*damage|consequential.*damage',
                full_text,
                re.IGNORECASE
            ))
            
            if has_third_party or has_indirect:
                page_numbers = _find_text_pages(pages, pattern)
                
                severity = "high" if has_third_party else "medium"
                
                findings.append({
                    "rule": "broad_indemnity",
                    "severity": severity,
                    "explain": "Contract contains broad indemnity obligations including third-party claims or indirect damages",
                    "evidence": "Indemnity clause with broad scope found",
                    "page_numbers": page_numbers
                })
                break
    
    return findings


def _check_missing_termination(pages: List[Dict], full_text: str) -> List[Dict]:
    """Check for missing or unclear termination clauses"""
    findings = []
    
    # Look for termination clauses
    termination_patterns = [
        r'termination',
        r'terminate\s+this\s+agreement',
        r'cancel(?:lation)?',
        r'end\s+this\s+agreement'
    ]
    
    has_termination = any(
        re.search(pattern, full_text, re.IGNORECASE)
        for pattern in termination_patterns
    )
    
    if not has_termination:
        findings.append({
            "rule": "missing_termination",
            "severity": "high",
            "explain": "Contract does not contain clear termination provisions",
            "evidence": "No termination clause found",
            "page_numbers": []
        })
    
    return findings


def _check_payment_terms(pages: List[Dict], full_text: str) -> List[Dict]:
    """Check for unfavorable payment terms"""
    findings = []
    
    # Check for payment terms
    payment_match = re.search(
        r'(?:payment|invoice).*(?:due|payable).*(\d+)\s*day',
        full_text,
        re.IGNORECASE
    )
    
    if payment_match:
        days = int(payment_match.group(1))
        
        if days < 15:
            page_numbers = _find_text_pages(pages, r'payment.*due')
            
            findings.append({
                "rule": "short_payment_terms",
                "severity": "medium",
                "explain": f"Payment due in {days} days (industry standard: 30 days)",
                "evidence": payment_match.group(0),
                "page_numbers": page_numbers
            })
    
    return findings


def _check_non_compete(pages: List[Dict], full_text: str) -> List[Dict]:
    """Check for non-compete clauses"""
    findings = []
    
    non_compete_patterns = [
        r'non[\s-]compete',
        r'shall\s+not\s+compete',
        r'agree\s+not\s+to\s+compete'
    ]
    
    for pattern in non_compete_patterns:
        if re.search(pattern, full_text, re.IGNORECASE):
            page_numbers = _find_text_pages(pages, pattern)
            
            findings.append({
                "rule": "non_compete_clause",
                "severity": "medium",
                "explain": "Contract contains non-compete provisions that may restrict business activities",
                "evidence": "Non-compete clause found",
                "page_numbers": page_numbers
            })
            break
    
    return findings


def _check_unilateral_modification(pages: List[Dict], full_text: str) -> List[Dict]:
    """Check for unilateral modification rights"""
    findings = []
    
    unilateral_patterns = [
        r'may\s+modify.*at\s+(?:any\s+time|its\s+discretion)',
        r'reserves?\s+the\s+right\s+to\s+(?:modify|amend|change)',
        r'unilateral(?:ly)?\s+modify'
    ]
    
    for pattern in unilateral_patterns:
        if re.search(pattern, full_text, re.IGNORECASE):
            page_numbers = _find_text_pages(pages, pattern)
            
            findings.append({
                "rule": "unilateral_modification",
                "severity": "high",
                "explain": "Contract allows one party to unilaterally modify terms",
                "evidence": "Unilateral modification language found",
                "page_numbers": page_numbers
            })
            break
    
    return findings


def _find_text_pages(pages: List[Dict], pattern: str) -> List[int]:
    """Find which pages contain a pattern"""
    page_numbers = []
    
    for page in pages:
        text = page.get("text", "")
        if re.search(pattern, text, re.IGNORECASE):
            page_numbers.append(page["page_no"])
    
    return page_numbers