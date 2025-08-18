import os
import json
import math
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Tuple

import pandas as pd
import requests

from config import config

# Paths
DATA_DIR = Path(config.XWINES_DATA_DIR)
DB_PATH = Path(config.XWINES_DB_PATH)
EMB_CSV = Path(config.XWINES_EMB_CSV)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))


def _embed_query(text: str) -> List[float]:
    url = f"{OLLAMA_BASE_URL}/api/embeddings"
    resp = requests.post(url, json={"model": OLLAMA_MODEL, "prompt": text}, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and "embedding" in data:
        emb = data["embedding"]
    elif isinstance(data, dict) and "data" in data and data["data"]:
        emb = data["data"][0].get("embedding", [])
    else:
        raise ValueError(f"Unexpected Ollama response: {data}")
    if not isinstance(emb, list) or (EMBED_DIM and len(emb) != EMBED_DIM):
        raise ValueError(f"Embedding length {len(emb)} does not match EMBED_DIM={EMBED_DIM}")
    return emb


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _load_embeddings() -> pd.DataFrame:
    if not EMB_CSV.exists():
        raise FileNotFoundError(f"Embeddings file not found: {EMB_CSV}")
    df = pd.read_csv(EMB_CSV)
    # Ensure string wine_id
    df["wine_id"] = df["wine_id"].apply(lambda v: str(int(v)) if isinstance(v, float) and v.is_integer() else str(v))
    # Parse JSON embeddings
    df["embedding_vec"] = df["embedding"].apply(lambda s: json.loads(s) if isinstance(s, str) else s)
    return df[["wine_id", "embedding_vec"]]


def _fetch_wines_by_ids(ids: List[str]) -> List[Dict[str, Any]]:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # Parameterized IN clause
        placeholders = ",".join(["?"] * len(ids))
        q = f"SELECT * FROM wines WHERE wine_id IN ({placeholders})"
        rows = conn.execute(q, ids).fetchall()
        res = [dict(r) for r in rows]
        return res
    finally:
        conn.close()


def search_wines(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """Semantic search using local precomputed embeddings and SQLite wines.

    Returns up to k wine dicts matching the schema from the wines table.
    """
    if not query or not query.strip():
        return []

    emb_df = _load_embeddings()
    q_vec = _embed_query(query.strip())

    # Compute cosine similarity
    sims: List[Tuple[str, float]] = []
    for _, row in emb_df.iterrows():
        wid = row["wine_id"]
        vec = row["embedding_vec"]
        if isinstance(vec, list) and vec:
            sims.append((wid, _cosine(q_vec, vec)))
    sims.sort(key=lambda t: t[1], reverse=True)

    top_ids = [wid for wid, _ in sims[:k]]
    if not top_ids:
        return []

    wines = _fetch_wines_by_ids(top_ids)
    # Preserve ranking order
    order = {wid: i for i, wid in enumerate(top_ids)}
    wines.sort(key=lambda w: order.get(str(w.get("wine_id")), 1e9))

    # Mark source
    for w in wines:
        w["source"] = "local"
    return wines
