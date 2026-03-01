#!/usr/bin/env python3
"""Ingest sample documents into EndeeSearch."""
import os, sys
from pathlib import Path
import httpx

URL = os.getenv("APP_URL", "http://localhost:8000")

def main():
    docs_dir = Path(__file__).parent / "data" / "sample_docs"
    files = sorted(f for f in docs_dir.glob("*") if f.suffix in (".txt", ".md", ".pdf", ".csv"))

    if not files:
        print("No sample docs found."); return

    print(f"Ingesting {len(files)} docs into {URL}...\n")
    for f in files:
        print(f"  {f.name} ...", end=" ")
        try:
            resp = httpx.post(f"{URL}/api/upload", files={"file": (f.name, open(f, "rb"))}, timeout=60)
            if resp.status_code == 200:
                d = resp.json(); print(f"✅ {d['chunks']} chunks")
            else:
                print(f"❌ {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"❌ {e}")

    print(f"\n✅ Done! Search at {URL}")

if __name__ == "__main__":
    main()
