from db.db_client import insert_invoice, insert_line_item
from schemas.invoice import Invoice


def store_invoice(invoice: Invoice):
    invoice_data = invoice.model_dump(exclude={"line_items"})
    invoice_id = insert_invoice(invoice_data)

    for item in invoice.line_items:
        line_item_data = item.model_dump()
        line_item_data["invoice_id"] = invoice_id
        insert_line_item(line_item_data)
