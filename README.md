# Debt Collection Intelligence System

Production-ready FastAPI application for intelligent contract analysis, field extraction, question answering, and risk auditing.

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

## Architecture

FastAPI Server
├── PDF Processing (PyMuPDF)
├── Chunking (1500 char, 300 overlap)
├── Embeddings (sentence-transformers)
├── Vector Search (FAISS)
├── LLM Integration (OpenAI, with fallback)
├── Rule Engine (Deterministic + Optional LLM)
└── Database (SQLite with async support)

## Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) OpenAI API key for enhanced Q&A

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd contract-intelligence-api
make setup
```

### 2. Configure Environment
```bash
# Create .env file
cat > .env << EOF
GROQ_API_KEY=your-key-here  # Optional
DB_URL=sqlite+aiosqlite:///./data/data.db
STORAGE_PATH=./storage
EMBEDDING_MODEL=all-MiniLM-L6-v2
LOG_LEVEL=INFO
ENVIRONMENT=development
MAX_FILE_SIZE_MB=50
RATE_LIMIT_ENABLED=true
EOF
```

### 3. Start Services
```bash
make up
```

### 4. Access API
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/healthz
- **Metrics**: http://localhost:8000/metrics

## API Endpoints

### Ingest Documents
```bash
# Upload PDFs
curl -X POST "http://localhost:8000/ingest" \
  -F "files=@contract1.pdf" \
  -F "files=@contract2.pdf" \
  -F "webhook_url=https://your-webhook.com/notify"

# Response
{
  "document_ids": ["uuid1", "uuid2"],
  "meta": [
    {"document_id": "uuid1", "filename": "contract1.pdf", "pages": 5},
    {"document_id": "uuid2", "filename": "contract2.pdf", "pages": 8}
  ],
  "message": "Documents ingested successfully"
}
```

### Extract Fields
```bash
curl -X POST "http://localhost:8000/extract" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "uuid1"}'

# Response
{
  "document_id": "uuid1",
  "parties": ["Alpha Corp", "Beta LLC"],
  "effective_date": "January 1, 2024",
  "term": "12 months",
  "governing_law": "State of California",
  "auto_renewal": true,
  "liability_cap": {"amount": 100000, "currency": "USD"},
  "signatories": [
    {"name": "John Doe", "title": "CEO"}
  ]
}
```

### Ask Questions
```bash
# Standard Q&A
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the termination notice period?",
    "document_ids": ["uuid1"],
    "top_k": 3
  }'

# Streaming Q&A (SSE)
curl -N "http://localhost:8000/ask/stream?question=Who%20are%20the%20parties?&document_ids=uuid1"
```

### Audit Contract
```bash
curl -X POST "http://localhost:8000/audit" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "uuid1",
    "use_llm_fallback": false
  }'

# Response
{
  "document_id": "uuid1",
  "findings": [
    {
      "rule": "auto_renewal_short_notice",
      "severity": "high",
      "explain": "Auto-renewal with only 15 days notice",
      "evidence": "...contract text snippet..."
    }
  ],
  "total_findings": 1,
  "risk_score": 25.0
}
```

### Webhook Management
```bash
# Register webhook
curl -X POST "http://localhost:8000/webhooks/register" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-webhook.com/events",
    "events": ["ingest.completed", "audit.completed"],
    "secret": "your-secret-key"
  }'

# List webhooks
curl "http://localhost:8000/webhooks/list"
```

## Test Sample Contracts

The repository includes 3-5 public contract samples in `/sample_contracts`:

1. **NDA.pdf** - Non-Disclosure Agreement
   - Source: [Example source URL]
   - Use case: Confidentiality testing

2. **MSA.pdf** - Master Service Agreement
   - Source: [Example source URL]
   - Use case: Multi-party, payment terms

3. **SaaS_ToS.pdf** - SaaS Terms of Service
   - Source: [Example source URL]
   - Use case: Auto-renewal, liability caps

*Note: All samples are publicly available templates without proprietary information.*

## Development

### Running Tests
```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
docker-compose exec api pytest tests/test_ingest.py -v
```

### Code Quality
```bash
# Lint
make lint

# Format code
make format
```

### Database Migrations
```bash
# Run migrations
make migrate

# Create new migration
make migrate-create msg="Add new table"
```

### Evaluation
```bash
# Run Q&A evaluation
make eval

# View results
cat eval/results.json
```

## Monitoring

### Metrics
```bash
# Prometheus format
curl http://localhost:8000/metrics

# Human-readable summary
curl http://localhost:8000/metrics/summary
```

**Available Metrics**:
- `http_requests_total`: Total HTTP requests by method/endpoint/status
- `http_request_duration_seconds`: Request duration histogram
- `http_requests_active`: Currently active requests
- `ingest_documents_total`: Total documents ingested
- `ingest_pages_total`: Total pages processed
- `ask_questions_total`: Total questions asked
- `audit_requests_total`: Total audits performed
- `llm_calls_total`: LLM API calls by status
- `webhooks_sent_total`: Webhooks sent by status

### Health Checks
```bash
# Liveness
curl http://localhost:8000/healthz

