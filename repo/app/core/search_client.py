"""
Tavily Search integration for external information retrieval
"""
import os
from typing import List, Dict, Any, Optional
from tavily import TavilyClient

from app.logger import logger

# Initialize Tavily client
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None


def search_legal_info(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search for legal/contract-related information using Tavily
    
    Args:
        query: Search query
        max_results: Maximum number of results
        
    Returns:
        List of search results with title, url, content
    """
    if not tavily_client:
        logger.warning("Tavily API key not configured")
        return []
    
    try:
        # Enhance query for legal context
        enhanced_query = f"contract law legal {query}"
        
        response = tavily_client.search(
            query=enhanced_query,
            search_depth="advanced",  # "basic" or "advanced"
            max_results=max_results,
            include_domains=["law.cornell.edu", "nolo.com", "legalmatch.com"],  # Trusted legal sites
        )
        
        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", "")[:500],  # Limit content
                "score": item.get("score", 0.0)
            })
        
        logger.info(f"Tavily search returned {len(results)} results for: {query}")
        return results
        
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return []


def enrich_answer_with_search(
    question: str,
    rag_answer: str,
    sources: List[Dict]
) -> Dict[str, Any]:
    """
    Enrich RAG answer with external search results
    
    Args:
        question: Original question
        rag_answer: Answer from RAG system
        sources: RAG sources
        
    Returns:
        Enriched response with external references
    """
    if not tavily_client:
        return {
            "answer": rag_answer,
            "sources": sources,
            "external_references": []
        }
    
    try:
        # Search for related information
        search_results = search_legal_info(question, max_results=2)
        
        # Build enriched answer
        enriched_answer = rag_answer
        
        if search_results:
            enriched_answer += "\n\n**Additional Legal Context:**\n"
            for idx, result in enumerate(search_results, 1):
                enriched_answer += (
                    f"\n{idx}. [{result['title']}]({result['url']})\n"
                    f"   {result['content'][:200]}...\n"
                )
        
        return {
            "answer": enriched_answer,
            "sources": sources,
            "external_references": search_results
        }
        
    except Exception as e:
        logger.error(f"Answer enrichment failed: {e}")
        return {
            "answer": rag_answer,
            "sources": sources,
            "external_references": []
        }
    
# --- Compatibility alias for backward imports ---
async def search_web(query: str) -> Dict[str, Any]:
    """
    Compatibility wrapper to support web search fallback in ask.py.
    Uses Tavily search directly.
    """
    try:
        results = search_legal_info(query, max_results=3)
        if not results:
            return {"answer": "No web search results found.", "external_references": []}

        summary = "\n".join(
            [f"{i+1}. {r['title']} - {r['url']}" for i, r in enumerate(results)]
        )

        return {
            "answer": f"Here are some web references for '{query}':\n{summary}",
            "external_references": results,
        }
    except Exception as e:
        logger.error(f"search_web failed: {e}")
        return {"answer": f"Web search failed: {str(e)}", "external_references": []}
