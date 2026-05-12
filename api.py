from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from langfuse import observe, get_client
from utils.pdf_reader import read_pdf_from_bytes
from utils.scoring import completeness_score
from llm.extractor import extract_invoice_data
from db.invoice_store import store_invoice
from db.storage_client import download_invoice, upload_to_bucket
from db.document_store import (
    compute_file_hash, document_exists, insert_document,
    get_pending_documents, mark_processing, mark_processed, mark_failed,
)
from schemas.invoice import Invoice
from constants import ALLOWED_MODELS, DEFAULT_MODEL, SUPABASE_BUCKET, BATCH_SIZE, BATCH_LIMIT

logging.basicConfig(level=logging.INFO)

app = FastAPI()

HTML = (Path(__file__).parent / "static" / "index.html").read_text()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


@observe(name="process_invoice")
def extract_and_observe(file_bytes: bytes, model: str) -> Invoice:
    text = read_pdf_from_bytes(file_bytes)
    logging.info("=== EXTRACTED PDF TEXT ===\n%s\n==========================", text)
    result = extract_invoice_data(text, model=model)
    score, comment = completeness_score(result)
    get_client().score_current_trace(name="completeness", value=score, comment=comment)
    return result


@app.post("/invoices/upload")
async def upload_invoices(files: list[UploadFile] = File(...)):
    results = []
    for file in files:
        if not file.filename.endswith(".pdf"):
            logging.warning("Rejected non-PDF file: %s", file.filename)
            results.append({"file": file.filename, "status": "rejected", "detail": "Only PDF files are accepted"})
            continue
        contents = await file.read()
        try:
            file_hash = compute_file_hash(contents)
            if document_exists(file_hash):
                logging.info("Duplicate file skipped: %s", file.filename)
                results.append({"file": file.filename, "status": "duplicate"})
                continue
            upload_to_bucket(SUPABASE_BUCKET, file.filename, contents)
            insert_document(SUPABASE_BUCKET + "/" + file.filename, file.filename, file_hash)
            logging.info("Uploaded %s to bucket", file.filename)
            results.append({"file": file.filename, "status": "uploaded"})
        except Exception as e:
            logging.error("Failed to upload %s: %s", file.filename, e)
            results.append({"file": file.filename, "status": "error", "detail": str(e)})
    return results


@app.post("/invoices/batch")
async def batch_invoices(
    model: str = DEFAULT_MODEL,
    limit: int = BATCH_LIMIT,
    batch_size: int = BATCH_SIZE,
):
    if model not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"Model must be one of: {', '.join(ALLOWED_MODELS)}")

    docs = get_pending_documents(limit)
    if not docs:
        return {"total": 0, "succeeded": 0, "skipped": 0, "failed": 0, "errors": []}

    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=batch_size)
    succeeded = 0
    skipped = 0
    failed = 0
    errors = []

    def process(doc: dict) -> bool:
        mark_processing(doc["id"])
        file_bytes = download_invoice(SUPABASE_BUCKET, doc["file_name"])
        result = extract_and_observe(file_bytes, model=model)
        result.file_path = doc["file_path"]
        stored = store_invoice(result)
        mark_processed(doc["id"])
        return stored

    async def process_one(doc: dict):
        nonlocal succeeded, skipped, failed
        try:
            stored = await loop.run_in_executor(executor, process, doc)
            if stored:
                succeeded += 1
            else:
                skipped += 1
        except Exception as e:
            failed += 1
            errors.append({"file": doc["file_name"], "error": str(e)})
            logging.error("FAILED %s: %s", doc["file_name"], e)
            mark_failed(doc["id"], str(e), doc["retry_count"])

    for i in range(0, len(docs), batch_size):
        batch = docs[i : i + batch_size]
        logging.info("Processing batch %d/%d (%d files)", i // batch_size + 1, -(-len(docs) // batch_size), len(batch))
        await asyncio.gather(*[process_one(d) for d in batch])

    return {"total": len(docs), "succeeded": succeeded, "skipped": skipped, "failed": failed, "errors": errors}
