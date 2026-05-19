"""
Stability evaluation using Langfuse Datasets.

Usage:
  python eval.py                        # run with default model
  python eval.py --model gpt-4.1        # run with a specific model
  python eval.py --dataset my-dataset   # run a named dataset

Setup:
  1. In Langfuse, create a dataset named "invoice-stability" (or pass --dataset).
  2. Add items using: python add_dataset_items.py path/to/*.pdf
  3. Run this script; results appear in the Langfuse Dataset Runs UI.
"""
from dotenv import load_dotenv
load_dotenv()

import argparse
import logging
import datetime
from langfuse import get_client
from langfuse.experiment import Evaluation
from llm.extractor import extract_invoice_data
from utils.scoring import completeness_score, schema_validity_score, hallucination_score
from schemas.invoice import Invoice
from constants import DEFAULT_MODEL, ALLOWED_MODELS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DEFAULT_DATASET = "invoice-stability"


def _to_invoice(output: dict) -> Invoice:
    return Invoice(**output)


def evaluate_completeness(*, output, **kwargs):
    if not output:
        return Evaluation(name="completeness", value=0, comment="No output")
    score, comment = completeness_score(_to_invoice(output))
    return Evaluation(name="completeness", value=score, comment=comment)


def evaluate_schema_validity(*, output, **kwargs):
    if not output:
        return Evaluation(name="schema_validity", value=0, comment="No output")
    score, comment = schema_validity_score(_to_invoice(output))
    return Evaluation(name="schema_validity", value=score, comment=comment)


def evaluate_hallucination(*, input, output, **kwargs):
    if not output:
        return Evaluation(name="hallucination", value=0, comment="No output")
    score, comment = hallucination_score(_to_invoice(output), input["text"])
    return Evaluation(name="hallucination", value=score, comment=comment)


def main(dataset_name: str, model: str, run_name: str):
    lf = get_client()
    dataset = lf.get_dataset(dataset_name)

    if not dataset.items:
        logging.warning("Dataset '%s' has no items.", dataset_name)
        return

    logging.info("Running %d item(s) from dataset '%s' with model=%s", len(dataset.items), dataset_name, model)

    async def task(*, item, **kwargs):
        result = await extract_invoice_data(item.input["text"], model=model)
        return result.model_dump() if result else None

    result = dataset.run_experiment(
        name=run_name,
        task=task,
        evaluators=[evaluate_completeness, evaluate_schema_validity, evaluate_hallucination],
    )

    lf.flush()
    logging.info("Done. View results: %s", result.dataset_run_url)
    print(result.format())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=ALLOWED_MODELS)
    parser.add_argument("--run-name", default=None)
    args = parser.parse_args()

    run_name = args.run_name or f"{args.model}/{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M')}"
    main(args.dataset, args.model, run_name)
