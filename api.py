from dotenv import load_dotenv
load_dotenv()

import logging
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from db.storage_client import upload_to_bucket
from db.document_store import compute_file_hash, document_exists, insert_document, get_pending_documents, reset_stale_processing, get_status_counts
from pipeline import InvoicePipeline
from constants import ALLOWED_MODELS, DEFAULT_MODEL, SUPABASE_BUCKET, BATCH_SIZE

logging.basicConfig(level=logging.INFO)

app = FastAPI()
_batch_running = False
_batch_doc_ids: list[str] = []


@app.on_event("startup")
async def on_startup():
    await reset_stale_processing()
    logging.info("Stale processing documents reset to pending")

_HTML_PATH = Path(__file__).parent / "static" / "index.html"


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/", response_class=HTMLResponse)
async def index():
    return _HTML_PATH.read_text()



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
            if await document_exists(file_hash):
                logging.info("Duplicate file skipped: %s", file.filename)
                results.append({"file": file.filename, "status": "duplicate"})
                continue

            await upload_to_bucket(SUPABASE_BUCKET, file.filename, contents)
            await insert_document(SUPABASE_BUCKET + "/" + file.filename, file.filename, file_hash)
            logging.info("Uploaded %s to bucket", file.filename)
            results.append({"file": file.filename, "status": "uploaded"})

        except Exception as e:
            logging.error("Failed to upload %s: %s", file.filename, e)
            results.append({"file": file.filename, "status": "error", "detail": str(e)})
            
    return results


async def _run_pipeline(docs: list[dict], model: str, batch_size: int) -> None:
    global _batch_running
    try:
        pipeline = InvoicePipeline(model=model, concurrency=batch_size)
        await pipeline.run_batch(docs)
    finally:
        _batch_running = False


@app.post("/invoices/batch", status_code=202)
async def batch_invoices(
    background_tasks: BackgroundTasks,
    model: str = DEFAULT_MODEL,
    batch_size: int = BATCH_SIZE,
):
    global _batch_running
    if model not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"Model must be one of: {', '.join(ALLOWED_MODELS)}")
    if _batch_running:
        raise HTTPException(status_code=409, detail="A batch is already running")

    docs = await get_pending_documents()
    if not docs:
        return {"status": "nothing_to_process", "queued": 0}

    _batch_running = True
    _batch_doc_ids.clear()
    _batch_doc_ids.extend(doc["id"] for doc in docs)
    background_tasks.add_task(_run_pipeline, docs, model, batch_size)
    return {"status": "started", "queued": len(docs)}


@app.get("/invoices/batch/status")
async def batch_status():
    counts = await get_status_counts(_batch_doc_ids)
    return {"running": _batch_running, "counts": counts}
