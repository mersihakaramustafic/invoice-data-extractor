import hashlib
import logging
import urllib.parse
from datetime import datetime, timezone
from db.db_client import _supabase_request, _supabase_get, _supabase_patch

MAX_RETRIES = 3


def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def document_exists(file_hash: str) -> bool:
    rows = _supabase_get(f"invoice_documents?file_hash=eq.{urllib.parse.quote(file_hash)}&select=id")
    return len(rows) > 0


def insert_document(file_path: str, file_name: str, file_hash: str) -> str:
    logging.info("Inserting invoice document: %s", file_name)
    result = _supabase_request("invoice_documents", {
        "file_path": file_path,
        "file_name": file_name,
        "file_hash": file_hash,
    })
    doc_id = result[0]["id"]
    logging.info("Inserted invoice document id=%s", doc_id)
    return doc_id


def get_pending_documents(limit: int) -> list[dict]:
    logging.info("Fetching pending invoice documents (limit=%d)", limit)
    docs = _supabase_get(
        f"invoice_documents?status=in.(pending,failed)&retry_count=lt.{MAX_RETRIES}"
        f"&order=uploaded_at.asc&limit={limit}"
    )
    logging.info("Found %d document(s) to process", len(docs))
    return docs


def mark_processing(doc_id: str) -> None:
    _supabase_patch(
        f"invoice_documents?id=eq.{doc_id}",
        {"status": "processing", "processing_started_at": _now()},
    )


def mark_processed(doc_id: str) -> None:
    _supabase_patch(
        f"invoice_documents?id=eq.{doc_id}",
        {"status": "processed", "processed_at": _now(), "error_message": None},
    )


def mark_failed(doc_id: str, error_message: str, retry_count: int) -> None:
    _supabase_patch(
        f"invoice_documents?id=eq.{doc_id}",
        {
            "status": "failed",
            "error_message": error_message[:500],
            "retry_count": retry_count + 1,
        },
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
