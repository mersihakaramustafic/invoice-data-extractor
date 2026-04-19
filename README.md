# Invoice Data Extractor

A web app that extracts structured data from PDF invoices using GPT-4o-mini. Upload a PDF, get back parsed invoice fields stored in Supabase.

## Features

- Upload PDF invoices via drag-and-drop UI
- Extracts seller, client, line items, totals, VAT, and currency
- Stores results in Supabase
- LLM observability via Langfuse (prompt management + generation tracing)
- Deployed on Vercel

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI (Python) |
| LLM | OpenAI GPT-4o-mini |
| Observability | Langfuse |
| Database | Supabase (PostgreSQL) |
| Deployment | Vercel |

## Project Structure

```
api.py                  # FastAPI app — HTTP endpoints
main.py                 # Batch script for local bulk processing
static/index.html       # Frontend UI
llm/
  extractor.py          # Calls OpenAI, manages Langfuse tracing
  prompts.py            # Prompt templates (fallback; production prompts live in Langfuse)
schemas/
  invoice.py            # Invoice Pydantic model
  line_item.py          # LineItem Pydantic model
db/
  db_client.py          # Raw HTTP calls to Supabase REST API
  invoice_store.py      # Persists invoice + line items to Supabase
utils/
  pdf_reader.py         # Extracts text from PDF bytes using pypdf
```

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

## Batch Processing

To process multiple PDFs from a local `data/` directory:

```bash
python main.py
```

Processes up to 10 files matching `data/invoice_*.pdf`.

## Deployment

The app is deployed via Vercel using the `@vercel/python` builder. On push to `main`, Vercel builds and deploys `api.py` automatically. Set all environment variables in the Vercel project settings.
