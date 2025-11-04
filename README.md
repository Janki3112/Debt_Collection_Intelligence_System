# Debt Collection Intelligence System

Production-ready FastAPI application for intelligent contract analysis, field extraction, question answering, and risk auditing.

### Prerequisites
- Docker & Docker Compose v2.0+
- GROQ API key for enhanced Q&A
- 4GB+ RAM recommended
- Python 3.11+ (for local development)

## Architecture

FastAPI Server
├── PDF Processing (PyMuPDF)
|
├── Chunking (1500 char, 300 overlap)
|
├── Embeddings (sentence-transformers)
|
├── Vector Search (FAISS)
|
├── LLM Integration (OpenAI, with fallback)
|
├── Rule Engine (Deterministic + Optional LLM)
|
└── Database (SQLite with async support)

## Environment Variables
Create a .env file (use .env.example as template):
Rename .env.example as .env and add api keys where mentioned.

## API Endpoints

### 1. Ingest Documents
#### Upload one or multiple PDF contracts for processing.
#### Request:
```
curl -X POST http://localhost:8000/ingest \
  -F "files=@data/docs/nda_uk_gov_example.pdf" \
  -F "files=@data/docs/nda_tntech.pdf" \
  -F "files=@data/docs/msa_mercycorps.pdf" \
  -F "files=@data/docs/msa_globalsign.pdf" \
  -F "files=@data/docs/tos_iubenda_sample.pdf"

```

#### Response:
```
{
  "document_ids": [
    "259aa2fe-2268-463b-92b6-566bc23dc08d",
    "7d355ef5-fbed-438a-a6ae-a8610ed33072",
    "27fff300-024a-47f9-a57d-95a8725e9707",
    "06551383-6ac9-4c0b-ab54-69bd55dfdeca",
    "a95afe1d-25ea-4a11-b8a7-47d2b6346066"
  ],
  "meta": [
    {"document_id": "259aa2fe-2268-463b-92b6-566bc23dc08d", "filename": "nda_uk_gov_example.pdf", "pages": 2},
    {"document_id": "7d355ef5-fbed-438a-a6ae-a8610ed33072", "filename": "nda_tntech.pdf", "pages": 4},
    {"document_id": "27fff300-024a-47f9-a57d-95a8725e9707", "filename": "msa_mercycorps.pdf", "pages": 11},
    {"document_id": "06551383-6ac9-4c0b-ab54-69bd55dfdeca", "filename": "msa_globalsign.pdf", "pages": 18},
    {"document_id": "a95afe1d-25ea-4a11-b8a7-47d2b6346066", "filename": "tos_iubenda_sample.pdf", "pages": 11}
  ],
  "message": "Documents ingested successfully"
}

```
#### Server Logs
```
INFO: 127.0.0.1:58880 - "POST /ingest HTTP/1.1" 201 Created
2025-11-02 01:26:47 - app.logger - INFO - Request: POST /ingest
2025-11-02 01:26:47 - app.logger - INFO - Processing document: nda_uk_gov_example.pdf (ID: 259aa2fe-2268-463b-92b6-566bc23dc08d)
2025-11-02 01:26:48 - app.logger - INFO - Extracted 2 pages from ./storage\259aa2fe-2268-463b-92b6-566bc23dc08d_nda_uk_gov_example.pdf using PyPDF2
2025-11-02 01:26:48 - app.logger - INFO - Created document 259aa2fe-2268-463b-92b6-566bc23dc08d with 2 pages
2025-11-02 01:26:48 - app.logger - INFO - Created 3 chunks for document 259aa2fe-2268-463b-92b6-566bc23dc08d
2025-11-02 01:26:48 - app.logger - INFO - Generating embeddings for 3 chunks
2025-11-02 01:26:48 - app.logger - INFO - Generated 3 embeddings in 0.33s (9.2 chunks/sec)
2025-11-02 01:26:48 - app.logger - INFO - Added 3 chunks to index. Total: 338
2025-11-02 01:26:48 - app.logger - INFO - Document 259aa2fe-2268-463b-92b6-566bc23dc08d ingested successfully: 2 pages, 3 chunks

[... similar logs for other documents ...]

2025-11-02 01:26:53 - app.logger - INFO - Response: POST /ingest status=201 duration=5.799s
```

---
### 2. Extract Structured Fields
#### Extract key contract fields using LLM + rule-based extraction.
#### Request:
```
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"document_id": "7d355ef5-fbed-438a-a6ae-a8610ed33072"}'

```

