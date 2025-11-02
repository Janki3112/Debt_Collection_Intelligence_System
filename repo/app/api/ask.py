"""
Q&A endpoints with streaming support and search enrichment
"""
from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
from sse_starlette.sse import EventSourceResponse
import asyncio
import json

from app.schemas.requests import AskRequest
from app.schemas.responses import AskResponse, SourceCitation
from app.core.retriever import retrieve_top_k
from app.core.llm_client import answer_with_optional_llm
from app.core.search_client import enrich_answer_with_search, search_web
from app.logger import logger
from app.metrics import ASK_COUNT

router = APIRouter()


@router.post("", response_model=AskResponse)
async def ask(req: AskRequest):
    """
    Answer questions using RAG over ingested documents
    
    Process:
    1. Embed question
    2. Retrieve top-k relevant chunks
    3. Generate answer using Groq LLM (if available) or extractive method
    4. Optionally enrich with external search (Tavily)
    5. Return answer with source citations
    """
    try:
        # Retrieve relevant chunks
        chunks = retrieve_top_k(
            req.question,
            req.document_ids,
            top_k=req.top_k
        )
        
        # If no chunks found and search enrichment is enabled, search the web
        if not chunks and req.use_search_enrichment:
            logger.info("No documents found, falling back to web search")
            try:
                search_results = search_web(req.question)
                if search_results and search_results.get("results"):
                    # Format web search results as answer
                    web_answer = "Based on web search:\n\n"
                    for i, result in enumerate(search_results["results"][:3], 1):
                        web_answer += f"{i}. {result.get('title', 'Result')}\n"
                        web_answer += f"   {result.get('content', 'No content available')}\n"
                        web_answer += f"   Source: {result.get('url', 'Unknown')}\n\n"
                    
                    return AskResponse(
                        answer=web_answer,
                        sources=[],
                        model_used="web-search"
                    )
            except Exception as e:
                logger.warning(f"Web search failed: {e}")
        
        if not chunks:
            return AskResponse(
                answer="No relevant information found in the provided documents.",
                sources=[],
                model_used="none"
            )
        
        # Generate answer with Groq
        answer, sources, model_used = answer_with_optional_llm(req.question, chunks)
        
        # Enrich with external search if enabled and we have an answer
        if req.use_search_enrichment and answer:
            try:
                logger.info("Enriching answer with web search")
                enriched = enrich_answer_with_search(req.question, answer, sources)
                if enriched and enriched.get("answer"):
                    answer = enriched["answer"]
                    model_used = f"{model_used}+web-search"
            except Exception as e:
                logger.warning(f"Search enrichment failed: {e}")
        
        # Update metrics
        ASK_COUNT.inc()
        
        logger.info(f"Answered question using {model_used}: {req.question[:50]}...")
        
        # Format sources
        source_citations = [
            SourceCitation(
                document_id=s["document_id"],
                page=s["page"],
                char_start=s["char_start"],
                char_end=s["char_end"],
                text_snippet=s.get("text", "")[:200] if s.get("text") else None
            )
            for s in sources
        ]
        
        return AskResponse(
            answer=answer,
            sources=source_citations,
            model_used=model_used
        )
        
    except Exception as e:
        logger.error(f"Ask failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to answer question: {str(e)}"
        )


@router.get("/stream")
async def ask_stream(
    question: str = Query(..., description="Question to ask"),
    document_ids: Optional[str] = Query(None, description="Comma-separated document IDs"),
    top_k: int = Query(3, ge=1, le=10, description="Number of chunks to retrieve")
):
    """
    Stream answer tokens using Server-Sent Events (SSE)
    
    Returns:
        SSE stream with answer tokens and final sources
    """
    # Parse document IDs
    doc_ids = document_ids.split(",") if document_ids else None
    
    # Retrieve chunks
    chunks = retrieve_top_k(question, doc_ids, top_k=top_k)
    
    if not chunks:
        async def no_answer():
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "error",
                    "content": "No relevant information found."
                })
            }
        
        return EventSourceResponse(no_answer())
    
    async def event_generator():
        try:
            # Get answer
            answer, sources, model_used = answer_with_optional_llm(question, chunks)
            
            # Stream tokens (simulate token-by-token streaming)
            tokens = answer.split()
            for i, token in enumerate(tokens):
                yield {
                    "event": "token",
                    "data": json.dumps({
                        "type": "token",
                        "content": token + (" " if i < len(tokens) - 1 else "")
                    })
                }
                await asyncio.sleep(0.02)  # Simulate streaming delay
            
            # Send sources
            yield {
                "event": "sources",
                "data": json.dumps({
                    "type": "sources",
                    "sources": [
                        {
                            "document_id": s["document_id"],
                            "page": s["page"],
                            "char_start": s["char_start"],
                            "char_end": s["char_end"]
                        }
                        for s in sources
                    ]
                })
            }
            
            # End stream
            yield {
                "event": "done",
                "data": json.dumps({"type": "done"})
            }
            
            # Update metrics
            ASK_COUNT.inc()
            
        except Exception as e:
            logger.error(f"Streaming failed: {str(e)}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "type": "error",
                    "content": str(e)
                })
            }
    
    return EventSourceResponse(event_generator())