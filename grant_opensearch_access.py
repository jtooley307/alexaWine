import os
import json
import logging
from urllib.parse import urlparse

import boto3
import requests
from requests_aws4auth import AWS4Auth
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("grant_os_access")

OS_ENDPOINT = os.getenv("OPENSEARCH_ENDPOINT", "").strip()
OS_REGION = os.getenv("OPENSEARCH_REGION", os.getenv("AWS_REGION", "us-west-2"))

if not OS_ENDPOINT:
    raise SystemExit("OPENSEARCH_ENDPOINT is not set in .env")

# Resolve host
host = OS_ENDPOINT
if host.startswith("https://"):
    host = host[len("https://"):]
elif host.startswith("http://"):
    host = host[len("http://"):]

def _sanitize_aws_env():
    aid = os.environ.get("AWS_ACCESS_KEY_ID", "")
    sak = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    # If placeholders are present, remove them to allow default credential chain (CLI profile, config files, etc.)
    def _is_placeholder(v: str) -> bool:
        vlow = v.strip().lower()
        return (not v) or vlow.startswith("your_") or vlow in {"", "changeme", "example"}
    if _is_placeholder(aid) or _is_placeholder(sak):
        os.environ.pop("AWS_ACCESS_KEY_ID", None)
        os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
        os.environ.pop("AWS_SESSION_TOKEN", None)

_sanitize_aws_env()

session = boto3.Session()
creds = session.get_credentials()
if creds is None:
    raise SystemExit("No AWS credentials found. Configure AWS credentials.")
creds = creds.get_frozen_credentials()
awsauth = AWS4Auth(creds.access_key, creds.secret_key, OS_REGION, 'es', session_token=creds.token)

# Get current caller ARN
sts = session.client('sts')
ident = sts.get_caller_identity()
caller_arn = ident['Arn']
log.info(f"Granting OpenSearch access to backend role: {caller_arn}")

# Build URL for FGAC role mapping API (OpenSearch 2.x)
base_url = f"https://{host}"
url = f"{base_url}/_plugins/_security/api/rolesmapping/all_access"

# Prepare mapping payload: add backend role if not present
# We'll fetch existing, merge, then PUT back
headers = {"Content-Type": "application/json"}

resp = requests.get(url, auth=awsauth, headers=headers, timeout=30)
if resp.status_code not in (200, 404):
    log.error(f"Failed to read current roles mapping: {resp.status_code} {resp.text}")
    raise SystemExit(1)

existing = {}
if resp.status_code == 200:
    try:
        existing = resp.json() or {}
    except Exception:
        existing = {}

# The format for GET all_access is usually: {"all_access": {"backend_roles": [...], ...}}
backend_roles = set()
if isinstance(existing, dict):
    role_obj = existing.get('all_access', {})
    backend_roles.update(role_obj.get('backend_roles', []) or [])

if caller_arn in backend_roles:
    log.info("Caller ARN already present in backend_roles. Nothing to do.")
    raise SystemExit(0)

backend_roles.add(caller_arn)

payload = {
    "backend_roles": sorted(list(backend_roles))
}

log.info(f"Updating role mapping with backend_roles count={len(backend_roles)}")
resp = requests.put(url, auth=awsauth, headers=headers, data=json.dumps(payload), timeout=30)
if resp.status_code not in (200):
    log.error(f"Failed to update roles mapping: {resp.status_code} {resp.text}")
    raise SystemExit(1)

log.info("Successfully updated role mapping for all_access.")
