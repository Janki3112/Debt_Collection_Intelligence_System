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
- (Optional) GROQ API key for enhanced Q&A
