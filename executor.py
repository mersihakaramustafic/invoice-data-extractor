from openai import OpenAI
from prompts import SYSTEM_PROMPT, USER_PROMPT
from validator import Invoice


def extract_invoice_data(invoice_text: str):
    client = OpenAI()
    user_prompt = USER_PROMPT.format(invoice_text=invoice_text)

    response = client.responses.parse(
        model="gpt-4o-2024-08-06",
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        text_format=Invoice
    )

    event = response.output_parsed
    return event
