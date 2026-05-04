import os
import json
import urllib.request


def _storage_request(method: str, path: str, payload: dict | None = None) -> bytes:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url:
        raise ValueError("SUPABASE_URL is missing")
    if not key:
        raise ValueError("SUPABASE_KEY is missing")

    full_url = f"{url.rstrip('/')}/storage/v1/{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        full_url,
        data=data,
        method=method,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def list_invoices(bucket: str) -> list[str]:
    raw = _storage_request("POST", f"object/list/{bucket}", {"prefix": "", "limit": 10000})
    files = json.loads(raw)
    return [f["name"] for f in files if f["name"].endswith(".pdf")]


def download_invoice(bucket: str, path: str) -> bytes:
    return _storage_request("GET", f"object/{bucket}/{path}")
