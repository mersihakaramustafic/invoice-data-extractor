from db.db_client import supabase_client
from schemas.invoice import Invoice


def store_invoice(invoice: Invoice):
    invoice_data = invoice.model_dump(exclude={"line_items"})
    response = supabase_client.table("invoice").insert(invoice_data).execute()
    invoice_id = response.data[0]["id"]

    for item in invoice.line_items:
        line_item_data = item.model_dump()
        line_item_data["invoice_id"] = invoice_id
        supabase_client.table("line_item").insert(line_item_data).execute()
