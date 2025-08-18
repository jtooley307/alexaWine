import os
import json
import logging
import argparse
from pathlib import Path
from typing import List, Optional

import pandas as pd
import requests
import sqlite3
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Config & Logging
# -----------------------------------------------------------------------------

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("xwines_precompute")

DATA_DIR = Path("data/xwines")
DB_PATH = DATA_DIR / "xwines.db"
OUT_CSV = DATA_DIR / "xwines_embeddings.csv"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def load_wines(csv_path: Optional[str] = None) -> pd.DataFrame:
    if csv_path:
        p = Path(csv_path)
        if not p.exists():
            raise FileNotFoundError(f"CSV path not found: {csv_path}")
        logger.info(f"Loading wines from CSV at {p}")
        return pd.read_csv(p)

    if DB_PATH.exists():
        logger.info(f"Loading wines from SQLite DB at {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        try:
            df = pd.read_sql_query("SELECT * FROM wines", conn)
            return df
        finally:
            conn.close()

    wines_csv = DATA_DIR / "wines.csv"
    if wines_csv.exists():
        logger.info(f"Loading wines from CSV at {wines_csv}")
        return pd.read_csv(wines_csv)

    raise FileNotFoundError("No wines data found. Provide --csv, or run setup_xwines_db.py, or place data/xwines/wines.csv")


def build_text(row: pd.Series) -> str:
    parts = [
        str(row.get("name", "")),
        str(row.get("winery", "")),
        str(row.get("type", "")),
        str(row.get("region", "")),
        str(row.get("country", "")),
        str(row.get("description", "")),
        str(row.get("body", "")),
        str(row.get("acidity", "")),
        str(row.get("sweetness", "")),
        str(row.get("tannin", "")),
        str(row.get("food_pairing", "")),
    ]
    return " | ".join([p for p in parts if p and p != "nan"]).strip()


def embed_text(text: str) -> List[float]:
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


def main():
    parser = argparse.ArgumentParser(description="Precompute embeddings for X-Wines using Ollama")
    parser.add_argument("--csv", dest="csv_path", help="Path to source wines CSV (optional)")
    parser.add_argument("--out", dest="out_csv", help="Output embeddings CSV (optional)")
    parser.add_argument("--limit", dest="limit", type=int, default=0, help="Limit rows for testing (0 = all)")
    args = parser.parse_args()

    logger.info("Precomputing X-Wines embeddings using local Ollama...")
    df = load_wines(args.csv_path)
    if args.limit and args.limit > 0:
        df = df.head(args.limit)
    logger.info(f"Loaded {len(df)} wines")

    out_rows = []
    for idx, row in df.iterrows():
        wine_id = row.get("wine_id", row.get("id", idx))
        text = build_text(row)
        if not text:
            if (idx + 1) % 1000 == 0:
                logger.info(f"Processed {idx + 1} rows...")
            continue
        try:
            emb = embed_text(text)
        except Exception as e:
            logger.error(f"Embedding failed for wine_id={wine_id}: {e}")
            continue
        out_rows.append({
            "wine_id": wine_id,
            "text": text,
            "embedding": json.dumps(emb),  # store as JSON string
        })
        if (idx + 1) % 200 == 0:
            logger.info(f"Embedded {idx + 1} / {len(df)}")

    if not out_rows:
        logger.error("No embeddings generated.")
        return

    out_df = pd.DataFrame(out_rows)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out_csv) if args.out_csv else OUT_CSV
    out_df.to_csv(out_path, index=False)
    logger.info(f"Wrote {len(out_df)} embeddings to {out_path}")


if __name__ == "__main__":
    main()
