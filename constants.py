ALLOWED_MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-4.1-mini"]
DEFAULT_MODEL = "gpt-4.1-mini"

REQUIRED_FIELDS = [
    "invoice_number", "invoice_date", "seller_name", "seller_address", "seller_tax_id",
    "client_name", "client_address", "client_tax_id", "currency", "subtotal", "total_amount",
]
