"""Submit and collect auditable trial-stoppage rescores with OpenAI Batches.

Submission starts paid work and requires ``--confirm-paid-batch``. Collection
re-renders every prompt and verifies its hash against the local manifest before
accepting a response.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common import CallResult, PRICING, append_jsonl, read_jsonl
import rescore_trial_stoppage as rescore

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


BATCH_PRICE_MULTIPLIER = 0.5
DEFAULT_BATCH_SIZE = 500
DEFAULT_MAX_BATCH_BYTES = 190_000_000
TERMINAL_STATUSES = {"completed", "failed", "expired", "cancelled"}


def get_client() -> Any:
    if OpenAI is None:
        raise RuntimeError("openai package is not installed")
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI()


def custom_id(nct_id: str) -> str:
    return f"stoppage-{nct_id.lower()}"


def request_for(dossier: dict[str, Any], model: str) -> tuple[dict[str, Any], dict[str, Any]]:
    user_prompt = rescore.render_model_input(dossier)
    request_id = custom_id(str(dossier["nct_id"]))
    request = {
        "custom_id": request_id,
        "method": "POST",
        "url": "/v1/responses",
        "body": {
            "model": model,
            "instructions": rescore.SYSTEM_PROMPT,
            "input": user_prompt,
            "max_output_tokens": rescore.MODEL_MAX_TOKENS,
            "reasoning": {"effort": "none"},
            "text": {"format": rescore.OUTPUT_FORMAT},
            "store": False,
        },
    }
    metadata = {
        "custom_id": request_id,
        "nct_id": dossier["nct_id"],
        "dossier_sha256": dossier["dossier_sha256"],
        "input_sha256": rescore.sha256_text(user_prompt),
    }
    return request, metadata


def completed_nct_ids(path: Path | None) -> set[str]:
    if path is None:
        return set()
    return {str(row.get("nct_id")) for row in read_jsonl(path) if row.get("nct_id")}


def submitted_nct_ids(path: Path) -> set[str]:
    return {
        str(request["nct_id"])
        for batch in read_jsonl(path)
        for request in batch.get("requests") or []
    }


def submit_chunk(client: Any, requests: list[dict], metadata: list[dict], args: argparse.Namespace) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", encoding="utf-8") as handle:
        for request in requests:
            handle.write(json.dumps(request, separators=(",", ":")) + "\n")
        handle.flush()
        with open(handle.name, "rb") as upload:
            input_file = client.files.create(file=upload, purpose="batch")
    batch = client.batches.create(
        input_file_id=input_file.id,
        endpoint="/v1/responses",
        completion_window="24h",
        metadata={"task": "trial_stoppage_rescore", "prompt_version": rescore.PROMPT_VERSION},
    )
    append_jsonl(args.manifest, {
        "schema_version": "trial_stoppage_openai_batch_v1",
        "batch_id": batch.id,
        "input_file_id": input_file.id,
        "status": batch.status,
        "model": args.model,
        "prompt_version": rescore.PROMPT_VERSION,
        "system_prompt_sha256": rescore.sha256_text(rescore.SYSTEM_PROMPT),
        "dossier_schema_version": rescore.DOSSIER_SCHEMA_VERSION,
        "result_schema_version": rescore.RESULT_SCHEMA_VERSION,
        "request_count": len(requests),
        "requests": metadata,
    })
    print(f"submitted batch={batch.id} requests={len(requests)}", flush=True)


def submit(args: argparse.Namespace) -> None:
    if not args.confirm_paid_batch:
        raise SystemExit("batch submission begins paid work; pass --confirm-paid-batch")
    client = get_client()
    skip = submitted_nct_ids(args.manifest) | completed_nct_ids(args.completed_out)
    requests: list[dict] = []
    metadata: list[dict] = []
    request_bytes = 0
    submitted = 0
    for dossier in read_jsonl(args.dossiers):
        nct_id = str(dossier.get("nct_id") or "")
        if not nct_id or nct_id in skip:
            continue
        request, request_metadata = request_for(dossier, args.model)
        size = len(json.dumps(request, separators=(",", ":")).encode("utf-8")) + 1
        if size > args.max_batch_bytes:
            raise ValueError(f"single request {nct_id} exceeds --max-batch-bytes")
        if requests and (
            len(requests) >= args.batch_size or request_bytes + size > args.max_batch_bytes
        ):
            submit_chunk(client, requests, metadata, args)
            submitted += len(requests)
            requests, metadata, request_bytes = [], [], 0
        requests.append(request)
        metadata.append(request_metadata)
        request_bytes += size
    if requests:
        submit_chunk(client, requests, metadata, args)
        submitted += len(requests)
    print(f"submitted_requests={submitted} manifest={args.manifest}")


def dossier_offsets(path: Path) -> dict[str, int]:
    offsets: dict[str, int] = {}
    with path.open("rb") as handle:
        while True:
            offset = handle.tell()
            line = handle.readline()
            if not line:
                break
            if not line.strip():
                continue
            value = json.loads(line)
            nct_id = str(value.get("nct_id") or "")
            if not nct_id or nct_id in offsets:
                raise ValueError(f"invalid or duplicate nct_id in dossier file: {nct_id!r}")
            offsets[nct_id] = offset
    return offsets


def load_dossier(path: Path, offsets: dict[str, int], nct_id: str) -> dict[str, Any]:
    if nct_id not in offsets:
        raise ValueError(f"{nct_id} absent from dossier file")
    with path.open("rb") as handle:
        handle.seek(offsets[nct_id])
        return json.loads(handle.readline())


def batch_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price = PRICING.get(model)
    if not price:
        return 0.0
    return BATCH_PRICE_MULTIPLIER * (
        input_tokens / 1_000_000 * price["input"]
        + output_tokens / 1_000_000 * price["output"]
    )


def collect_batch(
    client: Any,
    batch_row: dict[str, Any],
    args: argparse.Namespace,
    offsets: dict[str, int],
    handled: set[str],
) -> tuple[int, int, float]:
    batch_id = str(batch_row["batch_id"])
    batch = client.batches.retrieve(batch_id)
    counts = batch.request_counts.model_dump() if batch.request_counts else None
    print(f"batch={batch_id} status={batch.status} counts={counts}")
    if batch.status not in TERMINAL_STATUSES:
        return 0, 0, 0.0
    if not batch.output_file_id:
        return 0, int((counts or {}).get("total", 0) or 0), 0.0

    request_index = {str(item["custom_id"]): item for item in batch_row["requests"]}
    content = client.files.content(batch.output_file_id).text
    succeeded = failed = 0
    total_cost = 0.0
    for line in content.splitlines():
        item = json.loads(line)
        cid = str(item.get("custom_id") or "")
        submitted = request_index.get(cid)
        if submitted is None:
            append_jsonl(args.errors_out, {"batch_id": batch_id, "custom_id": cid, "error": "absent from manifest"})
            failed += 1
            continue
        nct_id = str(submitted["nct_id"])
        if nct_id in handled:
            continue
        response = item.get("response") or {}
        body = response.get("body") or {}
        usage = body.get("usage") or {}
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        response_model = str(body.get("model") or batch_row["model"])
        response_cost = batch_cost(response_model, input_tokens, output_tokens)
        try:
            if item.get("error") or int(response.get("status_code") or 0) != 200:
                raise ValueError(str(item.get("error") or body.get("error") or response))
            dossier = load_dossier(args.dossiers, offsets, nct_id)
            if dossier.get("dossier_sha256") != submitted["dossier_sha256"]:
                raise ValueError("dossier hash differs from submitted manifest")
            user_prompt = rescore.render_model_input(dossier)
            if rescore.sha256_text(user_prompt) != submitted["input_sha256"]:
                raise ValueError("rendered input differs from submitted manifest")
            result = CallResult(
                text=rescore.response_text(body),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=response_cost,
                model=response_model,
                provider_request_id=str(body.get("id") or response.get("request_id") or ""),
                system_prompt=rescore.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=rescore.MODEL_MAX_TOKENS,
                temperature=0.0,
                provider="openai",
            )
            row = rescore.parse_model_result(result, dossier)
            row["_batch_id"] = batch_id
            row["_batch_custom_id"] = cid
            row["_dossier_file"] = args.dossiers.name
            row["_model_parameters"].update({
                "reasoning_effort": "none", "structured_outputs": True, "batch_api": True
            })
            append_jsonl(args.out, row)
            handled.add(nct_id)
            succeeded += 1
            total_cost += float(row.get("_cost_usd") or 0.0)
        except Exception as exc:
            append_jsonl(args.errors_out, {
                "batch_id": batch_id, "custom_id": cid, "nct_id": nct_id,
                "error": f"{type(exc).__name__}: {exc}",
                "model": response_model, "input_tokens": input_tokens,
                "output_tokens": output_tokens, "cost_usd": response_cost,
            })
            handled.add(nct_id)
            failed += 1
    return succeeded, failed, total_cost


def collect(args: argparse.Namespace) -> None:
    client = get_client()
    offsets = dossier_offsets(args.dossiers)
    handled = completed_nct_ids(args.out) | completed_nct_ids(args.errors_out)
    succeeded = failed = 0
    cost = 0.0
    for batch_row in read_jsonl(args.manifest):
        if batch_row.get("schema_version") != "trial_stoppage_openai_batch_v1":
            raise ValueError("unsupported batch manifest schema")
        if batch_row.get("prompt_version") != rescore.PROMPT_VERSION:
            raise ValueError(
                "batch prompt version differs from the current collector: "
                f"{batch_row.get('prompt_version')!r} != {rescore.PROMPT_VERSION!r}"
            )
        submitted_system_hash = batch_row.get("system_prompt_sha256")
        if (
            submitted_system_hash is not None
            and submitted_system_hash != rescore.sha256_text(rescore.SYSTEM_PROMPT)
        ):
            raise ValueError("batch system prompt differs from the current collector")
        ok, bad, new_cost = collect_batch(client, batch_row, args, offsets, handled)
        succeeded += ok
        failed += bad
        cost += new_cost
    print(f"collected={succeeded} failed={failed} new_cost=${cost:.4f} out={args.out}")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    subparsers = parser.add_subparsers(dest="command", required=True)

    submit_parser = subparsers.add_parser("submit")
    submit_parser.add_argument("--dossiers", type=Path, required=True)
    submit_parser.add_argument("--manifest", type=Path, required=True)
    submit_parser.add_argument("--completed-out", type=Path)
    submit_parser.add_argument("--model", default=rescore.DEFAULT_MODEL)
    submit_parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    submit_parser.add_argument("--max-batch-bytes", type=int, default=DEFAULT_MAX_BATCH_BYTES)
    submit_parser.add_argument("--confirm-paid-batch", action="store_true")

    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("--dossiers", type=Path, required=True)
    collect_parser.add_argument("--manifest", type=Path, required=True)
    collect_parser.add_argument("--out", type=Path, required=True)
    collect_parser.add_argument("--errors-out", type=Path)

    args = parser.parse_args(argv)
    if args.command == "submit" and (args.batch_size <= 0 or args.max_batch_bytes <= 0):
        parser.error("batch limits must be positive")
    if args.command == "collect" and args.errors_out is None:
        args.errors_out = args.out.with_name(f"{args.out.stem}.openai-batch-errors.jsonl")
    return args


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)
    submit(args) if args.command == "submit" else collect(args)


if __name__ == "__main__":
    main()
