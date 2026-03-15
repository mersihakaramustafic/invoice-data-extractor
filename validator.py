from pydantic import BaseModel
from typing import List

class LineItem(BaseModel):
    no: int
    description: str
    quantity: float
    total_amount: float

class Invoice(BaseModel):
    invoice_number: str
    invoice_date: str
    seller_name: str
    seller_address: str
    seller_tax_id: str
    client_name: str
    client_address: str
    client_tax_id: str
    line_items: List[LineItem]
    net_total: float
    vat: float
    total_amount: float
    currency: str