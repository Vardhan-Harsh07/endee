"""Document chunking utilities."""
import hashlib
import io
import re
import logging

logger = logging.getLogger(__name__)


def extract_text(filename: str, content: bytes) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else "txt"
    if ext in ("txt", "md", "csv", "text"):
        return content.decode("utf-8", errors="replace")
    elif ext == "pdf":
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            return "\n\n".join(p.extract_text() or "" for p in reader.pages)
        except Exception as e:
            logger.warning(f"PDF read failed: {e}")
            return content.decode("utf-8", errors="replace")
    return content.decode("utf-8", errors="replace")


def chunk_text(text: str, source: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    if not text:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) > chunk_size and current:
            cid = hashlib.md5(f"{source}::{len(chunks)}".encode()).hexdigest()[:16]
            chunks.append({
                "id": cid,
                "text": current.strip(),
                "source": source,
                "chunk_index": len(chunks),
            })
            current = current[-overlap:] + " " + sentence if overlap > 0 else sentence
        else:
            current += (" " if current else "") + sentence

    if current.strip():
        cid = hashlib.md5(f"{source}::{len(chunks)}".encode()).hexdigest()[:16]
        chunks.append({
            "id": cid,
            "text": current.strip(),
            "source": source,
            "chunk_index": len(chunks),
        })

    logger.info(f"Chunked '{source}' → {len(chunks)} chunks")
    return chunks
