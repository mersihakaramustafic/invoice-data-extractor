import os
from supabase import create_client
from validator import Invoice

def get_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url:
        raise ValueError("SUPABASE_URL is missing")
    if not key:
        raise ValueError("SUPABASE_KEY is missing")

    return create_client(url, key)


def store_invoice(invoice: Invoice):
    supabase = get_client()

    invoice_data = invoice.model_dump(exclude={"line_items"})
    response = supabase.table("invoice").insert(invoice_data).execute()
    invoice_id = response.data[0]["id"]

    for item in invoice.line_items:
        line_item_data = item.model_dump()
        line_item_data["invoice_id"] = invoice_id
        supabase.table("line_item").insert(line_item_data).execute()