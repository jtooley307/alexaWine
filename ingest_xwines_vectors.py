import os
import json
import time
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Iterable, List, Optional, Union

import requests
import pandas as pd
import sqlite3
from dotenv import load_dotenv
import json as _json

from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.helpers import bulk
from requests_aws4auth import AWS4Auth

# -----------------------------------------------------------------------------
# Config & Logging
# -----------------------------------------------------------------------------

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("xwines_ingest")

# OpenSearch
OS_ENDPOINT = os.getenv("OPENSEARCH_ENDPOINT", "").strip()
OS_REGION = os.getenv("OPENSEARCH_REGION", os.getenv("AWS_REGION", "us-east-1"))
OS_INDEX = os.getenv("OPENSEARCH_INDEX", "xwines")
OS_USER = os.getenv("OPENSEARCH_USERNAME")
OS_PASS = os.getenv("OPENSEARCH_PASSWORD")
OS_USE_IAM = os.getenv("OPENSEARCH_USE_IAM", "true").lower() == "true"

# Embedding configuration
# Provider options: 'ollama' (default), 'bedrock'
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "ollama").strip().lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
BEDROCK_REGION = os.getenv("BEDROCK_REGION", os.getenv("AWS_REGION", "us-west-2"))
BEDROCK_EMBEDDING_MODEL_ID = os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")

# Data paths
DATA_DIR = Path("data/xwines")
DB_PATH = DATA_DIR / "xwines.db"
EMB_CSV = DATA_DIR / "xwines_embeddings.csv"

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------


def get_opensearch_client() -> OpenSearch:
    if not OS_ENDPOINT:
        raise RuntimeError("OPENSEARCH_ENDPOINT is not set")

    host = OS_ENDPOINT.replace("https://", "").replace("http://", "")

    if OS_USE_IAM:
        # SigV4 auth (works with OpenSearch domains that use IAM)
        session = requests.Session()
        # Boto3 credentials via env/instance role
        import boto3
        credentials = boto3.Session().get_credentials()
        if credentials is None:
            raise RuntimeError("No AWS credentials found for SigV4 auth. Configure your AWS profile or env vars.")
        awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, OS_REGION, 'es', session_token=credentials.token)
        client = OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=60,
            max_retries=3,
            retry_on_timeout=True,
        )
    else:
        # Basic auth
        if not (OS_USER and OS_PASS):
            raise RuntimeError("Set OPENSEARCH_USERNAME and OPENSEARCH_PASSWORD when OPENSEARCH_USE_IAM=false")
        scheme = "https" if OS_ENDPOINT.startswith("https://") else "http"
        port = 443 if scheme == "https" else 80
        client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_auth=(OS_USER, OS_PASS),
            use_ssl=(scheme == "https"),
            verify_certs=(scheme == "https"),
            connection_class=RequestsHttpConnection,
            timeout=60,
            max_retries=3,
            retry_on_timeout=True,
        )
    return client


def ensure_index(client: OpenSearch) -> None:
    if client.indices.exists(index=OS_INDEX):
        logger.info(f"Index '{OS_INDEX}' already exists")
        return

    index_body = {
        "settings": {
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 128,
            }
        },
        "mappings": {
            "properties": {
                "wine_id": {"type": "keyword"},
                "name": {"type": "text", "fields": {"raw": {"type": "keyword"}}},
                "winery": {"type": "keyword"},
                "type": {"type": "keyword"},
                "region": {"type": "keyword"},
                "country": {"type": "keyword"},
                "vintage": {"type": "integer"},
                "price": {"type": "float"},
                "rating": {"type": "float"},
                "alcohol": {"type": "float"},
                "num_reviews": {"type": "integer"},
                "body": {"type": "keyword"},
                "acidity": {"type": "keyword"},
                "sweetness": {"type": "keyword"},
                "tannin": {"type": "keyword"},
                "food_pairing": {"type": "keyword"},
                "description": {"type": "text"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": EMBED_DIM,
                    "method": {
                        "name": "hnsw",
                        "engine": "nmslib",
                        "space_type": "cosinesimil"
                    }
                }
            }
        }
    }

    client.indices.create(index=OS_INDEX, body=index_body)
    logger.info(f"Created index '{OS_INDEX}' with dimension {EMBED_DIM}")


