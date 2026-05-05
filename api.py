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
from db.storage_client import list_invoices, download_invoice
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


@app.post("/invoices/upload", response_model=Invoice)
async def upload_invoice(file: UploadFile = File(...), model: str = DEFAULT_MODEL):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    if model not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"Model must be one of: {', '.join(ALLOWED_MODELS)}")

    logging.info("Uploading invoice: filename=%s model=%s", file.filename, model)
    contents = await file.read()
    result = extract_and_observe(contents, model=model)
    result.file_path = file.filename
    store_invoice(result)
    return result


@app.post("/invoices/batch")
async def batch_invoices(
    model: str = DEFAULT_MODEL,
    limit: int = BATCH_LIMIT,
    batch_size: int = BATCH_SIZE,
):
    if model not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"Model must be one of: {', '.join(ALLOWED_MODELS)}")

    files = list_invoices(SUPABASE_BUCKET)[:limit]
    if not files:
        return {"total": 0, "succeeded": 0, "skipped": 0, "failed": 0, "errors": []}

    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=batch_size)
    succeeded = 0
    skipped = 0
    failed = 0
    errors = []

    def process(filename: str) -> bool:
        file_bytes = download_invoice(SUPABASE_BUCKET, filename)
        result = extract_and_observe(file_bytes, model=model)
        result.file_path = filename
        return store_invoice(result)

    async def process_one(filename: str):
        nonlocal succeeded, skipped, failed
        try:
            stored = await loop.run_in_executor(executor, process, filename)
            if stored:
                succeeded += 1
            else:
                skipped += 1
        except Exception as e:
            failed += 1
            errors.append({"file": filename, "error": str(e)})
            logging.error("FAILED %s: %s", filename, e)

    for i in range(0, len(files), batch_size):
        batch = files[i : i + batch_size]
        logging.info("Processing batch %d/%d (%d files)", i // batch_size + 1, -(-len(files) // batch_size), len(batch))
        await asyncio.gather(*[process_one(f) for f in batch])

    return {"total": len(files), "succeeded": succeeded, "skipped": skipped, "failed": failed, "errors": errors}
