import logging
import os
import json
import urllib.parse
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


def _supabase_get(path: str) -> list:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url:
        raise ValueError("SUPABASE_URL is missing")
    if not key:
        raise ValueError("SUPABASE_KEY is missing")

    full_url = f"{url.rstrip('/')}/rest/v1/{path}"
    req = urllib.request.Request(
        full_url,
        method="GET",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def invoice_exists(invoice_number: str) -> bool:
    logging.info("Checking if invoice exists: %s", invoice_number)
    rows = _supabase_get(f"invoice?invoice_number=eq.{urllib.parse.quote(invoice_number)}&select=id")
    return len(rows) > 0


def insert_invoice(invoice_data: dict) -> str:
    logging.info("Inserting invoice: %s", invoice_data.get("invoice_number"))
    result = _supabase_request("invoice", invoice_data)
    invoice_id = result[0]["id"]
    logging.info("Inserted invoice with id=%s", invoice_id)
    return invoice_id


def insert_line_item(line_item_data: dict) -> None:
    logging.info("Inserting line item for invoice_id=%s", line_item_data.get("invoice_id"))
    _supabase_request("line_item", line_item_data)