def load_wines(csv_path: Optional[str] = None) -> pd.DataFrame:
    """Load wines from a provided CSV path, the local SQLite DB, or default CSV.

    Priority:
    1) csv_path if provided
    2) SQLite DB at data/xwines/xwines.db
    3) CSV at data/xwines/wines.csv
    """
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

    raise FileNotFoundError("No wines source found. Provide --csv path, or ensure data/xwines/xwines.db or data/xwines/wines.csv exists")


def load_precomputed_embeddings() -> Dict[str, List[float]]:
    """Load precomputed embeddings from CSV, if available.

    Returns a dict mapping wine_id (as string) -> embedding list[float].
    """
    if not EMB_CSV.exists():
        return {}
    logger.info(f"Loading precomputed embeddings from {EMB_CSV}")
    df = pd.read_csv(EMB_CSV)
    mapping: Dict[str, List[float]] = {}
    for _, row in df.iterrows():
        wid = row.get("wine_id")
        emb_raw = row.get("embedding")
        if pd.isna(wid) or pd.isna(emb_raw):
            continue
        try:
            emb = _json.loads(emb_raw) if isinstance(emb_raw, str) else emb_raw
            if isinstance(wid, float) and wid.is_integer():
                wid = int(wid)
            wid_str = str(wid)
            if isinstance(emb, list) and (not EMBED_DIM or len(emb) == EMBED_DIM):
                mapping[wid_str] = emb
        except Exception:
            continue
    logger.info(f"Loaded {len(mapping)} precomputed embeddings")
    return mapping


def _first(row: pd.Series, keys: List[str], default: str = "") -> Any:
    for k in keys:
        if k in row and pd.notna(row.get(k)):
            return row.get(k)
    return default


def _normalize_listish(val: Union[str, List[str], None]) -> str:
    """Normalize a value that might be a python-list-as-string like "['A','B']"."""
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
    """Return embedding using the configured provider for batch ingestion."""
    if EMBED_PROVIDER == "bedrock":
        import boto3
        client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
        body = json.dumps({"inputText": text})
        resp = client.invoke_model(modelId=BEDROCK_EMBEDDING_MODEL_ID, body=body)
        payload = resp.get("body")
        if hasattr(payload, "read"):
            payload = payload.read()
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8")
        data = json.loads(payload)
        emb = data.get("embedding") or (data.get("embeddings", {}) or {}).get("values")
        if not isinstance(emb, list):
            raise ValueError(f"Unexpected Bedrock embedding response: {data}")
    else:
        url = f"{OLLAMA_BASE_URL}/api/embeddings"
        payload = {"model": OLLAMA_MODEL, "prompt": text}
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        # Ollama returns either {"embedding": [...]} or {"data":[{"embedding":[...]}]}
        if isinstance(data, dict) and "embedding" in data:
            emb = data["embedding"]
        elif isinstance(data, dict) and "data" in data and data["data"]:
            emb = data["data"][0].get("embedding", [])
        else:
            raise ValueError(f"Unexpected Ollama response: {data}")

    if not isinstance(emb, list) or (EMBED_DIM and len(emb) != EMBED_DIM):
        raise ValueError(f"Embedding length {len(emb)} does not match EMBED_DIM={EMBED_DIM}")
    return emb


