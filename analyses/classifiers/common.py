"""Shared audit helpers for the OpenAI trial-stoppage rescore scripts.

Used by ``rescore_trial_stoppage.py`` and
``rescore_trial_stoppage_openai_batch.py``:

- ``CallResult``: one model response plus the exact prompts and parameters.
- ``PRICING``: USD per 1M input / output tokens for the OpenAI models they call.
- ``extract_json_block``: first JSON object in a response text.
- ``annotate``: adds the audit fields (run id, provider, model, prompt version,
  exact prompts, raw response, usage, cost) that
  ``db/13_ingest_llm_outputs.py`` reads.
- ``append_jsonl`` / ``read_jsonl``: append one JSON row; read rows, skipping
  blank and malformed lines and yielding nothing for a missing file.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


# USD per 1M input / output tokens.
PRICING = {
    "gpt-5.6-luna": {"input": 0.2, "output": 1.2},
    "gpt-5.6-terra": {"input": 2.0, "output": 12.0},
}


@dataclass
class CallResult:
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    model: str
    provider_request_id: str | None
    system_prompt: str
    user_prompt: str
    max_tokens: int
    temperature: float
    provider: str = "openai"


def extract_json_block(text: str) -> dict:
    """Extract the first JSON object from an LLM response.

    Robust to code fences and preamble. Raises if no valid JSON found.
    """
    text = text.strip()
    if text.startswith("```"):
        # strip fence
        parts = text.split("```")
        for p in parts:
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                text = p
                break
    # Grab from first { to matching }
    start = text.find("{")
    if start < 0:
        raise ValueError(f"no JSON object in response: {text[:200]}")
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError(f"unterminated JSON in response: {text[start:start+200]}")


def annotate(row: dict, result: CallResult, prompt_version: str) -> dict:
    """Add the canonical audit-trail fields to a parsed classifier row.

    Every classifier row records the exact prompts and raw response in addition
    to model, version, usage, and cost. These underscore-prefixed fields are
    audit metadata added by the caller; the LLM never produces them.
    """
    row["_run_id"] = str(uuid.uuid4())
    row["_provider"] = result.provider
    row["_provider_request_id"] = result.provider_request_id
    row["_model"] = result.model
    row["_prompt_version"] = prompt_version
    row["_system_prompt"] = result.system_prompt
    row["_user_prompt"] = result.user_prompt
    row["_raw_response"] = result.text
    row["_model_parameters"] = {
        "max_tokens": result.max_tokens,
        "temperature": result.temperature,
    }
    row["_input_tokens"] = result.input_tokens
    row["_output_tokens"] = result.output_tokens
    row["_cost_usd"] = round(result.cost_usd, 6)
    return row


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(obj) + "\n")


def read_jsonl(path: Path) -> Iterator[dict]:
    if not path.exists():
        return iter(())
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                pass
