"""
Embedding generation and FAISS index management
OPTIMIZED FOR SPEED: Caching, batching, and fast model loading.
FIXED: Better document filtering with detailed logging
"""

import os
import pickle
import hashlib
import numpy as np
import faiss
from typing import List, Dict, Any, Optional
from functools import lru_cache
from sentence_transformers import SentenceTransformer

from app.logger import logger


# ==========================================
# Configuration
# ==========================================
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-MiniLM-L3-v2")
INDEX_PATH = "./data/faiss.index"
META_PATH = "./data/faiss_meta.pkl"

# Performance settings
ENABLE_CACHE = os.getenv("ENABLE_EMBEDDING_CACHE", "true").lower() == "true"
CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "1000"))


# ==========================================
# Global Variables
# ==========================================
_model: Optional[SentenceTransformer] = None
_index: Optional[faiss.IndexFlatL2] = None
_meta: Optional[List[Dict]] = None
_embedding_cache: Dict[str, np.ndarray] = {}


# ==========================================
# Model Loading
# ==========================================
def _get_model() -> SentenceTransformer:
    """Get or initialize embedding model (lazy loading)."""
    global _model

    if _model is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        import time
        start = time.time()

        _model = SentenceTransformer(EMBEDDING_MODEL)

        # Optimization: use GPU if available
        import torch
        if torch.cuda.is_available():
            _model = _model.to("cuda")
            logger.info("✔ Using GPU acceleration for embeddings")
        else:
            _model = _model.to("cpu")
            logger.info("ℹ Using CPU (GPU recommended for speed)")

        load_time = time.time() - start
        logger.info(f"Embedding model loaded in {load_time:.2f}s")

    return _model


# ==========================================
# Index Handling
# ==========================================
def _ensure_index():
    """Ensure FAISS index and metadata are loaded or initialized."""
    global _index, _meta

    if _index is not None and _meta is not None:
        return

    os.makedirs("./data", exist_ok=True)

    # Try loading existing index
    if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
        try:
            import time
            start = time.time()

            logger.info("Loading existing FAISS index...")
            _index = faiss.read_index(INDEX_PATH)
            with open(META_PATH, "rb") as f:
                _meta = pickle.load(f)

            load_time = time.time() - start
            logger.info(f"Loaded FAISS index with {_index.ntotal} vectors in {load_time:.2f}s")
            return
        except Exception as e:
            logger.warning(f"Failed to load existing index: {e}")

    # Create new index
    logger.info("Creating new FAISS index from scratch")
    model = _get_model()
    dimension = model.get_sentence_embedding_dimension()
    _index = faiss.IndexFlatL2(dimension)
    _meta = []
    logger.info(f"Initialized new FAISS index (dimension={dimension})")


# ==========================================
# Embedding Utilities
# ==========================================
def _hash_text(text: str) -> str:
    """Generate MD5 hash for text (used in caching)."""
    return hashlib.md5(text.encode()).hexdigest()


def embed_texts(texts: List[str], use_cache: bool = True) -> np.ndarray:
    """Generate embeddings for a list of texts (with caching)."""
    global _embedding_cache

    if not texts:
        return np.array([])

    model = _get_model()

    # Cache optimization: only single-text queries
    if use_cache and ENABLE_CACHE and len(texts) == 1:
        text_hash = _hash_text(texts[0])
        if text_hash in _embedding_cache:
            logger.debug("✔ Cache hit for embedding")
            return _embedding_cache[text_hash].reshape(1, -1)

    import time
    start = time.time()

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
        batch_size=32,  # Batch optimization
        normalize_embeddings=False,
    )

    elapsed = time.time() - start
    logger.info(f"Generated {len(texts)} embeddings in {elapsed:.2f}s ({len(texts)/elapsed:.1f}/s)")

    # Cache single queries
    if use_cache and ENABLE_CACHE and len(texts) == 1:
        text_hash = _hash_text(texts[0])
        if len(_embedding_cache) >= CACHE_SIZE:
            _embedding_cache.pop(next(iter(_embedding_cache)))  # Simple FIFO eviction
        _embedding_cache[text_hash] = embeddings[0]
        logger.debug(f"Cached embedding (cache size={len(_embedding_cache)})")

    return embeddings


def embed_text(text: str) -> np.ndarray:
    """Generate embedding for a single text (wrapper)."""
    return embed_texts([text])[0]


