from openai import OpenAI
from langfuse import observe, get_client
from schemas.invoice import Invoice
import logging

client = OpenAI()


@observe(as_type="generation", capture_output=False)
def extract_invoice_data(invoice_text: str, model: str = "gpt-4.1-mini"):
    langfuse = get_client()

    system_prompt = langfuse.get_prompt("system-prompt-invoice-extraction", label="production", cache_ttl_seconds=600)
    user_prompt = langfuse.get_prompt("user-prompt-invoice-extraction", label="production", cache_ttl_seconds=600)

    system_text = system_prompt.compile()
    user_text = user_prompt.compile(invoice_text=invoice_text)
    
    if "{invoice_text}" in user_text:
        user_text = user_text.replace("{invoice_text}", invoice_text)

    logging.info("=== SYSTEM PROMPT ===\n%s", system_text)
    logging.info("=== USER PROMPT ===\n%s", user_text)

    langfuse.update_current_generation(
        input=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text}
        ],
        model=model,
        prompt=user_prompt,
    )

    response = client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text}
        ],
        text_format=Invoice,
        temperature=0,
    )

    langfuse.update_current_generation(
        output=response.output_parsed.model_dump() if response.output_parsed else None,
        usage_details={
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
        }
    )

    return response.output_parsed
