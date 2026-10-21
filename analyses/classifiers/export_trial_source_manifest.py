"""Export a reproducible manifest for latest canonical trial sources."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

import psycopg2


NCT_RE = re.compile(r"^NCT\d{8}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--nct-id-file", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    nct_ids = sorted({
        line.strip().upper()
        for line in args.nct_id_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    })
    invalid = [value for value in nct_ids if not NCT_RE.fullmatch(value)]
    if invalid:
        raise ValueError(f"invalid NCT ids: {invalid[:5]}")
    connection = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cursor = connection.cursor()
        cursor.execute(
            """SELECT DISTINCT ON (s.subject_key)
                      s.subject_key, d.source_document_id, d.source_version,
                      d.source_url, d.content_sha256, d.retrieved_at,
                      COALESCE((d.metadata->>'has_results')::boolean, false)
               FROM preclin.source_document_subject s
               JOIN preclin.source_document d USING (source_document_id)
               WHERE s.subject_type='trial' AND s.subject_key=ANY(%s)
                 AND d.source_name='clinicaltrials.gov'
               ORDER BY s.subject_key, d.retrieved_at DESC,
                        d.source_document_id DESC""",
            (nct_ids,),
        )
        rows = cursor.fetchall()
    finally:
        connection.close()
    found = {str(row[0]) for row in rows}
    missing = sorted(set(nct_ids) - found)
    if missing:
        raise ValueError(f"missing canonical registry sources: {missing[:5]}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            record = {
                "nct_id": row[0],
                "source_document_id": int(row[1]),
                "source_version": row[2],
                "source_url": row[3],
                "content_sha256": row[4],
                "retrieved_at": row[5].isoformat(),
                "has_results": bool(row[6]),
            }
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    temporary.replace(args.out)
    print(
        f"manifest_rows={len(rows)} unique_nct_ids={len(found)} "
        f"has_results={sum(bool(row[6]) for row in rows)} out={args.out}"
    )


if __name__ == "__main__":
    main()