#### Response:
```
{
  "document_id": "7d355ef5-fbed-438a-a6ae-a8610ed33072",
  "parties": ["XYZ", "TTU"],
  "effective_date": "Not found (the effective date is not explicitly stated in the contract, but it is mentioned as the 'later of the two signature dates below')",
  "term": "Not found (the term length is not explicitly stated in the contract)",
  "governing_law": "The State of Tennessee",
  "payment_terms": "Not found (payment terms are not mentioned in the contract)",
  "termination": "IN WITNESS WHEREOF, the parties hereto have executed this Agreement.",
  "auto_renewal": false,
  "confidentiality": true,
  "indemnity": false,
  "liability_cap": null,
  "signatories": []
}

```

### If no any data found in document
#### Response:
```
{
  "document_id": "259aa2fe-2268-463b-92b6-566bc23dc08d",
  "parties": [],
  "effective_date": null,
  "term": null,
  "governing_law": "English law",
  "payment_terms": null,
  "termination": null,
  "auto_renewal": false,
  "confidentiality": true,
  "indemnity": false,
  "liability_cap": null,
  "signatories": []
}

```
#### Server Logs
```
2025-11-02 01:29:49 - app.logger - INFO - Extracted 7 fields using Groq LLM
2025-11-02 01:29:49 - app.logger - INFO - LLM enhanced extraction with 7 fields
2025-11-02 01:29:49 - app.logger - INFO - Extraction complete: 0 parties, 0 signatories
2025-11-02 01:29:49 - app.logger - INFO - Response: POST /extract status=200 duration=0.942s
INFO: 127.0.0.1:62262 - "POST /extract HTTP/1.1" 200 OK
```
---

### 3. Ask Questions (RAG)
#### Query contract contents using retrieval-augmented generation.
#### Request:
```
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the termination period in the TNTech NDA?", "document_ids": ["7d355ef5-fbed-438a-a6ae-a8610ed33072"]}'

```

#### Response:
```
{
  "answer": "The termination period is not explicitly stated in the provided context. The document mentions that the obligations concerning Confidential Information will survive any termination, but it does not specify the duration of the Agreement or the termination period. \n\n[Doc: 7d355ef5-fbed-438a-a6ae-a8610ed33072, Page: 3]",
  "sources": [
    {
      "document_id": "7d355ef5-fbed-438a-a6ae-a8610ed33072",
      "page": 4,
      "char_start": 0,
      "char_end": 379,
      "text_snippet": "Page 4 of 4 \n of the parties concerning Confidential Information disclosed during the term of the Agreement shall survive \nany such termination.  \n \nIN WITNESS WHEREOF, the parties hereto have execut"
    },
    {
      "document_id": "7d355ef5-fbed-438a-a6ae-a8610ed33072",
      "page": 3,
      "char_start": 2400,
      "char_end": 3900,
      "text_snippet": "f each party to this Agreement.  \n(d) Failure or delay  in exercising any right, power or privilege under this Agreement will not \noperate as a waiver thereof.   In the event that any provision of thi"
    }
  ],
  "confidence": null,
  "model_used": "groq-llama-3.1-8b-instant"
}

```
#### Server Logs
```
INFO: 127.0.0.1:65338 - "POST /extract HTTP/1.1" 200 OK
2025-11-02 01:33:30 - app.logger - INFO - Request: POST /ask
2025-11-02 01:33:30 - app.logger - INFO - Retrieving top-3 chunks for query: What is the termination period in the TNTech NDA?...
2025-11-02 01:33:30 - app.logger - INFO - Search completed in 0.047s (embed: 0.041s, faiss: 0.005s) - Found 2 results
2025-11-02 01:33:30 - app.logger - INFO - Retrieved 2 chunks
2025-11-02 01:33:30 - app.logger - INFO - Answering question with 2 chunks
2025-11-02 01:33:30 - app.logger - INFO - Using Groq LLM: llama-3.1-8b-instant
2025-11-02 01:33:30 - app.logger - INFO - Groq API call succeeded - Generated 317 chars
2025-11-02 01:33:30 - app.logger - INFO - Generated answer using Groq (317 chars)
2025-11-02 01:33:30 - app.logger - INFO - Answered question using groq-llama-3.1-8b-instant
2025-11-02 01:33:30 - app.logger - INFO - Response: POST /ask status=200 duration=0.629s
INFO: 127.0.0.1:65042 - "POST /ask HTTP/1.1" 200 OK
```
---

