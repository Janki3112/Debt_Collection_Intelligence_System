"""
LLM client with Groq integration
"""
import os
from typing import Tuple, List, Dict, Any
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from app.logger import logger
from app.metrics import LLM_CALLS

# Initialize Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "1024"))
GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.0"))

# ========================================
# DEBUG: Verify Groq Configuration
# ========================================
logger.info("=" * 60)
logger.info("INIT] LLM CLIENT INITIALIZATION")
logger.info("=" * 60)
logger.info(f"GROQ_API_KEY: {'✔ Found (' + GROQ_API_KEY[:20] + '...' + GROQ_API_KEY[-4:] + ')' if GROQ_API_KEY else '[ERROR] Missing'}")
logger.info(f"GROQ_MODEL: {GROQ_MODEL}")
logger.info(f"GROQ_MAX_TOKENS: {GROQ_MAX_TOKENS}")
logger.info(f"GROQ_TEMPERATURE: {GROQ_TEMPERATURE}")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

logger.info(f"Groq client initialized: {'✔ Yes' if client else '[ERROR] No (API key missing)'}")
if client:
    logger.info(f"✔ Groq is READY - Model: {GROQ_MODEL}")
else:
    logger.warning("[WARN] Groq NOT initialized - will use extractive fallback")
logger.info("=" * 60)
# ========================================

# Recommended Groq models:
# - llama-3.1-70b-versatile: Best for complex reasoning (default)
# - llama-3.1-8b-instant: Fastest, good for simple tasks
# - mixtral-8x7b-32768: Large context window (32k tokens)
# - llama-3.2-90b-text-preview: Most capable (preview)
# - llama-3.3-70b-versatile: Newest, best overall (recommended)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def _call_groq_chat(system: str, user: str, max_tokens: int = None) -> str:
    """
    Call Groq Chat API with retry logic
    
    Args:
        system: System message
        user: User message
        max_tokens: Maximum tokens to generate (None = model default)
        
    Returns:
        Generated response text
    """
    if not client:
        raise ValueError("Groq API key not configured. Set GROQ_API_KEY in .env")
    
    try:
        # Prepare parameters
        params = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": GROQ_TEMPERATURE,
        }
        
        # Add max_tokens if specified
        if max_tokens:
            params["max_tokens"] = max_tokens
        else:
            params["max_tokens"] = GROQ_MAX_TOKENS
        
        logger.debug(f"Calling Groq API with model: {GROQ_MODEL}")
        response = client.chat.completions.create(**params)
        
        LLM_CALLS.labels(status="success").inc()
        logger.info(f"✔ Groq API call succeeded - Generated {len(response.choices[0].message.content)} chars")
        
        # Extract response text
        return response.choices[0].message.content
        
    except Exception as e:
        LLM_CALLS.labels(status="failure").inc()
        logger.error(f"[ERROR] Groq API call failed: {str(e)}")
        raise


def answer_with_optional_llm(
    question: str,
    chunks: List[Dict[str, Any]]
) -> Tuple[str, List[Dict[str, Any]], str]:
    """
    Generate answer using Groq LLM if available, otherwise use extractive method
    
    Args:
        question: User question
        chunks: Retrieved chunks with context
        
    Returns:
        Tuple of (answer, sources, model_used)
    """
    logger.info(f"Answering question with {len(chunks)} chunks")
    
    # Prepare sources
    sources = []
    context_parts = []
    
    for chunk in chunks:
        sources.append({
            "document_id": chunk["document_id"],
            "page": chunk["page_no"],
            "char_start": chunk["char_start"],
            "char_end": chunk["char_end"],
            "text": chunk["text"]
        })
        
        context_parts.append(
            f"[Document: {chunk['document_id']}, Page: {chunk['page_no']}]\n"
            f"{chunk['text']}"
        )
    
    context = "\n\n---\n\n".join(context_parts)
    
    # Try Groq if available
    if client and GROQ_API_KEY:
        try:
            logger.info(f"[AI] Using Groq LLM: {GROQ_MODEL}")
            
            system = (
                "You are a highly skilled contract analysis assistant. "
                "Answer questions based ONLY on the provided context. "
                "Be precise, concise, and always cite sources using document ID and page number. "
                "If information is not in the context, explicitly state that."
            )
            
            user = (
                f"CONTEXT:\n{context}\n\n"
                f"QUESTION: {question}\n\n"
                f"Provide a clear, accurate answer based exclusively on the context above. "
                f"Include citations in format [Doc: document_id, Page: N]."
            )
            
            answer = _call_groq_chat(system, user)
            logger.info(f"✔ Generated answer using Groq ({len(answer)} chars)")
            return answer, sources, f"groq-{GROQ_MODEL}"
            
        except Exception as e:
            logger.warning(f"[WARN] Groq failed, using fallback: {str(e)}")
    else:
        logger.info("ℹ️ Groq not available, using extractive fallback")
    
    # Fallback: extractive answer
    max_context = 2000
    truncated_context = context[:max_context]
    if len(context) > max_context:
        truncated_context += "..."
    
    answer = (
        f"Based on the retrieved documents:\n\n{truncated_context}\n\n"
        f"[Note: This is an extractive answer. Configure GROQ_API_KEY for enhanced responses.]"
    )
    
    logger.info("📝 Using extractive fallback method")
    return answer, sources, "extractive"


