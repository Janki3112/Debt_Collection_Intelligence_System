#!/usr/bin/env python
"""
Inspect FAISS index to debug document_id matching issues
"""
import pickle
import sys
from collections import Counter

# Load FAISS metadata
try:
    with open("./data/faiss_meta.pkl", "rb") as f:
        meta = pickle.load(f)
except FileNotFoundError:
    print("[Error] FAISS metadata file not found at ./data/faiss_meta.pkl")
    sys.exit(1)

print(f"📊 FAISS Index Statistics")
print("=" * 60)
print(f"Total chunks: {len(meta)}")
print()

# Get unique document IDs
doc_ids = [chunk.get("document_id") for chunk in meta if chunk.get("document_id")]
doc_counter = Counter(doc_ids)

print(f"[DOC] Documents in FAISS index: {len(doc_counter)}")
print()

# Show document IDs and their chunk counts
print("Document IDs with chunk counts:")
print("-" * 60)
for doc_id, count in doc_counter.most_common():
    print(f"  {doc_id}: {count} chunks")

print()
print("=" * 60)

# Check most recent chunks (last 5)
print("\nLast 5 chunks added to index:")
print("-" * 60)
for i, chunk in enumerate(meta[-5:], 1):
    print(f"\nChunk {len(meta) - 5 + i}:")
    print(f"  document_id: {chunk.get('document_id')}")
    print(f"  page: {chunk.get('page_no')} (also as 'page': {chunk.get('page')})")
    print(f"  text preview: {chunk.get('text', '')[:100]}...")

print()
print("=" * 60)

# Check if specific document exists
if len(sys.argv) > 1:
    search_doc_id = sys.argv[1]
    print(f"\n🔎 Searching for document: {search_doc_id}")
    print("-" * 60)
    
    matching_chunks = [chunk for chunk in meta if chunk.get('document_id') == search_doc_id]
    
    if matching_chunks:
        print(f"✔ Found {len(matching_chunks)} chunks for this document")
        for i, chunk in enumerate(matching_chunks[:3], 1):
            print(f"\nChunk {i}:")
            print(f"  page: {chunk.get('page_no')}")
            print(f"  text: {chunk.get('text', '')[:150]}...")
    else:
        print(f"[Error] No chunks found for document: {search_doc_id}")
        print(f"\nDocument IDs in index (first 10):")
        for doc_id in list(doc_counter.keys())[:10]:
            print(f"  - {doc_id}")