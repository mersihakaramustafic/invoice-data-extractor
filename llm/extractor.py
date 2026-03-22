from openai import OpenAI
from langfuse import observe, get_client
from schemas.invoice import Invoice

client = OpenAI()


@observe(as_type="generation", capture_output=False)
def extract_invoice_data(invoice_text: str):
    langfuse = get_client()

    system_prompt = langfuse.get_prompt("system-prompt-invoice-extraction", label="production")
    user_prompt = langfuse.get_prompt("user-prompt-invoice-extraction", label="production")

    system_text = system_prompt.compile()
    user_text = user_prompt.compile(invoice_text=invoice_text)

    langfuse.update_current_generation(
        input=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text}
        ],
        model="gpt-4o-mini",
        prompt=user_prompt,
    )

    response = client.responses.parse(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text}
        ],
        text_format=Invoice
    )

    langfuse.update_current_generation(
        output=response.output_parsed.model_dump() if response.output_parsed else None,
        usage_details={
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
        }
    )

    return response.output_parsed
