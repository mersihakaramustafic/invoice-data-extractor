# Invoice Data Extractor

![Invoice Extractor UI](static/UI%20Screenshot.png)

A web app that extracts structured data from PDF invoices using OpenAI GPT models. Upload PDFs via the UI, trigger processing on demand, and get parsed invoice fields stored in Supabase.

## Features

- Upload PDF invoices via drag-and-drop UI (duplicate detection via SHA-256 hash)
- Extracts seller, client, line items, totals, VAT, and currency
- Background batch processing with live progress tracking in the UI
- Concurrent LLM calls with rate-limit retry (exponential backoff via tenacity)
- Per-invoice quality scores tracked in Langfuse: completeness, schema validity, hallucination
- Document lifecycle tracked in Supabase (`invoice_documents`, `invoice_logs`)
- Stale processing records reset automatically on server startup

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI (Python) |
| LLM | OpenAI GPT-4.1 / GPT-4.1-mini |
| Observability | Langfuse |
| Database | Supabase (PostgreSQL + Storage) |

## Extracted Fields

```json
{
  "invoice_number": "string",
  "invoice_date": "YYYY-MM-DD",
  "seller_name": "string",
  "seller_address": "string",
  "seller_tax_id": "string",
  "client_name": "string",
  "client_address": "string",
  "client_tax_id": "string",
  "currency": "USD",
  "subtotal": 100.00,
  "vat": 20.00,
  "total_amount": 120.00,
  "line_items": [
    { "no": 1, "description": "string", "quantity": 1, "total_amount": 100.00 }
  ]
}
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serves the UI |
| `POST` | `/invoices/upload` | Upload one or more PDF files |
| `POST` | `/invoices/batch` | Start background processing of all pending invoices |
| `GET` | `/invoices/batch/status` | Poll processing progress for the current batch |

### `POST /invoices/batch`
Returns `202` immediately and processes invoices in the background. Returns `409` if a batch is already running.

```json
{ "status": "started", "queued": 89 }
```

### `GET /invoices/batch/status`
```json
{
  "running": true,
  "counts": { "pending": 40, "processing": 5, "processed": 44, "failed": 0 }
}
```

## Quality Scoring

Each processed invoice is scored in Langfuse across three dimensions:

| Score | What it measures |
|---|---|
| **Completeness** | Fraction of required fields that were extracted |
| **Schema validity** | Date parseable, amounts positive, math consistent, currency format valid |
| **Hallucination** | Fraction of extracted values that can be found verbatim in the source PDF text |

## Rate Limit Handling

OpenAI API calls are wrapped with `tenacity` retry logic. On `RateLimitError`, `APIStatusError`, or `APITimeoutError`, the call is retried up to 3 times with exponential backoff (2s–30s). After 3 failures the document is marked `failed` and counted against its `retry_count` (max 3 retries before the document is excluded from future batches).

## Environment Variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase service role key |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key |

## Running Locally

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in env vars
uvicorn api:app --reload
```

Open `http://localhost:8000` in your browser.
