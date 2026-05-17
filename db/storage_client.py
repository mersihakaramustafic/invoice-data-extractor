import logging
import os
import httpx


def _headers(content_type: str = "application/json") -> dict:
    key = os.getenv("SUPABASE_KEY")
    if not key:
        raise ValueError("SUPABASE_KEY is missing")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": content_type,
    }


def _base_url() -> str:
    url = os.getenv("SUPABASE_URL")
    if not url:
        raise ValueError("SUPABASE_URL is missing")
    return url.rstrip("/") + "/storage/v1"


async def list_invoices(bucket: str) -> list[str]:
    logging.info("Listing invoices in bucket: %s", bucket)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_base_url()}/object/list/{bucket}",
            json={"prefix": "", "limit": 10000},
            headers=_headers(),
        )
        resp.raise_for_status()
        files = resp.json()
    names = [f["name"] for f in files if f["name"].endswith(".pdf")]
    logging.info("Found %d invoice(s) in bucket %s", len(names), bucket)
    return names


async def upload_to_bucket(bucket: str, path: str, file_bytes: bytes) -> None:
    logging.info("Uploading invoice to bucket: %s/%s (%d bytes)", bucket, path, len(file_bytes))
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_base_url()}/object/{bucket}/{path}",
            content=file_bytes,
            headers={**_headers("application/pdf"), "x-upsert": "true"},
        )
        resp.raise_for_status()
    logging.info("Uploaded invoice to bucket: %s/%s", bucket, path)


async def download_invoice(bucket: str, path: str) -> bytes:
    logging.info("Downloading invoice: %s/%s", bucket, path)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_base_url()}/object/{bucket}/{path}",
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.content
