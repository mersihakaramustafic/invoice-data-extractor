import logging
import os
import httpx


def _headers() -> dict:
    key = os.getenv("SUPABASE_KEY")
    if not key:
        raise ValueError("SUPABASE_KEY is missing")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _base_url() -> str:
    url = os.getenv("SUPABASE_URL")
    if not url:
        raise ValueError("SUPABASE_URL is missing")
    return url.rstrip("/") + "/rest/v1"


async def _supabase_post(endpoint: str, payload: dict) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{_base_url()}/{endpoint}", json=payload, headers=_headers())
        resp.raise_for_status()
        return resp.json()


async def _supabase_get(endpoint: str, params: dict) -> list:
    headers = _headers()
    del headers["Prefer"]
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_base_url()}/{endpoint}", headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()


async def _supabase_patch(endpoint: str, params: dict, payload: dict) -> None:
    headers = _headers()
    del headers["Prefer"]
    async with httpx.AsyncClient() as client:
        resp = await client.patch(f"{_base_url()}/{endpoint}", headers=headers, params=params, json=payload)
        resp.raise_for_status()


async def invoice_exists(invoice_number: str) -> bool:
    logging.info("Checking if invoice exists: %s", invoice_number)
    rows = await _supabase_get("invoice", {"invoice_number": f"eq.{invoice_number}", "select": "id"})
    return len(rows) > 0


async def insert_invoice(invoice_data: dict) -> str:
    logging.info("Inserting invoice: %s", invoice_data.get("invoice_number"))
    result = await _supabase_post("invoice", invoice_data)
    invoice_id = result[0]["id"]
    logging.info("Inserted invoice with id=%s", invoice_id)
    return invoice_id


async def insert_line_item(line_item_data: dict) -> None:
    logging.info("Inserting line item for invoice_id=%s", line_item_data.get("invoice_id"))
    await _supabase_post("line_item", line_item_data)
