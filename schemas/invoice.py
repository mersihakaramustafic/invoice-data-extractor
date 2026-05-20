from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from schemas.line_item import LineItem


def _to_float(v):
    if isinstance(v, str):
        return float(v.replace(",", ".").replace(" ", ""))
    return v


class Invoice(BaseModel):
    invoice_number: str = Field(description="Invoice number copied exactly as it appears — do not reformat or add prefixes like INV-")
    invoice_date: str
    seller_name: str
    seller_address: str
    seller_tax_id: str
    client_name: str
    client_address: str
    client_tax_id: str
    line_items: List[LineItem]
    subtotal: float
    vat: float
    total_amount: float
    currency: str
    file_path: Optional[str] = None

    @field_validator("subtotal", "vat", "total_amount", mode="before")
    @classmethod
    def coerce_numeric(cls, v):
        return _to_float(v)