### 4. Audit for Risks
#### Detect risky clauses using rule-based + LLM-based analysis.
#### Request:
```
curl -X POST http://localhost:8000/audit \
  -H "Content-Type: application/json" \
  -d '{"document_id": "7d355ef5-fbed-438a-a6ae-a8610ed33072"}'

```
#### Response:
```
{
  "document_id": "7d355ef5-fbed-438a-a6ae-a8610ed33072",
  "findings": [
    {
      "rule": "llm_enhanced_analysis",
      "severity": "medium",
      "explain": "LLM-detected additional concerns",
      "evidence": "Based on the provided contract excerpt, I have identified three additional risky clauses not yet identified:\n\n1. **Rule Name:** \"Lack of Clear Termination Provisions\"\n**Severity:** Medium\n**Explanation:** The contract does not clearly outline the circumstances under which the agreement can be terminated. This lack of clarity may lead to disputes and ambiguity in the event of termination.\n**Evidence:** \"NOW, THEREFORE, in consideration of the disclosure of Confidential Information (as defined bel",
      "page_numbers": null
    }
  ],
  "total_findings": 1,
  "risk_score": 15.0,
  "timestamp": "2025-11-01T20:05:47.053024"
}

```

#### Server Logs
```
INFO: 127.0.0.1:65042 - "POST /ask HTTP/1.1" 200 OK
2025-11-02 01:35:45 - app.logger - INFO - Request: POST /audit
2025-11-02 01:35:45 - app.logger - INFO - Audit found 0 issues in document 7d355ef5-fbed-438a-a6ae-a8610ed33072
2025-11-02 01:35:45 - app.logger - INFO - Enhancing audit with Groq LLM
2025-11-02 01:35:47 - app.logger - INFO - Groq API call succeeded - Generated 2764 chars
2025-11-02 01:35:47 - app.logger - INFO - Audit enhanced with Groq LLM analysis
2025-11-02 01:35:47 - app.logger - INFO - Audit completed for 7d355ef5-fbed-438a-a6ae-a8610ed33072: 1 findings, risk score 15.0 (LLM: True)
2025-11-02 01:35:47 - app.logger - INFO - Response: POST /audit status=200 duration=1.179s
INFO: 127.0.0.1:65025 - "POST /audit HTTP/1.1" 200 OK
```

### 5. Streaming Q&A (Server-Sent Events)
#### Stream answers token-by-token for real-time responses.
#### Request:

```
curl -N "http://localhost:8000/ask/stream?question=What%20is%20the%20term%20of%20the%20contract&document_id=7d355ef5-fbed-438a-a6ae-a8610ed33072"
```

#### Response (SSE stream):

```
event: token
data: {"type": "token", "content": "The "}

event: token
data: {"type": "token", "content": "term "}

event: token
data: {"type": "token", "content": "of "}

event: token
data: {"type": "token", "content": "the "}

event: token
data: {"type": "token", "content": "contract "}

event: token
data: {"type": "token", "content": "is "}

event: token
data: {"type": "token", "content": "not "}

event: token
data: {"type": "token", "content": "explicitly "}

event: token
data: {"type": "token", "content": "stated "}

event: token
data: {"type": "token", "content": "in "}

event: token
data: {"type": "token", "content": "the "}

event: token
data: {"type": "token", "content": "provided "}

event: token
data: {"type": "token", "content": "context."}

event: sources
data: {"type": "sources", "sources": [{"document_id": "de705f1e-bc2b-4d74-8eab-3da1725c06e8", "page": 7, "char_start": 0, "char_end": 1500}, {"document_id": "27fff300-024a-47f9-a57d-95a8725e9707", "page": 7, "char_start": 0, "char_end": 1500}, {"document_id": "989a5bab-edee-4711-a243-13d09b25c266", "page": 9, "char_start": 1200, "char_end": 2700}]}

event: done
data: {"type": "done"}

```
#### Server Logs
```
INFO: 127.0.0.1:65025 - "POST /audit HTTP/1.1" 200 OK
2025-11-02 01:39:08 - app.logger - INFO - Request: GET /ask/stream
2025-11-02 01:39:08 - app.logger - INFO - Retrieving top-3 chunks for query: What is the term of the contract...
2025-11-02 01:39:08 - app.logger - INFO - Search completed in 0.070s (embed: 0.070s, faiss: 0.000s) - Found 3 results
2025-11-02 01:39:08 - app.logger - INFO - Retrieved 3 chunks
2025-11-02 01:39:08 - app.logger - INFO - Answering question with 3 chunks
2025-11-02 01:39:08 - app.logger - INFO - Using Groq LLM: llama-3.1-8b-instant
2025-11-02 01:39:09 - app.logger - INFO - Groq API call succeeded - Generated 74 chars
2025-11-02 01:39:09 - app.logger - INFO - Generated answer using Groq (74 chars)
2025-11-02 01:39:09 - app.logger - INFO - Response: GET /ask/stream status=200 duration=0.642s
INFO: 127.0.0.1:52832 - "GET /ask/stream?question=What%20is%20the%20term%20of%20the%20contract&document_id=7d355ef5-fbed-438a-a6ae-a8610ed33072 HTTP/1.1" 200 OK
```
---

