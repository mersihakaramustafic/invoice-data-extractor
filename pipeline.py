import asyncio
import logging
from langfuse import observe, get_client
from utils.pdf_reader import read_pdf_from_bytes
from utils.scoring import completeness_score
from llm.extractor import extract_invoice_data
from db.invoice_store import store_invoice
from db.storage_client import download_invoice, delete_from_bucket
from db.document_store import mark_processing, mark_processed, mark_failed, log_event
from schemas.invoice import Invoice
from constants import SUPABASE_BUCKET


@observe(name="process_invoice")
async def _extract_and_observe(file_bytes: bytes, model: str) -> Invoice:
    text = read_pdf_from_bytes(file_bytes)
    logging.info("=== EXTRACTED PDF TEXT ===\n%s\n==========================", text)
    result = await extract_invoice_data(text, model=model)
    score, comment = completeness_score(result)
    get_client().score_current_trace(name="completeness", value=score, comment=comment)
    return result


class InvoicePipeline:
    def __init__(self, model: str, concurrency: int):
        self.model = model
        self._concurrency = concurrency

    async def run_batch(self, docs: list[dict]) -> list[dict]:
        results = []
        for i in range(0, len(docs), self._concurrency):
            batch = docs[i:i + self._concurrency]
            logging.info(
                "Processing batch %d/%d (%d files)",
                i // self._concurrency + 1,
                -(-len(docs) // self._concurrency),
                len(batch),
            )
            batch_results = await asyncio.gather(*[self._process(doc) for doc in batch])
            results.extend(batch_results)
        return results

    async def _process(self, doc: dict) -> dict:
        doc_id = doc["id"]
        file_name = doc["file_name"]
        try:
            await mark_processing(doc_id)
            await log_event(file_name, "info", "processing_started", document_id=doc_id)

            file_bytes = await download_invoice(SUPABASE_BUCKET, file_name)
            result = await _extract_and_observe(file_bytes, model=self.model)
            result.file_path = doc["file_path"]
            stored = await store_invoice(result)
            await mark_processed(doc_id)
            await delete_from_bucket(SUPABASE_BUCKET, file_name)

            status = "success" if stored else "skipped"
            await log_event(file_name, "info", f"processing_{status}", document_id=doc_id)
            return {"file_name": file_name, "status": status}
        except Exception as e:
            logging.error("FAILED %s: %s", file_name, e)
            await mark_failed(doc_id, str(e), doc["retry_count"])
            await log_event(file_name, "error", "processing_failed", document_id=doc_id, message=str(e))
            return {"file_name": file_name, "status": "failed", "error": str(e)}
