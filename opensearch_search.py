import os
import json
from typing import List, Dict, Any, Optional, Tuple
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import requests
import logging

# Reads config from environment to avoid tight coupling
OS_ENDPOINT = os.getenv("OPENSEARCH_ENDPOINT", "").strip()
OS_REGION = os.getenv("OPENSEARCH_REGION", os.getenv("AWS_REGION", "us-west-2"))
OS_INDEX = os.getenv("OPENSEARCH_INDEX", "xwines")
OS_USER = os.getenv("OPENSEARCH_USERNAME")
OS_PASS = os.getenv("OPENSEARCH_PASSWORD")
OS_USE_IAM = os.getenv("OPENSEARCH_USE_IAM", "true").lower() == "true"

# Embedding config (query-time)
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "ollama").strip().lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
BEDROCK_REGION = os.getenv("BEDROCK_REGION", os.getenv("AWS_REGION", "us-west-2"))
BEDROCK_EMBEDDING_MODEL_ID = os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")

_client: Optional[OpenSearch] = None
logger = logging.getLogger(__name__)

def get_client() -> OpenSearch:
    global _client
    if _client is not None:
        return _client
    if not OS_ENDPOINT:
        raise RuntimeError("OPENSEARCH_ENDPOINT is not set")
    host = OS_ENDPOINT.replace("https://", "").replace("http://", "")
    if OS_USE_IAM:
        # SigV4 auth
        import boto3
        credentials = boto3.Session().get_credentials()
        if credentials is None:
            raise RuntimeError("No AWS credentials found for SigV4 auth")
        awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, OS_REGION, 'es', session_token=credentials.token)
        _client = OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30,
        )
    else:
        if not (OS_USER and OS_PASS):
            raise RuntimeError("Set OPENSEARCH_USERNAME and OPENSEARCH_PASSWORD when OPENSEARCH_USE_IAM=false")
        scheme = "https" if OS_ENDPOINT.startswith("https://") else "http"
        port = 443 if scheme == "https" else 80
        _client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_auth=(OS_USER, OS_PASS),
            use_ssl=(scheme == "https"),
            verify_certs=(scheme == "https"),
            connection_class=RequestsHttpConnection,
            timeout=30,
        )
    return _client


def search_text(query: str, size: int = 5) -> List[Dict[str, Any]]:
    """Simple BM25 text search against the xwines index.
    Returns list of _source docs.
    """
    client = get_client()
    body = {
        "size": size,
        "query": {
            "multi_match": {
                "query": query,
                "fields": [
                    "name^3",
                    "winery",
                    "type",
                    "region",
                    "country",
                    "description"
                ]
            }
        }
    }
    res = client.search(index=OS_INDEX, body=body)
    hits = res.get('hits', {}).get('hits', [])
    out = []
    for h in hits:
        src = h.get('_source', {}) or {}
        try:
            src['_relevance'] = float(h.get('_score', 0.0))
        except Exception:
            src['_relevance'] = 0.0
        out.append(src)
    return out


