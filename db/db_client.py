import os
import json
import urllib.request
from schemas.invoice import Invoice


def _supabase_request(path: str, payload: dict) -> dict:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url:
        raise ValueError("SUPABASE_URL is missing")
    if not key:
        raise ValueError("SUPABASE_KEY is missing")

    full_url = f"{url.rstrip('/')}/rest/v1/{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        full_url,
        data=data,
        method="POST",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def insert_invoice(invoice_data: dict) -> str:
    result = _supabase_request("invoice", invoice_data)
    return result[0]["id"]


def insert_line_item(line_item_data: dict) -> None:
    _supabase_request("line_item", line_item_data)