def doc_from_row(row: pd.Series, embedding: List[float]) -> Dict[str, Any]:
    # IDs
    wine_id = _first(row, ["wine_id", "WineID", "id"])  # may be float
    try:
        if pd.notna(wine_id):
            wine_id = int(wine_id)
    except Exception:
        wine_id = str(wine_id) if wine_id is not None else None

    # Core fields with fallbacks for Slim CSV
    name = _first(row, ["name", "WineName"]) or None
    winery = _first(row, ["winery", "WineryName"]) or None
    wtype = _first(row, ["type", "Type"]) or None
    region = _first(row, ["region", "RegionName"]) or None
    country = _first(row, ["country", "Country"]) or None
    desc = _first(row, ["description", "Elaborate"]) or None
    body = _first(row, ["body", "Body"]) or None
    acidity = _first(row, ["acidity", "Acidity"]) or None
    food = _normalize_listish(_first(row, ["food_pairing", "Harmonize"])) or None
    grapes = _normalize_listish(_first(row, ["Grapes"])) or None

    # Numeric fields
    def _to_int(v):
        try:
            return int(v) if pd.notna(v) else None
        except Exception:
            return None
    def _to_float(v):
        try:
            return float(v) if pd.notna(v) else None
        except Exception:
            return None

    vintage = _to_int(_first(row, ["vintage"]))
    price = _to_float(_first(row, ["price"]))
    rating = _to_float(_first(row, ["rating"]))
    alcohol = _to_float(_first(row, ["alcohol", "ABV"]))
    num_reviews = _to_int(_first(row, ["num_reviews"]))

    return {
        "wine_id": wine_id,
        "name": name,
        "winery": winery,
        "type": wtype,
        "region": region,
        "country": country,
        "vintage": vintage,
        "price": price,
        "rating": rating,
        "alcohol": alcohol,
        "num_reviews": num_reviews,
        "body": body,
        "acidity": acidity,
        "sweetness": _first(row, ["sweetness"]) or None,
        "tannin": _first(row, ["tannin"]) or None,
        "food_pairing": food,
        "grapes": grapes,
        "description": desc,
        "embedding": embedding,
    }


def iter_bulk_actions(df: pd.DataFrame, emb_map: Optional[Dict[str, List[float]]] = None) -> Iterable[Dict[str, Any]]:
    for _, row in df.iterrows():
        text = build_text(row)
        if not text:
            continue
        emb: Optional[List[float]] = None
        # Prefer precomputed embedding if provided
        if emb_map is not None:
            wid_val = row.get("wine_id")
            if pd.notna(wid_val):
                try:
                    wid_key = str(int(wid_val))
                except Exception:
                    wid_key = str(wid_val)
                emb = emb_map.get(wid_key)
        # Fallback to live embedding
        if emb is None:
            try:
                emb = embed_text(text)
            except Exception as e:
                logger.error(f"Embedding failed for wine_id={row.get('wine_id')}: {e}")
                continue
        doc = doc_from_row(row, emb)
        doc_id = str(doc.get("wine_id") or row.get("wine_id") or row.get("id") or _)
        yield {
            "_index": OS_INDEX,
            "_id": doc_id,
            "_source": doc,
            "_op_type": "index",
        }


def main():
    parser = argparse.ArgumentParser(description="Ingest X-Wines into OpenSearch with embeddings via Ollama")
    parser.add_argument("--csv", dest="csv_path", help="Path to source wines CSV (optional)")
    parser.add_argument("--index", dest="index", help="Override OpenSearch index name (optional)")
    parser.add_argument("--chunk-size", dest="chunk_size", type=int, default=200, help="Bulk chunk size")
    args = parser.parse_args()

    if args.index:
        global OS_INDEX
        OS_INDEX = args.index
        logger.info(f"Using overridden index name: {OS_INDEX}")

    logger.info("Starting X-Wines vector ingestion using local Ollama embeddings...")

    client = get_opensearch_client()
    ensure_index(client)

    df = load_wines(args.csv_path)
    logger.info(f"Loaded {len(df)} wine rows")
    emb_map = load_precomputed_embeddings() if EMB_CSV.exists() else None
    if emb_map:
        logger.info("Using precomputed embeddings from CSV for ingestion")
    else:
        logger.info("No precomputed embeddings found; using live embeddings")

    success, failed = bulk(
        client,
        iter_bulk_actions(df, emb_map),
        chunk_size=args.chunk_size,
        max_retries=3,
        request_timeout=120,
    )
    logger.info(f"Bulk indexing completed: success={success}, failed={failed}")

    logger.info("Done.")


if __name__ == "__main__":
    main()