def enhance_audit_with_llm(contract_text: str, rules_findings: List[Dict]) -> List[Dict]:
    """
    Enhance audit findings using Groq LLM
    
    Args:
        contract_text: Full contract text
        rules_findings: Findings from rule engine
        
    Returns:
        Enhanced findings with LLM analysis
    """
    if not client or not GROQ_API_KEY:
        logger.info("Groq not configured, skipping LLM enhancement")
        return rules_findings
    
    try:
        logger.info("[AI] Enhancing audit with Groq LLM")
        
        system = (
            "You are an expert contract auditor. Analyze the contract for additional "
            "risky clauses beyond the initial findings. Focus on: unusual termination "
            "provisions, hidden fees, unfavorable dispute resolution, data rights issues."
        )
        
        # Limit contract text for context window
        limited_text = contract_text[:8000]
        
        user = (
            f"CONTRACT (excerpt):\n{limited_text}\n\n"
            f"INITIAL FINDINGS:\n{len(rules_findings)} issues detected\n\n"
            f"Find 2-3 additional risky clauses not yet identified. "
            f"For each, provide: rule_name, severity, explanation, evidence (quote)."
        )
        
        response = _call_groq_chat(system, user, max_tokens=1024)
        
        # Parse response (basic parsing - enhance as needed)
        # For now, add as single finding
        enhanced_findings = rules_findings.copy()
        enhanced_findings.append({
            "rule": "llm_enhanced_analysis",
            "severity": "medium",
            "explain": "LLM-detected additional concerns",
            "evidence": response[:500],
            "page_numbers": None
        })
        
        logger.info("✔ Audit enhanced with Groq LLM analysis")
        return enhanced_findings
        
    except Exception as e:
        logger.error(f"LLM enhancement failed: {e}")
        return rules_findings


def extract_fields_with_llm(contract_text: str) -> Dict[str, Any]:
    """
    Extract structured fields using Groq LLM
    
    Args:
        contract_text: Full contract text
        
    Returns:
        Extracted fields dictionary
    """
    if not client or not GROQ_API_KEY:
        logger.info("Groq not configured, skipping LLM extraction")
        return {}
    
    try:
        logger.info("[AI] Extracting fields with Groq LLM")
        
        system = (
            "You are a contract parsing expert. Extract structured information "
            "from contracts with high accuracy. Return information in a clear format."
        )
        
        # Limit text
        limited_text = contract_text[:10000]
        
        user = (
            f"CONTRACT:\n{limited_text}\n\n"
            f"Extract and return the following in this exact format:\n"
            f"PARTIES: [list parties]\n"
            f"EFFECTIVE_DATE: [date or 'Not found']\n"
            f"TERM: [term length or 'Not found']\n"
            f"GOVERNING_LAW: [jurisdiction or 'Not found']\n"
            f"PAYMENT_TERMS: [payment terms or 'Not found']\n"
            f"AUTO_RENEWAL: [YES/NO]\n"
            f"LIABILITY_CAP: [amount or 'Not found']\n"
        )
        
        response = _call_groq_chat(system, user, max_tokens=512)
        
        # Basic parsing (enhance with regex)
        fields = {}
        lines = response.strip().split('\n')
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                fields[key] = value
        
        logger.info(f"✔ Extracted {len(fields)} fields using Groq LLM")
        return fields
        
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        return {}