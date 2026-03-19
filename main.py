from dotenv import load_dotenv
load_dotenv()

import glob
from utils.pdf_reader import read_pdf
from llm.extractor import extract_invoice_data
from db.invoice_store import store_invoice

LIMIT = 10  # process only 10 invoices

invoice_files = sorted(glob.glob("data/invoice_*.pdf"))[:LIMIT]

for invoice_file in invoice_files:
    print(f"\nProcessing: {invoice_file}")
    text = read_pdf(invoice_file)
    result = extract_invoice_data(text)
    print(result)
    store_invoice(result)
