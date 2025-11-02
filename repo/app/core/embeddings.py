"""
Embedding generation and FAISS index management
OPTIMIZED FOR SPEED: Caching, batching, faster model
"""
import os
import pickle
from typing import List, Dict, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from functools import lru_cache
import hashlib

from app.logger import logger


# Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
INDEX_PATH = "./data/faiss.index"
META_PATH = "./data/faiss_meta.pkl"

# Performance settings
ENABLE_CACHE = os.getenv("ENABLE_EMBEDDING_CACHE", "true").lower() == "true"
CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "1000"))


# Global variables for index and metadata
_model: Optional[SentenceTransformer] = None
_index: Optional[faiss.IndexFlatL2] = None
_meta: Optional[List[Dict]] = None
_embedding_cache: Dict[str, np.ndarray] = {}


def _get_model() -> SentenceTransformer:
    """Get or initialize embedding model (lazy loading)"""
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        import time
        start = time.time()
        
        _model = SentenceTransformer(EMBEDDING_MODEL)
        
        # OPTIMIZATION: Set device to CPU explicitly (or cuda if available)
        import torch
        if torch.cuda.is_available():
            _model = _model.to('cuda')
            logger.info("✔ Using GPU acceleration")
        else:
            _model = _model.to('cpu')
            logger.info("ℹ️ Using CPU (consider GPU for faster embeddings)")
        
        load_time = time.time() - start
        logger.info(f"Embedding model loaded in {load_time:.2f}s")
    return _model


def _ensure_index():
    """Ensure FAISS index is loaded or initialized"""
    global _index, _meta
    
    if _index is not None and _meta is not None:
        return
    
    os.makedirs("./data", exist_ok=True)
    
    # Try to load existing index
    if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
        try:
            logger.info("Loading existing FAISS index")
            import time
            start = time.time()
            
            _index = faiss.read_index(INDEX_PATH)
            
            with open(META_PATH, 'rb') as f:
                _meta = pickle.load(f)
            
            load_time = time.time() - start
            logger.info(f"Loaded FAISS index with {_index.ntotal} vectors in {load_time:.2f}s")
            return
        except Exception as e:
            logger.warning(f"Failed to load existing index: {e}")
    
    # Create new index
    logger.info("Creating new FAISS index")
    model = _get_model()
    dimension = model.get_sentence_embedding_dimension()
    _index = faiss.IndexFlatL2(dimension)
    _meta = []
    logger.info(f"Created new FAISS index with dimension {dimension}")


def _hash_text(text: str) -> str:
    """Generate hash for text (for caching)"""
    return hashlib.md5(text.encode()).hexdigest()


def embed_texts(texts: List[str], use_cache: bool = True) -> np.ndarray:
    """
    Generate embeddings for texts with caching
    
    Args:
        texts: List of text strings
        use_cache: Whether to use cache (default: True)
        
    Returns:
        Numpy array of embeddings
    """
    global _embedding_cache
    
    if not texts:
        return np.array([])
    
    model = _get_model()
    
    # OPTIMIZATION: Check cache first
    if use_cache and ENABLE_CACHE and len(texts) == 1:
        text_hash = _hash_text(texts[0])
        if text_hash in _embedding_cache:
            logger.debug("✔ Cache hit for embedding")
            return _embedding_cache[text_hash].reshape(1, -1)
    
    # Generate embeddings
    import time
    start = time.time()
    
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
        batch_size=32,  # OPTIMIZATION: Batch processing
        normalize_embeddings=False  # OPTIMIZATION: Skip normalization if not needed
    )
    
    embed_time = time.time() - start
    logger.debug(f"Generated {len(texts)} embeddings in {embed_time:.3f}s ({len(texts)/embed_time:.1f} texts/sec)")
    
    # OPTIMIZATION: Cache single queries
    if use_cache and ENABLE_CACHE and len(texts) == 1:
        text_hash = _hash_text(texts[0])
        
        # Limit cache size
        if len(_embedding_cache) >= CACHE_SIZE:
            # Remove oldest entry (simple FIFO)
            _embedding_cache.pop(next(iter(_embedding_cache)))
        
        _embedding_cache[text_hash] = embeddings[0]
        logger.debug(f"Cached embedding (cache size: {len(_embedding_cache)})")
    
    return embeddings