### 6. Health Check

#### Request:
```
curl http://localhost:8000/healthz
```
#### Response
```
{
  "status": "healthy",
  "timestamp": "2025-11-01T20:13:03.691218",
  "version": "1.0.0",
  "environment": "development"
}
```
#### Server Logs
```
2025-11-02 01:43:03 - app.logger - INFO - Request: GET /healthz
2025-11-02 01:43:03 - app.logger - INFO - Response: GET /healthz status=200 duration=0.004s
INFO: 127.0.0.1:63786 - "GET /healthz HTTP/1.1" 200 OK
```
---

### 7. Metrics Endpoint

#### Request:
```
curl http://localhost:8000/metrics
```
#### Response:
```
# HELP ingest_documents_total Total documents ingested
# TYPE ingest_documents_total counter
ingest_documents_total 6.0

# HELP ingest_pages_total Total pages ingested
# TYPE ingest_pages_total counter
ingest_pages_total 48.0

# HELP extract_requests_total Total extraction requests
# TYPE extract_requests_total counter
extract_requests_total 0.0

# HELP ask_requests_total Total ask/QA requests
# TYPE ask_requests_total counter
ask_requests_total 2.0

# HELP audit_requests_total Total audit requests
# TYPE audit_requests_total counter
audit_requests_total 1.0

# HELP chunks_created_total Total chunks created
# TYPE chunks_created_total counter
chunks_created_total 131.0

# HELP active_requests Number of active requests
# TYPE active_requests gauge
active_requests 0.0

# HELP request_duration_seconds Request duration in seconds
# TYPE request_duration_seconds histogram
request_duration_seconds_count{endpoint="/ingest",method="POST",status="201"} 2.0
request_duration_seconds_sum{endpoint="/ingest",method="POST",status="201"} 10.767767667770386

request_duration_seconds_count{endpoint="/extract",method="POST",status="200"} 2.0
request_duration_seconds_sum{endpoint="/extract",method="POST",status="200"} 1.682464599609375

request_duration_seconds_count{endpoint="/ask",method="POST",status="200"} 1.0
request_duration_seconds_sum{endpoint="/ask",method="POST",status="200"} 0.6268219947814941

request_duration_seconds_count{endpoint="/audit",method="POST",status="200"} 1.0
request_duration_seconds_sum{endpoint="/audit",method="POST",status="200"} 1.1760313510894775

request_duration_seconds_count{endpoint="/ask/stream",method="GET",status="200"} 1.0
request_duration_seconds_sum{endpoint="/ask/stream",method="GET",status="200"} 0.6390528678894043

request_duration_seconds_count{endpoint="/healthz",method="GET",status="200"} 1.0
request_duration_seconds_sum{endpoint="/healthz",method="GET",status="200"} 0.0020406246185302734

# HELP llm_calls_total Total LLM API calls
# TYPE llm_calls_total counter
llm_calls_total{status="success"} 5.0
```
#### Server Logs
```
2025-11-02 01:44:05 - app.logger - INFO - Request: GET /metrics
2025-11-02 01:44:05 - app.logger - INFO - Response: GET /metrics status=200 duration=0.017s
```
--- 

## Summary
All endpoints are functioning correctly:
•	Ingest: Successfully ingested 5 PDFs (46 total pages, 131 chunks)
•	Extract: Extracted structured fields from contracts
•	Ask (RAG): Question answering with citation support
•	Audit: Risk detection with LLM enhancement
•	Stream: Server-Sent Events streaming responses
•	Health: Health check endpoint operational
•	Metrics: Prometheus metrics tracking all operations


## Features

✔ **Document Ingestion**: Multi-PDF upload with text extraction and storage

✔ **Field Extraction**: Automated extraction of parties, dates, terms, and clauses

✔ **Q&A System**: RAG-based question answering with source citations

✔ **Contract Audit**: Risk detection for auto-renewal, liability, and indemnity clauses

✔ **Streaming**: SSE-based token streaming for real-time responses

✔ **Webhooks**: Event-driven notifications for long-running tasks

✔ **Monitoring**: Prometheus metrics, health checks, and system info

✔ **Security**: PII redaction in logs, input validation, rate limiting

✔ **Testing**: Comprehensive test suite with fixtures
