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


def _first(row: pd.Series, keys: list[str], default: str = ""):
    for k in keys:
        if k in row and pd.notna(row.get(k)):
            return row.get(k)
    return default


def _normalize_listish(val):
    """Normalize values like "['A','B']" or Python lists to a comma string."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    if isinstance(val, list):
        return ", ".join([str(x) for x in val if x])
    s = str(val)
    if s.startswith("[") and s.endswith("]"):
        try:
            import ast
            parsed = ast.literal_eval(s)
            if isinstance(parsed, list):
                return ", ".join([str(x) for x in parsed if x])
        except Exception:
            pass
    return s


def build_text(row: pd.Series) -> str:
    """Builds the embedding text, ensuring wine name is included across schemas.

    Supports both Slim and Full CSVs by checking multiple column aliases,
    mirroring the ingestion script fields.
    """
    name = _first(row, ["name", "WineName"]) or ""
    winery = _first(row, ["winery", "WineryName"]) or ""
    wtype = _first(row, ["type", "Type"]) or ""
    region = _first(row, ["region", "RegionName"]) or ""
    country = _first(row, ["country", "Country"]) or ""
    desc = _first(row, ["description", "Elaborate"]) or ""
    body = _first(row, ["body", "Body"]) or ""
    acidity = _first(row, ["acidity", "Acidity"]) or ""
    sweetness = _first(row, ["sweetness"]) or ""
    tannin = _first(row, ["tannin"]) or ""
    food = _normalize_listish(_first(row, ["food_pairing", "Harmonize"]))
    grapes = _normalize_listish(_first(row, ["Grapes"]))

    parts = [name, winery, wtype, region, country, grapes, food, desc, body, acidity, sweetness, tannin]
    return " | ".join([str(p) for p in parts if p and str(p) != "nan"]).strip()


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
