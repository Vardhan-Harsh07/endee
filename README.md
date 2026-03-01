# 🔍 EndeeSearch — Semantic Search Engine powered by Endee

A **semantic search engine** that lets users upload documents and search them by **meaning** rather than exact keywords. Built with **[Endee](https://github.com/endee-io/endee)** as the high-performance vector database.

Unlike traditional keyword search (which matches exact words), semantic search understands that *"global warming effects"* is related to *"climate change impacts"* — even when the words don't match.

---

## 🧩 Problem Statement

Traditional search engines rely on keyword matching, missing results where the meaning is the same but the words differ. Semantic search solves this by converting text into vector embeddings and using similarity search to find relevant content based on meaning.

**EndeeSearch** demonstrates this using Endee's vector database for fast, accurate similarity search.

---

## 🏗️ System Design

```
┌────────────┐       ┌───────────────┐       ┌──────────────┐
│   User     │──────▶│  FastAPI App   │──────▶│    Endee     │
│ (Browser)  │◀──────│  (Python)     │◀──────│  Vector DB   │
└────────────┘       └───────┬───────┘       │  (Port 8080) │
                             │               └──────────────┘
                    ┌────────▼────────┐
                    │  Sentence       │
                    │  Transformers   │
                    │  (all-MiniLM)   │
                    └─────────────────┘
```

### Flow

**Indexing:** Document → Chunk into segments → Embed each chunk (384-dim vectors) → Store in Endee

**Searching:** Query → Embed query → Endee finds nearest vectors → Return ranked results

---

## 🔧 How Endee Is Used

Endee serves as the **vector storage and similarity search engine**. All API calls verified from Endee source code (`src/main.cpp`):

| Operation | Endee API | Parameters |
|-----------|-----------|------------|
| Create Index | `POST /api/v1/index/create` | `index_name`, `dim`, `space_type` |
| Insert Vectors | `POST /api/v1/index/{name}/vector/insert` | Array of `{id, values, meta}` |
| Search | `POST /api/v1/index/{name}/search` | `vector`, `k` |
| List Indexes | `GET /api/v1/index/list` | — |
| Delete Index | `DELETE /api/v1/index/{name}/delete` | — |

### Why Endee?

- **Sub-5ms search latency** — ideal for interactive search
- **Handles up to 1B vectors** on a single node
- **Low memory footprint** — runs on modest hardware
- **HNSW indexing** with configurable parameters
- **Open source** under Apache 2.0

---

## 📁 Project Structure

```
├── app/
│   ├── main.py            # FastAPI application
│   ├── endee_client.py    # Endee REST API client
│   ├── embeddings.py      # Sentence-transformers embeddings
│   ├── chunker.py         # Document chunking
│   └── config.py          # Configuration
├── data/sample_docs/      # Sample documents
├── templates/index.html   # Web UI (single file)
├── ingest.py              # Bulk ingestion script
├── requirements.txt       # Python dependencies
├── .env.example           # Environment template
└── README.md
```

---

## 🚀 Setup & Running

### Prerequisites
- **Python 3.10+**
- **Docker** (for running Endee)

### Step 1: Start Endee

```bash
docker run -d -p 8080:8080 -v endee-data:/data --name endee-server endeeio/endee-server:latest
```

### Step 2: Install & Run

```bash
# Clone your fork
git clone https://github.com/<your-username>/endee.git
cd endee

# Create virtual environment
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Copy config
cp .env.example .env

# Start the app
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 3: Use It

1. Open **http://localhost:8000**
2. Upload documents (drag & drop or browse)
3. Search by meaning!

Or ingest sample docs:
```bash
python ingest.py
```

### API Examples

```bash
# Health check
curl http://localhost:8000/api/health

# Upload document
curl -X POST http://localhost:8000/api/upload -F "file=@data/sample_docs/ai_overview.txt"

# Semantic search
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how do neural networks learn?"}'
```

---

## ⚙️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ENDEE_URL` | `http://localhost:8080` | Endee server URL |
| `ENDEE_AUTH_TOKEN` | `` | Auth token (if enabled) |
| `INDEX_NAME` | `semantic_search` | Vector index name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Embedding model (384 dimensions) |
| `TOP_K` | `5` | Default results count |
| `CHUNK_SIZE` | `500` | Characters per chunk |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |

---

## 📝 License

Built on [Endee](https://github.com/endee-io/endee), licensed under [Apache 2.0](LICENSE).