def embed_text(text: str) -> np.ndarray:
    """
    Generate embedding for a single text (with caching)
    
    Args:
        text: Text string
        
    Returns:
        Numpy array embedding
    """
    return embed_texts([text])[0]


def ensure_index_and_add(chunks: List[Dict[str, Any]]):
    """
    Add chunks to FAISS index
    
    Args:
        chunks: List of chunk dicts with 'text' and metadata
    """
    global _index, _meta
    
    if not chunks:
        return
    
    _ensure_index()
    
    # Extract texts
    texts = [chunk["text"] for chunk in chunks]
    
    # Generate embeddings (no cache for bulk operations)
    logger.info(f"Generating embeddings for {len(texts)} chunks")
    import time
    start = time.time()
    
    embeddings = embed_texts(texts, use_cache=False)
    
    embed_time = time.time() - start
    logger.info(f"Generated {len(texts)} embeddings in {embed_time:.2f}s ({len(texts)/embed_time:.1f} chunks/sec)")
    
    # Add to index
    _index.add(embeddings.astype('float32'))
    
    # Store metadata
    for chunk in chunks:
        _meta.append({
            "chunk_id": chunk.get("chunk_id"),
            "document_id": chunk["document_id"],
            "page_no": chunk["page_no"],
            "char_start": chunk["char_start"],
            "char_end": chunk["char_end"],
            "text": chunk["text"]
        })
    
    # Save index and metadata
    _save_index()
    
    logger.info(f"Added {len(chunks)} chunks to index. Total: {_index.ntotal}")


def search_index(
    query: str,
    top_k: int = 5,
    document_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Search FAISS index for similar chunks
    OPTIMIZED: Uses embedding cache for repeated queries
    
    Args:
        query: Query text
        top_k: Number of results to return
        document_ids: Optional filter by document IDs
        
    Returns:
        List of matching chunks with metadata
    """
    import time
    search_start = time.time()
    
    _ensure_index()
    
    if _index.ntotal == 0:
        logger.warning("FAISS index is empty")
        return []
    
    # Generate query embedding (with caching)
    embed_start = time.time()
    query_embedding = embed_texts([query], use_cache=True)
    embed_time = time.time() - embed_start
    logger.debug(f"Query embedding: {embed_time:.3f}s")
    
    # Search index (retrieve more if filtering by document_ids)
    search_k = min(top_k * 10 if document_ids else top_k, _index.ntotal)
    
    faiss_start = time.time()
    distances, indices = _index.search(query_embedding.astype('float32'), search_k)
    faiss_time = time.time() - faiss_start
    logger.debug(f"FAISS search: {faiss_time:.3f}s")
    
    # Collect results
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:  # Invalid index
            continue
        
        if idx >= len(_meta):
            logger.warning(f"Index {idx} out of range for metadata")
            continue
        
        chunk_meta = _meta[idx].copy()
        chunk_meta["score"] = float(dist)
        
        # Filter by document_ids if provided
        if document_ids and chunk_meta["document_id"] not in document_ids:
            continue
        
        results.append(chunk_meta)
        
        if len(results) >= top_k:
            break
    
    search_time = time.time() - search_start
    logger.info(f"Search completed in {search_time:.3f}s (embed: {embed_time:.3f}s, faiss: {faiss_time:.3f}s) - Found {len(results)} results")
    
    return results


def _save_index():
    """Save FAISS index and metadata to disk"""
    try:
        faiss.write_index(_index, INDEX_PATH)
        
        with open(META_PATH, 'wb') as f:
            pickle.dump(_meta, f)
        
        logger.debug("FAISS index saved successfully")
    except Exception as e:
        logger.error(f"Failed to save FAISS index: {e}")


def clear_cache():
    """Clear embedding cache"""
    global _embedding_cache
    _embedding_cache.clear()
    logger.info("Embedding cache cleared")


def get_index_stats() -> Dict[str, Any]:
    """Get statistics about the FAISS index"""
    _ensure_index()
    
    return {
        "total_vectors": _index.ntotal,
        "dimension": _index.d,
        "index_type": type(_index).__name__,
        "cache_size": len(_embedding_cache),
        "cache_enabled": ENABLE_CACHE
    }


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return {
        "cache_enabled": ENABLE_CACHE,
        "cache_size": len(_embedding_cache),
        "max_cache_size": CACHE_SIZE
    }