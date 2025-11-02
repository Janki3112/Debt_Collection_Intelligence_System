# Debt Collection Intelligence System - Design Document

## 1. Architecture Overview

### System Components
<img width="532" height="471" alt="{019BBBFD-5F99-4E53-BE49-410735C1EA4A}" src="https://github.com/user-attachments/assets/88776ec5-f802-42ad-8b45-b901aedb6a39" />

### Technology Stack
- **Framework**: FastAPI 0.104+
- **Database**: SQLite with async support (aiosqlite)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Vector Store**: FAISS (CPU version)
- **LLM**: OpenAI API (optional, with fallback)
- **PDF Processing**: PyMuPDF (fitz)
- **Metrics**: Prometheus client
- **Containerization**: Docker + Docker Compose

## 2. Data Model

### Database Schema
<img width="416" height="408" alt="{751C08F6-526F-45C8-B7A5-561BB52CBDE1}" src="https://github.com/user-attachments/assets/76c41ff4-2ff2-4152-b290-174a8dae8db9" />


### FAISS Index Structure

<img width="415" height="256" alt="{E5F40600-161B-4C91-A357-0BBC832158ED}" src="https://github.com/user-attachments/assets/23f30d76-b551-44cc-bd39-e802bf13f429" />


## 3. Processing Pipeline

### Ingestion Flow

PDF Upload → Validation → Text Extraction → Page Storage
↓
Chunking (1500 chars, 300 overlap)
↓
Embedding Generation
↓
FAISS Index Update
↓
Webhook Notification

### Q&A Flow (RAG)

Question → Embedding → FAISS Search (top-k) → Context Assembly
↓
LLM Generation (if available)
↓
Answer + Citations

### Audit Flow

Document → Rule Engine → Pattern Matching → Findings
↓
Optional LLM Analysis
↓
Risk Score Calculation

## 4. Key Design Decisions

### Chunking Strategy
- **Size**: 1500 characters per chunk
- **Overlap**: 300 characters
- **Rationale**: Balances context preservation with retrieval granularity

### Embedding Model
- **Model**: all-MiniLM-L6-v2
- **Dimension**: 384
- **Rationale**: Fast, local, good quality for domain

### Retrieval
- **Method**: Cosine similarity via FAISS IndexFlatIP
- **Top-k**: Configurable (default 3)
- **Filtering**: By document_id when specified

### LLM Integration
- **Primary**: OpenAI GPT-3.5-turbo
- **Fallback**: Extractive (concatenated chunks)
- **Rationale**: Cost-effective with graceful degradation

### Rule Engine
- **Approach**: Regex-based deterministic rules
- **Extensibility**: Optional LLM fallback for complex patterns
- **Rationale**: Fast, explainable, consistent

## 5. Security Considerations

### PII Protection
- **Log Redaction**: Automatic PII masking in logs
- **Patterns**: Email, phone, SSN, Aadhaar, credit cards, IPs

### Input Validation
- **File types**: PDF only
- **Size limits**: 50MB default (configurable)
- **Rate limiting**: Configurable per-IP limits

### Webhook Security
- **HMAC Signatures**: Optional secret-based signing
- **Retry Logic**: Exponential backoff
- **Async Execution**: Non-blocking webhook delivery

## 6. Monitoring & Observability

### Metrics (Prometheus)
- Request counts by endpoint/status
- Request duration histograms
- Active request gauge
- Document/page/chunk counters
- LLM call success/failure
- Webhook delivery status

### Health Checks
- `/healthz`: Basic liveness
- `/readyz`: Readiness with dependency checks
- `/metrics`: Prometheus exposition format
- `/metrics/summary`: Human-readable summary

### Logging
- Structured logging with timestamps
- PII redaction
- Request/response logging
- Error tracking with stack traces
- Rotating file handlers (10MB, 5 backups)

## 7. Trade-offs & Limitations

### Current Limitations
1. **Scale**: Single-node, in-process FAISS (not distributed)
2. **Database**: SQLite (suitable for <1M documents)
3. **Concurrency**: Limited by GIL for CPU-bound operations
4. **Storage**: Local filesystem (no S3/blob storage)

### Future Improvements
1. **Scalability**
   - Migrate to PostgreSQL for production
   - Use Qdrant/Weaviate for distributed vector search
   - Add Redis for caching
   - Implement proper task queue (Celery/RQ)

2. **Accuracy**
   - Fine-tune embeddings on legal domain
   - Add re-ranker for retrieved chunks
   - Implement citation verification
   - Add confidence scoring

3. **Features**
   - OCR for scanned PDFs
   - Multi-language support
   - Document comparison
   - Version tracking
   - Collaborative annotations

## 8. Deployment

### Local Development
```bash
make up        # Start with Docker Compose
make test      # Run test suite
make logs      # View logs
```

### Production Checklist
- [ ] Set strong SECRET_KEY
- [ ] Configure HTTPS/TLS
- [ ] Set up proper PostgreSQL
- [ ] Enable authentication/authorization
- [ ] Configure rate limiting
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Configure log aggregation
- [ ] Set up automated backups
- [ ] Review security headers
- [ ] Load test and tune

## 9. Testing Strategy

### Unit Tests
- PDF extraction
- Chunking logic
- Rule engine patterns
- PII redaction

### Integration Tests
- End-to-end ingest → extract → ask → audit
- Database operations
- FAISS index operations
- Webhook delivery

### Performance Tests
- Large document handling (>100 pages)
- Concurrent requests
- Memory usage under load
- Index rebuild time

---

**Document Version**: 1.0
**Last Updated**: 2024
**Author**: Contract Intelligence Team
