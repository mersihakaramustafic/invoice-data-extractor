from dotenv import load_dotenv
load_dotenv()

import asyncio
import glob
import logging
from concurrent.futures import ThreadPoolExecutor
from langfuse import observe
from utils.pdf_reader import read_pdf
from llm.extractor import extract_invoice_data
from db.invoice_store import store_invoice
from constants import DEFAULT_MODEL

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CONCURRENCY = 10
MODEL = DEFAULT_MODEL


@observe(name="process_invoice")
def process_invoice(invoice_file: str):
    text = read_pdf(invoice_file)
    result = extract_invoice_data(text, model=MODEL)
    store_invoice(result)
    return result


async def run_batch(invoice_files: list[str]):
    semaphore = asyncio.Semaphore(CONCURRENCY)
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=CONCURRENCY)
    succeeded = 0
    failed = 0
    total = len(invoice_files)

    async def process(file: str):
        nonlocal succeeded, failed
        async with semaphore:
            try:
                await loop.run_in_executor(executor, process_invoice, file)
                succeeded += 1
            except Exception as e:
                failed += 1
                logging.error("FAILED %s: %s", file, e)
            logging.info("[%d/%d] succeeded=%d failed=%d", succeeded + failed, total, succeeded, failed)

    await asyncio.gather(*[process(f) for f in invoice_files])
    logging.info("Done: %d succeeded, %d failed out of %d", succeeded, failed, total)


if __name__ == "__main__":
    invoice_files = sorted(glob.glob("data/invoice_*.pdf"))
    logging.info("Found %d invoices, concurrency=%d, model=%s", len(invoice_files), CONCURRENCY, MODEL)
    asyncio.run(run_batch(invoice_files))
