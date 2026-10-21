"""Fetch curated source URLs and preserve raw bytes plus retrieval digests."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


USER_AGENT = "predictive-validity research source archive contact: research@example.invalid"


class SnapshotHTTPError(Exception):
    def __init__(self, status: int, media_type: str | None, final_url: str, body: bytes):
        super().__init__(f"HTTP status {status}")
        self.status = status
        self.media_type = media_type
        self.final_url = final_url
        self.body = body


def fetch_with_curl(url: str, timeout_seconds: int) -> tuple[bytes, str | None, int, str]:
    """Fallback for sites that discriminate against Python's HTTP stack."""
    with tempfile.NamedTemporaryFile() as body_file:
        completed = subprocess.run(
            [
                "curl", "-L", "--silent", "--show-error",
                "--max-time", str(timeout_seconds),
                "--user-agent", USER_AGENT,
                "--header", "Accept: text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
                "--output", body_file.name,
                "--write-out", "%{json}",
                url,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        body_file.seek(0)
        body = body_file.read()
    if not completed.stdout:
        raise RuntimeError(
            f"curl failed with exit {completed.returncode}: "
            f"{completed.stderr.decode('utf-8', errors='replace')[:300]}"
        )
    metadata = json.loads(completed.stdout)
    status = int(metadata.get("http_code") or 0)
    media_type = metadata.get("content_type") or None
    final_url = metadata.get("url_effective") or url
    if completed.returncode != 0 or not 200 <= status < 300:
        raise SnapshotHTTPError(status, media_type, final_url, body)
    return body, media_type, status, final_url


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    return parser.parse_args()


def fetch(url: str, timeout_seconds: int) -> tuple[bytes, str | None, int, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8",
        },
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return (
                    response.read(),
                    response.headers.get("Content-Type"),
                    response.status,
                    response.geturl(),
                )
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(2 ** attempt)
    assert last_error is not None
    try:
        return fetch_with_curl(url, timeout_seconds)
    except Exception as curl_error:
        if isinstance(curl_error, SnapshotHTTPError):
            raise curl_error
        raise RuntimeError(f"urllib failed ({last_error}); curl fallback failed ({curl_error})") from curl_error


def main() -> None:
    args = parse_args()
    if not 1 <= args.workers <= 16:
        raise ValueError("--workers must be between 1 and 16")
    sources = [json.loads(line) for line in args.sources.read_text(encoding="utf-8").splitlines() if line.strip()]
    unique: dict[str, dict] = {}
    for row in sources:
        unique.setdefault(str(row["source_url"]), row)
    existing_by_url: dict[str, dict] = {}
    if args.manifest.exists():
        for line in args.manifest.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing = json.loads(line)
                existing_by_url[str(existing["source_url"])] = existing
    args.raw_dir.mkdir(parents=True, exist_ok=True)

    def one(item: tuple[str, dict]) -> dict:
        url, source = item
        retrieved_at = datetime.now(timezone.utc).isoformat()
        try:
            body, media_type, status, final_url = fetch(url, args.timeout_seconds)
            digest = hashlib.sha256(body).hexdigest()
            raw_path = args.raw_dir / f"{digest}.bin"
            if not raw_path.exists():
                temporary = raw_path.with_suffix(".bin.tmp")
                temporary.write_bytes(body)
                temporary.replace(raw_path)
            return {
                "nct_ids": sorted({
                    str(row["nct_id"]) for row in sources if row["source_url"] == url
                }),
                "source_url": url,
                "final_url": final_url,
                "source_name": source["source_name"],
                "external_id": source["external_id"],
                "retrieved_at": retrieved_at,
                "http_status": status,
                "media_type": media_type,
                "raw_byte_count": len(body),
                "raw_sha256": digest,
                "raw_snapshot_path": str(raw_path),
                "error": None,
            }
        except Exception as exc:  # preserve search-negative/fetch-failure provenance
            error_body = b""
            error_media_type = None
            error_status = None
            final_url = url
            if isinstance(exc, urllib.error.HTTPError):
                error_status = exc.code
                error_media_type = exc.headers.get("Content-Type")
                final_url = exc.geturl()
                error_body = exc.read()
            elif isinstance(exc, SnapshotHTTPError):
                error_status = exc.status
                error_media_type = exc.media_type
                final_url = exc.final_url
                error_body = exc.body
            error_digest = hashlib.sha256(error_body).hexdigest() if error_body else None
            error_path = args.raw_dir / f"{error_digest}.bin" if error_digest else None
            if error_path is not None and not error_path.exists():
                temporary = error_path.with_suffix(".bin.tmp")
                temporary.write_bytes(error_body)
                temporary.replace(error_path)
            return {
                "nct_ids": sorted({
                    str(row["nct_id"]) for row in sources if row["source_url"] == url
                }),
                "source_url": url,
                "final_url": final_url,
                "source_name": source["source_name"],
                "external_id": source["external_id"],
                "retrieved_at": retrieved_at,
                "http_status": error_status,
                "media_type": error_media_type,
                "raw_byte_count": len(error_body) if error_body else None,
                "raw_sha256": error_digest,
                "raw_snapshot_path": str(error_path) if error_path else None,
                "error": f"{type(exc).__name__}: {exc}",
            }

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        manifest = list(executor.map(one, sorted(unique.items())))
    for index, row in enumerate(manifest):
        previous = existing_by_url.get(row["source_url"])
        if row["error"] and previous and not previous.get("error"):
            retained = dict(previous)
            retained["later_failed_attempt"] = {
                key: row.get(key)
                for key in (
                    "retrieved_at", "http_status", "raw_byte_count",
                    "raw_sha256", "raw_snapshot_path", "error",
                )
            }
            manifest[index] = retained
    manifest.sort(key=lambda row: (row["source_name"], row["external_id"], row["source_url"]))
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.manifest.with_suffix(args.manifest.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in manifest:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(args.manifest)
    failures = sum(bool(row["error"]) for row in manifest)
    print(
        f"sources={len(manifest)} snapshotted={len(manifest) - failures} "
        f"failures={failures} manifest={args.manifest}"
    )


if __name__ == "__main__":
    main()
