"""
Add PDF invoices to a Langfuse dataset as evaluation items.

Usage:
  python add_dataset_items.py data/eval/*.pdf
  python add_dataset_items.py invoice_1.pdf invoice_2.pdf --dataset my-dataset
"""
from dotenv import load_dotenv
load_dotenv()

import argparse
import logging
from pathlib import Path
from langfuse import get_client
from utils.pdf_reader import read_pdf_from_bytes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DEFAULT_DATASET = "invoice-stability"


def main(pdf_paths: list[Path], dataset_name: str):
    lf = get_client()

    lf.create_dataset(name=dataset_name)

    added = 0
    for path in pdf_paths:
        if not path.exists():
            logging.warning("File not found, skipping: %s", path)
            continue
        text = read_pdf_from_bytes(path.read_bytes())
        lf.create_dataset_item(
            dataset_name=dataset_name,
            input={"text": text, "file_name": path.name},
        )
        logging.info("Added: %s", path.name)
        added += 1

    lf.flush()
    logging.info("Done. %d item(s) added to dataset '%s'.", added, dataset_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pdfs", nargs="+", type=Path, help="PDF files to add")
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    args = parser.parse_args()

    main(args.pdfs, args.dataset)
