"""
Retrieval logic for RAG system
"""
from typing import List, Dict, Any, Optional

from app.core.embeddings import search_index
from app.logger import logger


def retrieve_top_k(
    query: str,
    document_ids: Optional[List[str]] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Retrieve top-k most relevant chunks for a query
    
    Args:
        query: User query
        document_ids: Optional list of document IDs to filter by
        top_k: Number of chunks to retrieve
        
    Returns:
        List of relevant chunks with metadata
    """
    try:
        logger.info(f"Retrieving top-{top_k} chunks for query: {query[:50]}...")
        
        # Search the FAISS index
        results = search_index(query, top_k=top_k, document_ids=document_ids)
        
        if not results:
            logger.warning("No relevant chunks found")
            return []
        
        logger.info(f"Retrieved {len(results)} chunks")
        
        # Enhance results with ranking
        for i, chunk in enumerate(results):
            chunk["rank"] = i + 1
        
        return results
        
    except Exception as e:
        logger.error(f"Retrieval failed: {str(e)}", exc_info=True)
        return []


def retrieve_with_reranking(
    query: str,
    document_ids: Optional[List[str]] = None,
    top_k: int = 5,
    initial_k: int = 20
) -> List[Dict[str, Any]]:
    """
    Retrieve with two-stage reranking
    
    Stage 1: Retrieve more candidates (initial_k)
    Stage 2: Rerank and return top_k
    
    Args:
        query: User query
        document_ids: Optional list of document IDs to filter by
        top_k: Final number of chunks to return
        initial_k: Number of initial candidates to retrieve
        
    Returns:
        Reranked list of top-k chunks
    """
    # First stage: retrieve more candidates
    candidates = retrieve_top_k(query, document_ids, top_k=initial_k)
    
    if not candidates:
        return []
    
    # Second stage: simple reranking by score and text length balance
    # In production, use a cross-encoder model for better reranking
    for chunk in candidates:
        # Simple scoring: balance relevance and completeness
        text_length_score = min(len(chunk["text"]) / 1000, 1.0)  # Normalize to 0-1
        relevance_score = 1.0 / (1.0 + chunk["score"])  # Lower distance = higher score
        
        chunk["rerank_score"] = 0.7 * relevance_score + 0.3 * text_length_score
    
    # Sort by rerank score
    reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
    
    # Return top_k
    return reranked[:top_k]