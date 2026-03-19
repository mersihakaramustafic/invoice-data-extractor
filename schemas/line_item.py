from pydantic import BaseModel

class LineItem(BaseModel):
    no: int
    description: str
    quantity: float
    total_amount: float