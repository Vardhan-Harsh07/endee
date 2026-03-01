"""EndeeSearch — Semantic Search Engine powered by Endee Vector Database."""

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config
from .chunker import chunk_text, extract_text
from .embeddings import embed_texts, embed_query, get_model
from .endee_client import EndeeClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Track ingested docs
documents: dict[str, dict] = {}
endee: EndeeClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global endee
    logger.info("Starting EndeeSearch...")
    endee = EndeeClient(config.ENDEE_URL, config.ENDEE_AUTH_TOKEN)
    get_model()  # pre-load embedding model

    try:
        endee.ensure_index(config.INDEX_NAME, config.EMBEDDING_DIM, "cosine")
        logger.info(f"Index '{config.INDEX_NAME}' ready.")
    except Exception as e:
        logger.warning(f"Endee connection issue: {e}. Will retry on first request.")

    logger.info("EndeeSearch is ready!")
    yield
    if endee:
        endee.close()


app = FastAPI(title="EndeeSearch", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

static_dir = Path(__file__).parent.parent / "static"
templates_dir = Path(__file__).parent.parent / "templates"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


class SearchRequest(BaseModel):
    query: str
    top_k: int | None = None


class SearchResult(BaseModel):
    text: str
    source: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int


@app.get("/", response_class=HTMLResponse)
async def home():
    html_path = templates_dir / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text())
    return HTMLResponse("<h1>EndeeSearch</h1><p>Visit <code>/docs</code> for API.</p>")


@app.get("/api/health")
async def health():
    ok = endee.health_check() if endee else False
    return {
        "status": "healthy" if ok else "degraded",
        "endee_connected": ok,
        "model": config.EMBEDDING_MODEL,
        "documents": len(documents),
    }


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and index a document for semantic search."""
    if not endee:
        raise HTTPException(503, "Endee not initialized")

    filename = file.filename or "unknown.txt"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("txt", "md", "pdf", "csv"):
        raise HTTPException(400, f"Unsupported file type: .{ext}")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")

    text = extract_text(filename, content)
    if not text.strip():
        raise HTTPException(400, "Could not extract text")

    # Chunk
    chunks = chunk_text(text, filename, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    if not chunks:
        raise HTTPException(400, "No chunks created")

    # Embed
    chunk_texts = [c["text"] for c in chunks]
    vectors = embed_texts(chunk_texts)

    # Ensure index
    try:
        endee.ensure_index(config.INDEX_NAME, config.EMBEDDING_DIM, "cosine")
    except Exception as e:
        raise HTTPException(503, f"Endee error: {e}")

    # Insert into Endee
    try:
        ids = [c["id"] for c in chunks]
        meta = [{"text": c["text"], "source": c["source"], "chunk_index": c["chunk_index"]} for c in chunks]
        endee.insert_vectors(config.INDEX_NAME, ids, vectors, meta)
    except Exception as e:
        raise HTTPException(500, f"Insert failed: {e}")

    documents[filename] = {"name": filename, "chunks": len(chunks)}
    logger.info(f"Indexed '{filename}': {len(chunks)} chunks")
    return {"message": f"'{filename}' indexed successfully", "chunks": len(chunks)}


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Semantic search across all indexed documents."""
    if not endee:
        raise HTTPException(503, "Endee not initialized")
    if not request.query.strip():
        raise HTTPException(400, "Empty query")

    k = request.top_k or config.TOP_K
    query_vec = embed_query(request.query)

    try:
        raw_results = endee.search(config.INDEX_NAME, query_vec, k)
    except Exception as e:
        raise HTTPException(500, f"Search failed: {e}")

    results = []
    for r in raw_results:
        meta_raw = r.get("meta", r.get("metadata", "{}"))
        if isinstance(meta_raw, str):
            try:
                meta = json.loads(meta_raw)
            except json.JSONDecodeError:
                meta = {"text": meta_raw}
        else:
            meta = meta_raw

        results.append(SearchResult(
            text=meta.get("text", ""),
            source=meta.get("source", "unknown"),
            score=round(r.get("score", r.get("distance", 0)), 4),
        ))

    return SearchResponse(query=request.query, results=results, total=len(results))


@app.get("/api/documents")
async def list_documents():
    return {"documents": list(documents.values())}
