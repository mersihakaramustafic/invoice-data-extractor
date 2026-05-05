import logging
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader


def read_pdf_from_bytes(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    logging.info("Reading PDF: %d page(s)", len(reader.pages))
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    logging.info("Extracted %d characters from PDF", len(text))
    return text


def read_pdf(file_path: str) -> str:
    logging.info("Reading PDF from path: %s", file_path)
    return read_pdf_from_bytes(Path(file_path).read_bytes())