# Readiness
curl http://localhost:8000/readyz

# System info
curl http://localhost:8000/system
```

### Logs
```bash
# View logs
make logs

# Logs are also written to ./logs/app.log with rotation
tail -f logs/app.log
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_URL` | `sqlite+aiosqlite:///./data/data.db` | Database connection URL |
| `STORAGE_PATH` | `./storage` | PDF storage directory |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `GROQ_API_KEY` | None | OpenAI API key (optional) |
| `GROQ_MODEL` | `llama-3.1-70b-versatile` | OpenAI model to use |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENVIRONMENT` | `development` | Environment name |
| `MAX_FILE_SIZE_MB` | `50` | Max upload size in MB |
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `SECRET_KEY` | Required in prod | Secret key for security |

## Design Decisions & Trade-offs

### Chunking
- **Size**: 1500 characters
- **Overlap**: 300 characters
- **Rationale**: Balances context preservation with retrieval granularity

### Embeddings
- **Model**: all-MiniLM-L6-v2 (384 dimensions)
- **Rationale**: Fast, runs locally, good for legal text
- **Alternative**: Could use larger models for better accuracy

### Vector Store
- **Choice**: FAISS (CPU, in-memory)
- **Rationale**: Simple, fast for small-medium datasets
- **Limitation**: Not distributed, limited to single node
- **Production Alternative**: Qdrant, Weaviate, or Pinecone

### LLM Integration
- **Primary**: OpenAI GPT-3.5-turbo
- **Fallback**: Extractive (concatenated chunks)
- **Rationale**: Cost-effective with graceful degradation
- **Note**: Works without API key using fallback

### Database
- **Choice**: SQLite with async support
- **Rationale**: Simple setup, suitable for < 1M documents
- **Production Alternative**: PostgreSQL for scale

### Rule Engine
- **Approach**: Deterministic regex patterns
- **Rationale**: Fast, explainable, consistent
- **Extension**: Optional LLM fallback for complex patterns

## Security Features

### PII Redaction
Automatically redacts from logs:
- Email addresses
- Phone numbers
- SSNs, Aadhaar numbers
- Credit card numbers
- IP addresses

### Input Validation
- File type restrictions (PDF only)
- Size limits (configurable)
- Content type verification
- Document ID validation

### Rate Limiting
- Per-IP rate limits (configurable)
- Prevents abuse and DoS

### Webhook Security
- HMAC signature verification
- Optional secret-based authentication
- Async non-blocking delivery

## Troubleshooting

### Issue: FAISS index not loading
```bash
# Reload index
curl -X POST http://localhost:8000/reload-index

# Or delete and rebuild
rm data/faiss.index data/faiss_meta.pkl
# Re-ingest documents
```

### Issue: Out of memory
- Reduce `CHUNK_SIZE` in `chunker.py`
- Reduce `top_k` in queries
- Process fewer documents at once

### Issue: Slow embedding generation
- Use smaller embedding model
- Reduce document batch size
- Consider GPU acceleration (use `faiss-gpu`)

### Issue: OpenAI rate limits
- Implement exponential backoff (already included)
- Use fallback mode without LLM
- Upgrade OpenAI tier

## Production Deployment

### Checklist
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set strong `SECRET_KEY`
- [ ] Configure HTTPS/TLS
- [ ] Enable authentication/authorization
- [ ] Set up proper logging aggregation
- [ ] Configure monitoring (Prometheus + Grafana)
- [ ] Set up automated backups
- [ ] Use distributed vector store
- [ ] Implement proper task queue (Celery)
- [ ] Enable CORS properly
- [ ] Review and harden security headers
- [ ] Load test and performance tune
- [ ] Set up CI/CD pipeline
- [ ] Configure secrets management

### Example Production Setup
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  api:
    image: contract-intel:latest
    environment:
      - DB_URL=postgresql+asyncpg://user:pass@db:5432/contracts
      - ENVIRONMENT=production
      - SECRET_KEY=${SECRET_KEY}
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
  
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Code Style
- Follow PEP 8
- Use type hints
- Add docstrings
- Write tests for new features

## License

MIT License - see LICENSE file for details

## Support

- **Documentation**: See `/docs` endpoint
- **Issues**: GitHub Issues
- **Design Doc**: See `DESIGN.md`
- **Prompts**: See `/prompts` directory

## Acknowledgments

- PyMuPDF for PDF processing
- sentence-transformers for embeddings
- FAISS for vector search
- FastAPI for the excellent framework
- OpenAI for LLM capabilities

---

**Version**: 1.0.0
**Status**: Production-Ready
**Last Updated**: 2024