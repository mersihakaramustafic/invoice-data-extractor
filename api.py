from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from langfuse import observe
from utils.pdf_reader import read_pdf_from_bytes
from llm.extractor import extract_invoice_data
from db.invoice_store import store_invoice
from schemas.invoice import Invoice

app = FastAPI()

HTML = (Path(__file__).parent / "static" / "index.html").read_text()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


@observe(name="process_invoice")
def extract_and_observe(file_bytes: bytes) -> Invoice:
    text = read_pdf_from_bytes(file_bytes)
    print("=== EXTRACTED PDF TEXT ===")
    print(text)
    print("==========================")
    return extract_invoice_data(text)


@app.post("/invoices/upload", response_model=Invoice)
async def upload_invoice(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    contents = await file.read()
    result = extract_and_observe(contents)
    store_invoice(result)
    return result
