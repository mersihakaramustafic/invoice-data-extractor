from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from langfuse import observe
from utils.pdf_reader import read_pdf_from_bytes
from llm.extractor import extract_invoice_data
from db.invoice_store import store_invoice
from schemas.invoice import Invoice

app = FastAPI()


@observe(name="process_invoice")
def process_invoice(file_bytes: bytes) -> Invoice:
    text = read_pdf_from_bytes(file_bytes)
    result = extract_invoice_data(text)
    store_invoice(result)
    return result


@app.post("/invoices/upload", response_model=Invoice)
async def upload_invoice(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    contents = await file.read()
    return process_invoice(contents)