def _embed(text: str) -> List[float]:
    """Return an embedding vector for the given text using the configured provider.
    Providers:
      - bedrock: AWS Bedrock Runtime invoke_model (recommended for Lambda)
      - ollama: Local dev server
    """
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
        vec = data.get("embedding") or (data.get("embeddings", {}) or {}).get("values")
        if not isinstance(vec, list):
            raise RuntimeError(f"Unexpected Bedrock embedding response: {data}")
    else:
        # Default: Ollama local embedding
        payload = {"model": OLLAMA_EMBED_MODEL, "prompt": text}
        r = requests.post(f"{OLLAMA_BASE_URL}/api/embeddings", json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "embedding" in data:
            vec = data["embedding"]
        elif isinstance(data, dict) and "data" in data:
            vec = data["data"][0].get("embedding", [])
        else:
            raise RuntimeError(f"Unexpected embedding response: {data}")
    if not isinstance(vec, list) or (EMBED_DIM and len(vec) != EMBED_DIM):
        raise RuntimeError(f"Embedding length {len(vec)} != EMBED_DIM={EMBED_DIM}")
    try:
        logger.debug("Embed vector provider=%s dims=%s sample=%s", EMBED_PROVIDER, len(vec), vec[:5])
    except Exception:
        pass
    return vec


def _knn_search(client: OpenSearch, qv: List[float], k: int, num_candidates: int, with_ids: bool) -> List[Any]:
    """Try multiple kNN body shapes for broader OpenSearch compatibility."""
    errors: List[str] = []
    # Shape A: object-style under field (newer syntax)
    bodies = [
        {
            "size": k,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": qv,
                        "k": k,
                        "num_candidates": num_candidates
                    }
                }
            }
        },
        # Shape B: field, query_vector, num_candidates (commonly supported)
        {
            "size": k,
            "query": {
                "knn": {
                    "field": "embedding",
                    "query_vector": qv,
                    "k": k,
                    "num_candidates": num_candidates
                }
            }
        },
        # Shape B2: knn as a list of queries
        {
            "size": k,
            "query": {
                "knn": [
                    {
                        "field": "embedding",
                        "query_vector": qv,
                        "k": k,
                        "num_candidates": num_candidates
                    }
                ]
            }
        },
        # Shape C: without num_candidates
        {
            "size": k,
            "query": {
                "knn": {
                    "field": "embedding",
                    "query_vector": qv,
                    "k": k
                }
            }
        }
    ]
    for body in bodies:
        try:
            logger.debug("Attempting kNN body: %s", str(body)[:500])
            res = client.search(index=OS_INDEX, body=body)
            hits = res.get('hits', {}).get('hits', [])
            if with_ids:
                return [(h.get('_id', ''), h.get('_source', {}), float(h.get('_score', 0.0))) for h in hits]
            else:
                return [h.get('_source', {}) for h in hits]
        except Exception as e:
            logger.warning("kNN variant failed: %s", e)
            errors.append(str(e))
            continue
    # Fallback: script_score with cosineSimilarity
    try:
        body = {
            "size": k,
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, doc['embedding']) + 1.0",
                        "params": {"query_vector": qv}
                    }
                }
            }
        }
        logger.debug("Attempting script_score body: %s", str(body)[:500])
        res = client.search(index=OS_INDEX, body=body)
        hits = res.get('hits', {}).get('hits', [])
        if with_ids:
            return [(h.get('_id', ''), h.get('_source', {}), float(h.get('_score', 0.0))) for h in hits]
        else:
            return [h.get('_source', {}) for h in hits]
    except Exception as e2:
        logger.warning("script_score fallback failed: %s", e2)
        errors.append(f"script_score fallback failed: {e2}")
    # Fallback: _plugins/_knn/knn_search endpoint
    try:
        body = {
            "index": OS_INDEX,
            "queries": [
                {
                    "field": "embedding",
                    "query_vector": qv,
                    "k": k,
                    "num_candidates": num_candidates
                }
            ]
        }
        logger.debug("Attempting plugin knn_search body: %s", str(body)[:500])
        res = client.transport.perform_request(
            method="POST",
            url="/_plugins/_knn/knn_search",
            body=body,
        )
        # Response shape may differ by version; try common paths
        payload = res["body"] if isinstance(res, dict) and "body" in res else res
        if isinstance(payload, dict):
            # Try direct hits
            hits = payload.get('hits', {}).get('hits', [])
            if not hits:
                # Some versions return {"_shards":..., "hits":{...}} or {"responses":[{"hits":{...}}]}
                if "responses" in payload and payload["responses"]:
                    hits = payload["responses"][0].get('hits', {}).get('hits', [])
            if with_ids:
                return [(h.get('_id', ''), h.get('_source', {}), float(h.get('_score', 0.0))) for h in hits]
            else:
                return [h.get('_source', {}) for h in hits]
        raise RuntimeError("Unexpected knn_search plugin response")
    except Exception as e3:
        logger.warning("knn_search plugin fallback failed: %s", e3)
        errors.append(f"knn_search plugin fallback failed: {e3}")
        raise RuntimeError("All vector query variants failed: " + " | ".join(errors))


