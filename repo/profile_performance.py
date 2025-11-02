"""
Performance profiling for Debt Collection Intelligence System
Run this to identify bottlenecks
"""
import time
import asyncio
from app.core.retriever import retrieve_top_k
from app.core.llm_client import answer_with_optional_llm
from app.core.embeddings import embed_text, search_index

def profile_operation(name, func, *args, **kwargs):
    """Time an operation"""
    start = time.time()
    result = func(*args, **kwargs)
    duration = time.time() - start
    print(f"⏱️  {name}: {duration:.3f}s")
    return result, duration

async def profile_ask_endpoint():
    """Profile a complete ask request"""
    print("=" * 60)
    print("🔍 PERFORMANCE PROFILING")
    print("=" * 60)
    
    question = "What are the confidentiality obligations?"
    doc_id = "497512e6-8dc6-40fe-be6a-31fdfac37f86"
    
    total_start = time.time()
    
    # 1. Embedding generation
    print("\n1️⃣ EMBEDDING GENERATION")
    embedding, emb_time = profile_operation(
        "Generate query embedding",
        embed_text,
        question
    )
    
    # 2. FAISS search
    print("\n2️⃣ VECTOR SEARCH")
    chunks, search_time = profile_operation(
        "FAISS index search",
        retrieve_top_k,
        question,
        [doc_id],
        5
    )
    
    print(f"   Retrieved {len(chunks)} chunks")
    
    # 3. LLM call
    if chunks:
        print("\n3️⃣ LLM GENERATION")
        llm_start = time.time()
        answer, sources, model = answer_with_optional_llm(question, chunks)
        llm_time = time.time() - llm_start
        print(f"⏱️  LLM call: {llm_time:.3f}s")
        print(f"   Model: {model}")
        print(f"   Answer length: {len(answer)} chars")
    
    total_time = time.time() - total_start
    
    print("\n" + "=" * 60)
    print("📊 BREAKDOWN")
    print("=" * 60)
    print(f"Embedding:      {emb_time:.3f}s  ({emb_time/total_time*100:.1f}%)")
    print(f"Search:         {search_time:.3f}s  ({search_time/total_time*100:.1f}%)")
    if chunks:
        print(f"LLM:            {llm_time:.3f}s  ({llm_time/total_time*100:.1f}%)")
    print(f"-" * 60)
    print(f"TOTAL:          {total_time:.3f}s")
    print("=" * 60)
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS")
    if emb_time > 0.5:
        print("[WARN]  Embeddings are slow (>500ms)")
        print("   → Use faster model: all-MiniLM-L6-v2 → paraphrase-MiniLM-L3-v2")
        print("   → Or switch to OpenAI embeddings API")
    
    if search_time > 0.1:
        print("[WARN]  FAISS search is slow (>100ms)")
        print("   → Index might be too large")
        print("   → Consider using IVF index instead of Flat")
    
    if chunks and llm_time > 3:
        print("[WARN]  LLM calls are slow (>3s)")
        print("   → Reduce context size")
        print("   → Use faster model: llama-3.1-8b-instant")
        print("   → Check network latency")

if __name__ == "__main__":
    asyncio.run(profile_ask_endpoint())