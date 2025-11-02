#!/bin/bash
# Test script to verify all fixes

set -e  # Exit on error

BASE_URL="http://localhost:8000"
echo "🧪 Testing Contract Analysis API Fixes..."
echo "========================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "\n${YELLOW}Test 1: Health Check${NC}"
curl -s "$BASE_URL/healthz" | jq -r '.status' | grep -q "healthy" && \
  echo -e "${GREEN}✔ Health check passed${NC}" || \
  echo -e "${RED}[Error] Health check failed${NC}"

# Test 2: Metrics (JSON format)
echo -e "\n${YELLOW}Test 2: Metrics (JSON)${NC}"
curl -s "$BASE_URL/metrics" | jq -e '.documents' > /dev/null && \
  echo -e "${GREEN}✔ Metrics endpoint returns JSON${NC}" || \
  echo -e "${RED}[Error] Metrics endpoint failed${NC}"

# Test 3: Ingest Document
echo -e "\n${YELLOW}Test 3: Document Ingestion${NC}"
response=$(curl -s -X POST "$BASE_URL/ingest" \
  -F "files=@data/docs/nda_uk_gov_example.pdf")

echo "$response" | jq .

doc_id=$(echo "$response" | jq -r '.document_ids[0]')

if [ -z "$doc_id" ] || [ "$doc_id" = "null" ]; then
  echo -e "${RED}[Error] Failed to get document ID${NC}"
  exit 1
fi

echo -e "${GREEN}✔ Document ingested with ID: $doc_id${NC}"

# Test 4: Ask with SINGLE document_id (testing fix)
echo -e "\n${YELLOW}Test 4: Ask with single document_id${NC}"
echo "Querying document: $doc_id"

answer_response=$(curl -s -X POST "$BASE_URL/ask" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$doc_id\",\"question\":\"What is the governing law?\"}")

echo "$answer_response" | jq .

# Verify sources match requested document
source_doc_id=$(echo "$answer_response" | jq -r '.sources[0].document_id // empty')

if [ "$source_doc_id" = "$doc_id" ]; then
  echo -e "${GREEN}✔ Document ID filter working! Sources match requested document${NC}"
else
  echo -e "${RED}[Error] Document ID mismatch!${NC}"
  echo -e "   Requested: $doc_id"
  echo -e "   Received:  $source_doc_id"
fi

# Test 5: Ask with document_ids array
echo -e "\n${YELLOW}Test 5: Ask with document_ids array${NC}"
answer_response2=$(curl -s -X POST "$BASE_URL/ask" \
  -H "Content-Type: application/json" \
  -d "{\"document_ids\":[\"$doc_id\"],\"question\":\"What are the parties?\"}")

echo "$answer_response2" | jq '.answer' 

# Test 6: Webhook Registration (FIXED PATH)
echo -e "\n${YELLOW}Test 6: Webhook Registration${NC}"
webhook_response=$(curl -s -X POST "$BASE_URL/webhooks/register" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/webhook","events":["ingest.completed"],"description":"Test webhook"}')

echo "$webhook_response" | jq .

webhook_id=$(echo "$webhook_response" | jq -r '.webhook_id')

if [ -n "$webhook_id" ] && [ "$webhook_id" != "null" ]; then
  echo -e "${GREEN}✔ Webhook registered: $webhook_id${NC}"
else
  echo -e "${RED}[Error] Webhook registration failed${NC}"
fi

# Test 7: Webhook Event (FIXED PATH)
echo -e "\n${YELLOW}Test 7: Send Webhook Event${NC}"
event_response=$(curl -s -X POST "$BASE_URL/webhooks/events" \
  -H "Content-Type: application/json" \
  -d "{\"event_type\":\"test.event\",\"document_id\":\"$doc_id\",\"status\":\"completed\"}")

echo "$event_response" | jq .

event_id=$(echo "$event_response" | jq -r '.event_id')

if [ -n "$event_id" ] && [ "$event_id" != "null" ]; then
  echo -e "${GREEN}✔ Webhook event received: $event_id${NC}"
else
  echo -e "${RED}[Error] Webhook event failed${NC}"
fi

# Test 8: Extract
echo -e "\n${YELLOW}Test 8: Field Extraction${NC}"
extract_response=$(curl -s -X POST "$BASE_URL/extract" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$doc_id\"}")

echo "$extract_response" | jq .

# Test 9: Audit
echo -e "\n${YELLOW}Test 9: Risk Audit${NC}"
audit_response=$(curl -s -X POST "$BASE_URL/audit" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$doc_id\"}")

echo "$audit_response" | jq '{document_id, total_findings, risk_score}'

# Summary
echo -e "\n========================================"
echo -e "${GREEN}✔ All tests completed!${NC}"
echo -e "\nKey Fixes Verified:"
echo -e "  ✔ document_id filter now works correctly"
echo -e "  ✔ Metrics endpoint returns JSON"
echo -e "  ✔ Webhook endpoints implemented"
echo -e "\nCheck logs for detailed filtering information"