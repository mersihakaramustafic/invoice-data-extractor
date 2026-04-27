from schemas.invoice import Invoice
from constants import REQUIRED_FIELDS


def completeness_score(invoice: Invoice) -> tuple[float, str]:
    filled = sum(1 for f in REQUIRED_FIELDS if getattr(invoice, f) is not None)
    if invoice.line_items:
        filled += 1
    total = len(REQUIRED_FIELDS) + 1  # +1 for line_items
    return round(filled / total, 2), f"{filled}/{total} fields extracted"
