from openai import OpenAI
from llm.prompts import SYSTEM_PROMPT, USER_PROMPT
from schemas.invoice import Invoice

client = OpenAI()


def extract_invoice_data(invoice_text: str):
    user_prompt = USER_PROMPT.format(invoice_text=invoice_text)

    response = client.responses.parse(
        model="gpt-5.4-mini",
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        text_format=Invoice
    )

    return response.output_parsed