def search_vector(query: str, k: int = 5, num_candidates: int = 100) -> List[Dict[str, Any]]:
    """Two-phase search: BM25 prefilter then vector script_score rescore.

    1) Use BM25 multi_match to retrieve ``num_candidates`` docs (fast lexical prefilter).
    2) Rescore those candidates with cosineSimilarity over ``embedding`` and return top ``k``.
    """
    client = get_client()

    # Phase 1: BM25 prefilter to get candidates (ids)
    try:
        text_hits = _search_text_with_ids(query, size=max(num_candidates, k))
        candidate_ids = [doc_id for doc_id, _src, _s in text_hits]
    except Exception as e:
        logger.warning("Text prefilter failed (%s); falling back to pure vector search", e)
        candidate_ids = []

    # Compute query embedding once
    qv = _embed(query)

    # Phase 2: Vector rescore over candidates if available; else over all docs
    base_query: Dict[str, Any]
    if candidate_ids:
        # Use ids filter to restrict scoring set
        base_query = {
            "bool": {
                "filter": [
                    {"ids": {"values": candidate_ids}}
                ]
            }
        }
        size = min(len(candidate_ids), max(k, 10))  # enough to rank within candidates
    else:
        base_query = {"match_all": {}}
        size = k

    body = {
        "size": size,
        "query": {
            "script_score": {
                "query": base_query,
                "script": {
                    "source": "cosineSimilarity(params.query_vector, doc['embedding']) + 1.0",
                    "params": {"query_vector": qv}
                }
            }
        }
    }

    res = client.search(index=OS_INDEX, body=body)
    hits = res.get('hits', {}).get('hits', [])

    # If we over-fetched due to candidate_ids, trim to k
    results = []
    for h in hits[:k]:
        src = h.get('_source', {}) or {}
        try:
            src['_relevance'] = float(h.get('_score', 0.0))
        except Exception:
            src['_relevance'] = 0.0
        results.append(src)
    return results


def _search_text_with_ids(query: str, size: int) -> List[Tuple[str, Dict[str, Any], float]]:
    client = get_client()
    body = {
        "size": size,
        "query": {
            "multi_match": {
                "query": query,
                "fields": [
                    "name^3",
                    "winery",
                    "type",
                    "region",
                    "country",
                    "description",
                    "grapes",
                    "food_pairing"
                ]
            }
        }
    }
    res = client.search(index=OS_INDEX, body=body)
    hits = res.get('hits', {}).get('hits', [])
    return [(h.get('_id', ''), h.get('_source', {}), float(h.get('_score', 0.0))) for h in hits]


def _search_vector_with_ids(query: str, k: int, num_candidates: int) -> List[Tuple[str, Dict[str, Any], float]]:
    client = get_client()
    qv = _embed(query)
    return _knn_search(client, qv, k, num_candidates, with_ids=True)  # type: ignore[return-value]


def search_hybrid(query: str, size: int = 5, k: int = 5) -> List[Dict[str, Any]]:
    """Hybrid search: run BM25 and kNN, then merge by reciprocal rank."""
    text_hits = _search_text_with_ids(query, max(size, k))
    vec_hits = _search_vector_with_ids(query, k, num_candidates=max(100, k * 20))
    ranks: Dict[str, float] = {}
    sources: Dict[str, Dict[str, Any]] = {}
    # Assign reciprocal rank contributions
    for i, (id_, src, _) in enumerate(text_hits):
        if not id_:
            continue
        sources[id_] = src
        ranks[id_] = ranks.get(id_, 0.0) + 1.0 / (i + 1)
    for i, (id_, src, _) in enumerate(vec_hits):
        if not id_:
            continue
        sources[id_] = src
        ranks[id_] = ranks.get(id_, 0.0) + 1.0 / (i + 1)
    # Sort by combined score
    ordered = sorted(ranks.items(), key=lambda kv: kv[1], reverse=True)
    results: List[Dict[str, Any]] = []
    for id_, score in ordered[:size]:
        src = sources[id_] or {}
        src['_relevance'] = float(score)
        results.append(src)
    # If insufficient, top up with unique text hits
    if len(results) < size:
        seen = set(ordered_i[0] for ordered_i in ordered)
        for id_, src, _ in text_hits:
            if id_ not in seen:
                # Assign a small fallback relevance based on remaining order
                if isinstance(src, dict):
                    src['_relevance'] = src.get('_relevance', 0.0)
                results.append(src)
                if len(results) >= size:
                    break
    return results
