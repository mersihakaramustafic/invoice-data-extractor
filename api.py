from dotenv import load_dotenv
load_dotenv()

import logging
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from db.storage_client import upload_to_bucket
from db.document_store import compute_file_hash, document_exists, insert_document, get_pending_documents
from pipeline import InvoicePipeline
from constants import ALLOWED_MODELS, DEFAULT_MODEL, SUPABASE_BUCKET, BATCH_SIZE, BATCH_LIMIT, MAX_UPLOAD_FILES

logging.basicConfig(level=logging.INFO)

app = FastAPI()

HTML = (Path(__file__).parent / "static" / "index.html").read_text()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML



@app.post("/invoices/upload")
async def upload_invoices(files: list[UploadFile] = File(...)):
    if len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(status_code=400, detail=f"Max {MAX_UPLOAD_FILES} files per request")
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


@app.post("/invoices/batch")
async def batch_invoices(
    model: str = DEFAULT_MODEL,
    limit: int = BATCH_LIMIT,
    batch_size: int = BATCH_SIZE,
):
    if model not in ALLOWED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Model must be one of: {', '.join(ALLOWED_MODELS)}"
        )

    docs = await get_pending_documents(limit)

    if not docs:
        return {
            "total": 0,
            "succeeded": 0,
            "skipped": 0,
            "failed": 0,
            "errors": []
        }

    pipeline = InvoicePipeline(model=model, concurrency=batch_size)

    results = await pipeline.run_batch(docs)

    summary = {
        "total": len(results),
        "succeeded": sum(r["status"] == "success" for r in results),
        "skipped": sum(r["status"] == "skipped" for r in results),
        "failed": sum(r["status"] == "failed" for r in results),
        "errors": [
            {
                "file": r["file_name"],
                "error": r.get("error")
            }
            for r in results
            if r["status"] == "failed"
        ]
    }

    return summary
