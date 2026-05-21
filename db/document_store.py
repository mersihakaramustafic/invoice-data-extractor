import hashlib
import logging
from datetime import datetime, timezone
from db.db_client import _supabase_post, _supabase_get, _supabase_patch

MAX_RETRIES = 3


def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


async def document_exists(file_hash: str) -> bool:
    rows = await _supabase_get("invoice_documents", {"file_hash": f"eq.{file_hash}", "select": "id"})
    return len(rows) > 0


async def insert_document(file_path: str, file_name: str, file_hash: str) -> str:
    logging.info("Inserting invoice document: %s", file_name)
    result = await _supabase_post("invoice_documents", {
        "file_path": file_path,
        "file_name": file_name,
        "file_hash": file_hash,
    })
    doc_id = result[0]["id"]
    logging.info("Inserted invoice document id=%s", doc_id)
    return doc_id


async def reset_stale_processing() -> None:
    await _supabase_patch(
        "invoice_documents",
        {"status": "eq.processing"},
        {"status": "pending"},
    )


async def get_status_counts(doc_ids: list[str]) -> dict:
    counts = {"pending": 0, "processing": 0, "processed": 0, "failed": 0}
    if not doc_ids:
        return counts
    rows = await _supabase_get("invoice_documents", {
        "select": "status",
        "id": f"in.({','.join(doc_ids)})",
    })
    for row in rows:
        status = row.get("status")
        if status in counts:
            counts[status] += 1
    return counts


async def get_pending_documents() -> list[dict]:
    logging.info("Fetching pending invoice documents")
    docs = await _supabase_get("invoice_documents", {
        "status": "in.(pending,failed)",
        "retry_count": f"lt.{MAX_RETRIES}",
        "order": "uploaded_at.asc",
    })
    logging.info("Found %d document(s) to process", len(docs))
    return docs


async def mark_processing(doc_id: str) -> None:
    await _supabase_patch(
        "invoice_documents",
        {"id": f"eq.{doc_id}"},
        {"status": "processing", "processing_started_at": _now()},
    )


async def mark_processed(doc_id: str) -> None:
    await _supabase_patch(
        "invoice_documents",
        {"id": f"eq.{doc_id}"},
        {"status": "processed", "processed_at": _now()},
    )


async def mark_failed(doc_id: str, retry_count: int) -> None:
    await _supabase_patch(
        "invoice_documents",
        {"id": f"eq.{doc_id}"},
        {"status": "failed", "retry_count": retry_count + 1},
    )


async def log_event(
    document_id: str,
    level: str,
    event: str,
    message: str | None = None,
) -> None:
    await _supabase_post("invoice_logs", {
        "document_id": document_id,
        "level": level,
        "event": event,
        "message": message,
    })


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
