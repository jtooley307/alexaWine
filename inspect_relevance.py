#!/usr/bin/env python3
"""
inspect_relevance.py

Small diagnostic script to print wines and their _relevance values for a query
using the existing WineService pipeline (OpenSearch if enabled).

Usage:
  USE_OPENSEARCH=true USE_VECTOR_SEARCH=true python3 inspect_relevance.py "california red blend" --size 12

Env flags respected (same as runtime):
  - USE_OPENSEARCH, USE_VECTOR_SEARCH, USE_HYBRID_SEARCH
  - OPENSEARCH_ENDPOINT, OPENSEARCH_REGION, OPENSEARCH_INDEX, OPENSEARCH_USE_IAM
  - EMBED_PROVIDER, BEDROCK_REGION, BEDROCK_EMBEDDING_MODEL_ID, EMBED_DIM

Outputs a sorted list with name, winery, region, country, and _relevance.
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any

# Ensure we import from local project
sys.path.append(os.path.dirname(__file__))

from wine_service import WineService  # type: ignore
from config import config  # type: ignore


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect wine search relevance values")
    parser.add_argument("query", help="Search query (e.g., 'california red blend')")
    parser.add_argument("--size", type=int, default=12, help="How many results to request (default: 12)")
    args = parser.parse_args()

    # Hint the service about desired size via config (WINE_API_MAX_RESULTS)
    try:
        # Monkey-patch for the session: set desired size for this run
        setattr(config, 'WINE_API_MAX_RESULTS', int(args.size))
    except Exception:
        pass

    svc = WineService()
    wines: List[Dict[str, Any]] = svc.search_wines(args.query)

    if not wines:
        print("No results.")
        return 0

    # Sort by _relevance desc if present
    def rel(w: Dict[str, Any]) -> float:
        try:
            return float(w.get('_relevance', 0.0) or 0.0)
        except Exception:
            return 0.0

    wines_sorted = sorted(wines, key=rel, reverse=True)

    rows = []
    for i, w in enumerate(wines_sorted, start=1):
        rows.append({
            'rank': i,
            'name': w.get('name'),
            'winery': w.get('winery'),
            'region': w.get('region'),
            'country': w.get('country'),
            '_relevance': rel(w),
            'source': w.get('source')
        })

    # Pretty print
    print(json.dumps({'query': args.query, 'results': rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
