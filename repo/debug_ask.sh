#!/bin/bash
# Debug script to test single document_id filtering

BASE_URL="http://localhost:8000"

# Get the most recent document
echo " Fetching most recent document..."
doc_id=$(curl -s "$BASE_URL/ingest/documents" | jq -r '.documents[0].id')
echo "Document ID: $doc_id"

# Test 1: Ask with document_id (singular)
echo -e "\n Test 1: Using 'document_id' (singular)"
curl -s -X POST "$BASE_URL/ask" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$doc_id\",\"question\":\"What is this document about?\"}" | jq .

# Test 2: Ask with document_ids (array)
echo -e "\n Test 2: Using 'document_ids' (array)"
curl -s -X POST "$BASE_URL/ask" \
  -H "Content-Type: application/json" \
  -d "{\"document_ids\":[\"$doc_id\"],\"question\":\"What is this document about?\"}" | jq .

# Test 3: Ask WITHOUT filter (search all documents)
echo -e "\n Test 3: No document filter (search all)"
curl -s -X POST "$BASE_URL/ask" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"What is this document about?\"}" | jq .

echo -e "\n✔ Check your server logs for detailed filtering information"
echo "Look for lines containing ' Filtering' to see what's happening"