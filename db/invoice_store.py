from db.db_client import get_supabase_client
from schemas.invoice import Invoice


async def store_invoice(invoice: Invoice):
    supabase_client = await get_supabase_client()
    invoice_data = invoice.model_dump(exclude={"line_items"})
    response = await supabase_client.table("invoice").insert(invoice_data).execute()
    invoice_id = response.data[0]["id"]

    for item in invoice.line_items:
        line_item_data = item.model_dump()
        line_item_data["invoice_id"] = invoice_id
        await supabase_client.table("line_item").insert(line_item_data).execute()
