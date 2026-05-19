import logging
import re
from datetime import datetime
from schemas.invoice import Invoice
from constants import REQUIRED_FIELDS

_DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y", "%B %d, %Y", "%d %B %Y"]
_MATH_TOLERANCE = 0.02


def completeness_score(invoice: Invoice) -> tuple[float, str]:
    filled = sum(1 for f in REQUIRED_FIELDS if getattr(invoice, f) is not None)
    if invoice.line_items:
        filled += 1
    total = len(REQUIRED_FIELDS) + 1
    score = round(filled / total, 2)
    comment = f"{filled}/{total} fields extracted"
    logging.info("Completeness score: %s (%s)", score, comment)
    return score, comment


def schema_validity_score(invoice: Invoice) -> tuple[float, str]:
    checks = {
        "date_parseable": _is_valid_date(invoice.invoice_date),
        "total_positive": invoice.total_amount is not None and invoice.total_amount > 0,
        "subtotal_positive": invoice.subtotal is not None and invoice.subtotal > 0,
        "math_consistent": _math_checks_out(invoice),
        "currency_format": bool(invoice.currency and re.fullmatch(r"[A-Z]{3}", invoice.currency)),
        "has_line_items": bool(invoice.line_items),
    }
    passed = sum(checks.values())
    total = len(checks)
    score = round(passed / total, 2)
    failed = [k for k, v in checks.items() if not v]
    comment = f"{passed}/{total} checks passed" + (f"; failed: {', '.join(failed)}" if failed else "")
    logging.info("Schema validity score: %s (%s)", score, comment)
    return score, comment


_CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£", "CHF": "chf", "JPY": "¥"}


def hallucination_score(invoice: Invoice, source_text: str) -> tuple[float, str]:
    normalized_source = re.sub(r"\s+", " ", source_text.lower())
    ungrounded = []

    text_fields = {
        "invoice_number": invoice.invoice_number,
        "seller_name": invoice.seller_name,
        "seller_tax_id": invoice.seller_tax_id,
        "client_name": invoice.client_name,
        "client_tax_id": invoice.client_tax_id,
    }
    numeric_fields = {
        "total_amount": invoice.total_amount,
        "subtotal": invoice.subtotal,
    }

    checks = {}
    for name, value in text_fields.items():
        if value:
            checks[name] = value.lower().strip() in normalized_source

    for name, value in numeric_fields.items():
        if value is not None:
            checks[name] = _number_grounded(value, normalized_source)

    if invoice.currency:
        symbol = _CURRENCY_SYMBOLS.get(invoice.currency.upper(), "")
        checks["currency"] = (
            invoice.currency.lower() in normalized_source
            or (symbol and symbol.lower() in normalized_source)
        )

    ungrounded = [k for k, v in checks.items() if not v]
    grounded = sum(checks.values())
    total = len(checks)
    score = round(grounded / total, 2) if total else 1.0
    comment = f"{grounded}/{total} fields grounded in source text"
    if ungrounded:
        comment += f"; not found: {', '.join(ungrounded)}"
    logging.info("Hallucination score: %s (%s)", score, comment)
    return score, comment


def _number_grounded(value: float, source: str) -> bool:
    candidates = {
        str(value),
        f"{value:.2f}",
        f"{int(value)}" if value == int(value) else f"{value:.2f}",
        f"{value:,.2f}",
        f"{value:,.2f}".replace(",", ".").replace("..", "."),
        # European formats
        f"{value:,.2f}".replace(",", " "),
        f"{value:.2f}".replace(".", ","),
        f"{value:,.2f}".replace(",", " ").replace(".", ","),
    }
    return any(c.lower() in source for c in candidates)


def _is_valid_date(value: str | None) -> bool:
    if not value:
        return False
    for fmt in _DATE_FORMATS:
        try:
            datetime.strptime(value.strip(), fmt)
            return True
        except ValueError:
            continue
    return False


def _math_checks_out(invoice: Invoice) -> bool:
    if invoice.subtotal is None or invoice.vat is None or invoice.total_amount is None:
        return False
    expected = invoice.subtotal + invoice.vat
    return abs(expected - invoice.total_amount) <= _MATH_TOLERANCE * invoice.total_amount
