from dotenv import load_dotenv
load_dotenv()

import logging
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from langfuse import observe, get_client
from utils.pdf_reader import read_pdf_from_bytes
from llm.extractor import extract_invoice_data
from db.invoice_store import store_invoice
from schemas.invoice import Invoice

logging.basicConfig(level=logging.INFO)

app = FastAPI()

HTML = (Path(__file__).parent / "static" / "index.html").read_text()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


ALLOWED_MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-4.1-mini"]


REQUIRED_FIELDS = [
    "invoice_number", "invoice_date", "seller_name", "seller_address", "seller_tax_id",
    "client_name", "client_address", "client_tax_id", "currency", "subtotal", "total_amount",
]


def _completeness_score(invoice: Invoice) -> tuple[float, str]:
    filled = sum(1 for f in REQUIRED_FIELDS if getattr(invoice, f) is not None)
    if invoice.line_items:
        filled += 1
    total = len(REQUIRED_FIELDS) + 1  # +1 for line_items
    return round(filled / total, 2), f"{filled}/{total} fields extracted"


@observe(name="process_invoice")
def extract_and_observe(file_bytes: bytes, model: str) -> Invoice:
    text = read_pdf_from_bytes(file_bytes)
    logging.info("=== EXTRACTED PDF TEXT ===\n%s\n==========================", text)
    result = extract_invoice_data(text, model=model)
    score, comment = _completeness_score(result)
    get_client().score_current_trace(name="completeness", value=score, comment=comment)
    return result


@app.post("/invoices/upload", response_model=Invoice)
async def upload_invoice(file: UploadFile = File(...), model: str = "gpt-4o-mini"):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    if model not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"Model must be one of: {', '.join(ALLOWED_MODELS)}")

    contents = await file.read()
    result = extract_and_observe(contents, model=model)
    store_invoice(result)
    return result
