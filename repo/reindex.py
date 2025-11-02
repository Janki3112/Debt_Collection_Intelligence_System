"""
Script to re-index documents and verify embeddings
Run this to fix empty retrieval results
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

from app.db.session import async_session
from app.db.models import Document, Chunk
from app.core.embeddings import create_index
from sqlalchemy import select

async def reindex_all():
    """Re-create FAISS index from database chunks"""
    print("=" * 60)
    print("[Reload] Re-indexing Documents")
    print("=" * 60)
    
    async with async_session() as session:
        # Get all documents
        result = await session.execute(select(Document))
        documents = result.scalars().all()
        
        print(f"\n[DOC] Found {len(documents)} documents:")
        for doc in documents:
            print(f"  - {doc.id}: {doc.filename}")
        
        # Get all chunks
        result = await session.execute(select(Chunk))
        chunks = result.scalars().all()
        
        print(f"\n📦 Found {len(chunks)} chunks in database")
        
        if not chunks:
            print("\n[ERROR] No chunks found! You need to re-upload your documents.")
            print("   Use: POST /ingest/upload to upload a new document")
            return
        
        # Prepare chunks for indexing
        chunk_data = []
        for chunk in chunks:
            chunk_data.append({
                "id": chunk.id,
                "document_id": chunk.document_id,
                "text": chunk.text,
                "page_no": chunk.page_no,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end
            })
        
        print(f"\n🔨 Creating FAISS index with {len(chunk_data)} chunks...")
        
        # Create index
        create_index(chunk_data)
        
        print("\n✔ Index created successfully!")
        print(f"   Index file: ./data/faiss_index.bin")
        print(f"   Metadata file: ./data/faiss_metadata.pkl")
        
        # Verify
        from app.core.embeddings import search_index
        test_query = "payment terms"
        results = search_index(test_query, top_k=3)
        
        print(f"\n🧪 Test search for '{test_query}':")
        print(f"   Found {len(results)} results")
        
        if results:
            print(f"\n   Top result preview:")
            print(f"   - Document: {results[0]['document_id']}")
            print(f"   - Page: {results[0]['page_no']}")
            print(f"   - Text: {results[0]['text'][:100]}...")
            print(f"   - Score: {results[0]['score']:.4f}")
        
        print("\n" + "=" * 60)
        print("✔ Re-indexing Complete!")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(reindex_all())