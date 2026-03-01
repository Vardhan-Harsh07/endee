"""
Endee Vector Database Client.
API format verified from src/main.cpp source code.
"""

import json as json_lib
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class EndeeClient:
    """Client for Endee vector database REST API."""

    def __init__(self, base_url: str, auth_token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.client = httpx.Client(timeout=30.0)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = self.auth_token
        return headers

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/v1/{path.lstrip('/')}"

    def health_check(self) -> bool:
        """Check if Endee is reachable."""
        try:
            resp = self.client.get(self._url("index/list"), headers=self._headers())
            return resp.status_code == 200
        except httpx.RequestError:
            return False

    def list_indexes(self) -> list[dict[str, Any]]:
        """List all indexes. Returns list from {"indexes": [...]}"""
        resp = self.client.get(self._url("index/list"), headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        return data.get("indexes", [])

    def create_index(self, name: str, dimension: int, space_type: str = "cosine") -> bool:
        """
        Create index. Verified params from src/main.cpp line ~300:
        Required: index_name, dim, space_type
        """
        payload = {
            "index_name": name,
            "dim": dimension,
            "space_type": space_type,
        }
        logger.info(f"Creating index: {name} (dim={dimension}, space_type={space_type})")
        resp = self.client.post(self._url("index/create"), json=payload, headers=self._headers())
        resp.raise_for_status()
        return True

    def delete_index(self, name: str) -> bool:
        """Delete index. Route: DELETE /api/v1/index/<name>/delete"""
        resp = self.client.delete(self._url(f"index/{name}/delete"), headers=self._headers())
        resp.raise_for_status()
        return True

    def insert_vectors(
        self,
        index_name: str,
        ids: list[str],
        vectors: list[list[float]],
        metadata: Optional[list[dict[str, Any]]] = None,
    ) -> bool:
        """
        Insert vectors. Verified from src/main.cpp:
        Route: POST /api/v1/index/<name>/vector/insert
        Body: array of objects OR single object with:
          - id: string or number
          - values: list of floats (dense vector)
          - meta: string (JSON stringified metadata)
        """
        points = []
        for i, (vid, vec) in enumerate(zip(ids, vectors)):
            point: dict[str, Any] = {
                "id": vid,
                "vector": vec,
            }
            if metadata and i < len(metadata):
                point["meta"] = json_lib.dumps(metadata[i])
            points.append(point)

        logger.info(f"Inserting {len(points)} vectors into: {index_name}")

        # Insert in batches of 100
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            resp = self.client.post(
                self._url(f"index/{index_name}/vector/insert"),
                json=batch,
                headers=self._headers(),
            )
            resp.raise_for_status()

        return True

    def search(
        self,
        index_name: str,
        vector: list[float],
        k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Search similar vectors. Verified from src/main.cpp line ~650:
        Route: POST /api/v1/index/<name>/search
        Required: k, vector (list of floats)
        """
        payload = {
            "vector": vector,
            "k": k,
        }
        resp = self.client.post(
            self._url(f"index/{index_name}/search"),
            json=payload,
            headers=self._headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        return data.get("results", data.get("matches", []))

    def index_exists(self, name: str) -> bool:
        """Check if index exists by listing all indexes."""
        try:
            indexes = self.list_indexes()
            return any(idx.get("name") == name for idx in indexes)
        except Exception:
            return False

    def ensure_index(self, name: str, dimension: int, space_type: str = "cosine") -> None:
        """Create index only if it doesn't exist."""
        if not self.index_exists(name):
            self.create_index(name, dimension, space_type)
        else:
            logger.info(f"Index '{name}' already exists")

    def close(self):
        self.client.close()