# ==========================================
# Index Update and Search
# ==========================================
def ensure_index_and_add(chunks: List[Dict[str, Any]]):
    """Add text chunks with metadata to FAISS index."""
    global _index, _meta

    if not chunks:
        return

    _ensure_index()

    texts = [chunk["text"] for chunk in chunks]
    logger.info(f"Generating embeddings for {len(texts)} chunks")

    import time
    start = time.time()
    embeddings = embed_texts(texts, use_cache=False)
    elapsed = time.time() - start

    logger.info(f"Generated {len(texts)} embeddings in {elapsed:.2f}s ({len(texts)/elapsed:.1f}/s)")
    _index.add(embeddings.astype("float32"))

    for chunk in chunks:
        _meta.append({
            "chunk_id": chunk.get("chunk_id"),
            "document_id": chunk.get("document_id"),
            "page_no": chunk.get("page_no"),
            "page": chunk.get("page_no"),  # Add 'page' alias for compatibility
            "char_start": chunk.get("char_start"),
            "char_end": chunk.get("char_end"),
            "text": chunk.get("text"),
        })

    _save_index()
    logger.info(f"Added {len(chunks)} chunks to FAISS index (total={_index.ntotal})")


def search_index(query: str, top_k: int = 5, document_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Search the FAISS index for semantically similar chunks."""
    import time
    search_start = time.time()

    _ensure_index()

    if _index.ntotal == 0:
        logger.warning("FAISS index is empty")
        return []

    query_embedding = embed_texts([query], use_cache=True)

    # Retrieve more results if document filter is applied (to ensure we get enough after filtering)
    search_k = min(top_k * 10 if document_ids else top_k, _index.ntotal)
    
    # Log filtering info
    if document_ids:
        logger.info(f"🔍 Filtering search by document_ids: {document_ids}")
        logger.info(f"   Searching {search_k} candidates to find {top_k} matches")
    
    distances, indices = _index.search(query_embedding.astype("float32"), search_k)

    results = []
    filtered_out = 0
    
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1 or idx >= len(_meta):
            continue
        
        meta = _meta[idx].copy()
        meta["score"] = float(dist)

        # Apply document filter
        if document_ids:
            chunk_doc_id = str(meta["document_id"])  # Ensure string comparison
            search_doc_ids = [str(d) for d in document_ids]  # Ensure all are strings
            
            if chunk_doc_id not in search_doc_ids:
                filtered_out += 1
                if filtered_out <= 3:  # Only log first 3 to avoid spam
                    logger.info(f"[FILTER] Rejected: '{chunk_doc_id}' not in {search_doc_ids}")
                continue
            else:
                logger.info(f"[FILTER] MATCH: doc={chunk_doc_id}, page={meta.get('page_no')}, score={dist:.4f}")

        results.append(meta)
        if len(results) >= top_k:
            break

    if document_ids:
        logger.info(f"✔ Filter results: {len(results)} matched, {filtered_out} filtered out")
    
    total_time = time.time() - search_start
    logger.info(f"Search done in {total_time:.3f}s — found {len(results)} results")
    
    return results


# ==========================================
# Index Persistence
# ==========================================
def _save_index():
    """Persist FAISS index and metadata."""
    try:
        faiss.write_index(_index, INDEX_PATH)
        with open(META_PATH, "wb") as f:
            pickle.dump(_meta, f)
        logger.debug("FAISS index and metadata saved")
    except Exception as e:
        logger.error(f"Failed to save FAISS index: {e}")


# ==========================================
# Cache & Metrics
# ==========================================
def clear_cache():
    """Clear the in-memory embedding cache."""
    global _embedding_cache
    _embedding_cache.clear()
    logger.info("Embedding cache cleared")


def get_index_stats() -> Dict[str, Any]:
    """Return basic statistics about FAISS index."""
    _ensure_index()
    return {
        "total_vectors": _index.ntotal,
        "dimension": _index.d,
        "index_type": type(_index).__name__,
        "cache_size": len(_embedding_cache),
        "cache_enabled": ENABLE_CACHE,
    }


def get_cache_stats() -> Dict[str, Any]:
    """Return embedding cache statistics."""
    return {
        "cache_enabled": ENABLE_CACHE,
        "cache_size": len(_embedding_cache),
        "cache_size": len(_embedding_cache),
        "max_cache_size": CACHE_SIZE,
    }