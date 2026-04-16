from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from langfuse import observe
from utils.pdf_reader import read_pdf_from_bytes
from llm.extractor import extract_invoice_data
from db.invoice_store import store_invoice
from schemas.invoice import Invoice

app = FastAPI()

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Invoice Extractor</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f5f5f5;
      min-height: 100vh;
      display: flex;
      align-items: flex-start;
      justify-content: center;
      padding: 48px 16px;
    }
    .card {
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08);
      padding: 36px;
      width: 100%;
      max-width: 680px;
    }
    h1 { font-size: 22px; font-weight: 600; margin-bottom: 24px; color: #111; }
    .upload-area {
      border: 2px dashed #d1d5db;
      border-radius: 8px;
      padding: 32px;
      text-align: center;
      cursor: pointer;
      transition: border-color 0.2s, background 0.2s;
      margin-bottom: 16px;
    }
    .upload-area:hover, .upload-area.drag-over { border-color: #6366f1; background: #f5f3ff; }
    .upload-area input { display: none; }
    .upload-icon { font-size: 36px; margin-bottom: 8px; }
    .upload-area p { color: #6b7280; font-size: 14px; }
    .upload-area .file-name { color: #6366f1; font-weight: 500; margin-top: 6px; }
    button {
      width: 100%;
      padding: 12px;
      background: #6366f1;
      color: #fff;
      border: none;
      border-radius: 8px;
      font-size: 15px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s;
    }
    button:hover:not(:disabled) { background: #4f46e5; }
    button:disabled { background: #a5b4fc; cursor: not-allowed; }
    .error {
      margin-top: 16px;
      padding: 12px 16px;
      background: #fef2f2;
      border: 1px solid #fecaca;
      border-radius: 8px;
      color: #dc2626;
      font-size: 14px;
      display: none;
    }
    .result { margin-top: 24px; display: none; }
    .result h2 { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #111; }
    .section { margin-bottom: 20px; }
    .section-title { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #9ca3af; margin-bottom: 8px; }
    .fields { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .field label { font-size: 11px; color: #9ca3af; display: block; margin-bottom: 2px; }
    .field span { font-size: 14px; color: #111; font-weight: 500; }
    table { width: 100%; border-collapse: collapse; font-size: 14px; }
    thead th { text-align: left; font-size: 12px; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.05em; padding: 6px 8px; border-bottom: 1px solid #e5e7eb; }
    tbody td { padding: 8px; border-bottom: 1px solid #f3f4f6; color: #111; }
    .totals { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; margin-top: 12px; }
    .totals div { font-size: 14px; color: #374151; }
    .totals .total { font-size: 16px; font-weight: 700; color: #111; }
    .spinner { display: inline-block; width: 18px; height: 18px; border: 2px solid #fff; border-top-color: transparent; border-radius: 50%; animation: spin 0.7s linear infinite; vertical-align: middle; margin-right: 8px; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
<div class="card">
  <h1>Invoice Extractor</h1>

  <div class="upload-area" id="dropZone">
    <input type="file" id="fileInput" accept=".pdf" />
    <div class="upload-icon">📄</div>
    <p>Drag &amp; drop a PDF here, or <strong>click to browse</strong></p>
    <div class="file-name" id="fileName"></div>
  </div>

  <button id="uploadBtn" disabled>Upload &amp; Extract</button>
  <div class="error" id="error"></div>

  <div class="result" id="result">
    <h2>Extracted Data</h2>

    <div class="section">
      <div class="section-title">Invoice</div>
      <div class="fields">
        <div class="field"><label>Number</label><span id="r-invoice_number"></span></div>
        <div class="field"><label>Date</label><span id="r-invoice_date"></span></div>
        <div class="field"><label>Currency</label><span id="r-currency"></span></div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">Seller</div>
      <div class="fields">
        <div class="field"><label>Name</label><span id="r-seller_name"></span></div>
        <div class="field"><label>Tax ID</label><span id="r-seller_tax_id"></span></div>
        <div class="field" style="grid-column: span 2"><label>Address</label><span id="r-seller_address"></span></div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">Client</div>
      <div class="fields">
        <div class="field"><label>Name</label><span id="r-client_name"></span></div>
        <div class="field"><label>Tax ID</label><span id="r-client_tax_id"></span></div>
        <div class="field" style="grid-column: span 2"><label>Address</label><span id="r-client_address"></span></div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">Line Items</div>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Description</th>
            <th>Qty</th>
            <th>Amount</th>
          </tr>
        </thead>
        <tbody id="r-line_items"></tbody>
      </table>
      <div class="totals">
        <div>Subtotal: <strong id="r-subtotal"></strong></div>
        <div>VAT: <strong id="r-vat"></strong></div>
        <div class="total">Total: <span id="r-total_amount"></span></div>
      </div>
    </div>
  </div>
</div>

<script>
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const fileNameEl = document.getElementById('fileName');
  const uploadBtn = document.getElementById('uploadBtn');
  const errorEl = document.getElementById('error');
  const resultEl = document.getElementById('result');
  let selectedFile = null;

  dropZone.addEventListener('click', () => fileInput.click());
  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) setFile(file);
  });
  fileInput.addEventListener('change', () => { if (fileInput.files[0]) setFile(fileInput.files[0]); });

  function setFile(file) {
    if (!file.name.endsWith('.pdf')) { showError('Only PDF files are accepted.'); return; }
    selectedFile = file;
    fileNameEl.textContent = file.name;
    uploadBtn.disabled = false;
    errorEl.style.display = 'none';
    resultEl.style.display = 'none';
  }

  uploadBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<span class="spinner"></span>Extracting…';
    errorEl.style.display = 'none';
    resultEl.style.display = 'none';

    const form = new FormData();
    form.append('file', selectedFile);

    try {
      const res = await fetch('/invoices/upload', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) { showError(data.detail || 'Upload failed.'); return; }
      renderResult(data);
    } catch (e) {
      showError('Network error: ' + e.message);
    } finally {
      uploadBtn.disabled = false;
      uploadBtn.innerHTML = 'Upload &amp; Extract';
    }
  });

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.style.display = 'block';
  }

  function set(id, val) { document.getElementById('r-' + id).textContent = val ?? '—'; }

  function renderResult(d) {
    set('invoice_number', d.invoice_number);
    set('invoice_date', d.invoice_date);
    set('currency', d.currency);
    set('seller_name', d.seller_name);
    set('seller_tax_id', d.seller_tax_id);
    set('seller_address', d.seller_address);
    set('client_name', d.client_name);
    set('client_tax_id', d.client_tax_id);
    set('client_address', d.client_address);
    set('subtotal', fmt(d.subtotal, d.currency));
    set('vat', fmt(d.vat, d.currency));
    set('total_amount', fmt(d.total_amount, d.currency));

    const tbody = document.getElementById('r-line_items');
    tbody.innerHTML = (d.line_items || []).map(item =>
      `<tr><td>${item.no}</td><td>${item.description}</td><td>${item.quantity}</td><td>${fmt(item.total_amount, d.currency)}</td></tr>`
    ).join('');

    resultEl.style.display = 'block';
  }

  function fmt(val, currency) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: currency || 'USD' }).format(val);
  }
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


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
