#!/bin/bash
# Verify if a document has chunks in the FAISS index

BASE_URL="http://localhost:8000"

echo "🔍 Checking FAISS index for specific document..."

# Get the most recent document
doc_id=$(curl -s "$BASE_URL/ingest/documents" | jq -r '.documents[0].id')
echo "Document ID: $doc_id"

# Get document details
echo -e "\n[DOC] Document details:"
curl -s "$BASE_URL/ingest/documents/$doc_id" | jq '{id, filename, page_count}'

# Try to search WITHOUT filter to see if ANY chunks are returned
echo -e "\n🔍 Test 1: Search ALL documents (no filter)"
result=$(curl -s -X POST "$BASE_URL/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is this document about?","top_k":10}')

echo "$result" | jq '{answer: (.answer[:100] + "..."), source_count: (.sources | length), source_docs: [.sources[].document_id] | unique}'

# Try WITH the specific document filter
echo -e "\n🔍 Test 2: Search with document_id filter"
result=$(curl -s -X POST "$BASE_URL/ask" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$doc_id\",\"question\":\"What is this document about?\",\"top_k\":10}")

echo "$result" | jq '{answer: (.answer[:100] + "..."), source_count: (.sources | length)}'

# Ingest a FRESH document to test
echo -e "\n📥 Ingesting a fresh document for testing..."
fresh_response=$(curl -s -X POST "$BASE_URL/ingest" \
  -F "files=@data/docs/nda_uk_gov_example.pdf")

fresh_id=$(echo "$fresh_response" | jq -r '.document_ids[0]')
echo "Fresh document ID: $fresh_id"

# Wait a moment for indexing
sleep 2

# Test the fresh document
echo -e "\n🔍 Test 3: Search the FRESH document"
result=$(curl -s -X POST "$BASE_URL/ask" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$fresh_id\",\"question\":\"What is the governing law?\",\"top_k\":5}")

echo "$result" | jq '.'

echo -e "\n✔ If Test 3 returns sources, the filtering works!"
echo "If not, check server logs for filtering messages"