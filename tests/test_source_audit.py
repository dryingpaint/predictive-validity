"""Focused unit tests for source-aware LLM audit invariants."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ingest = load_module("source_audit_ingest", "db/13_ingest_llm_outputs.py")


class SourceAuditTests(unittest.TestCase):
    def test_user_prompt_compression_round_trips_exact_utf8(self):
        prompt = "Exact model input with Unicode: β-catenin\n" * 100
        encoded, size = ingest.compress_user_prompt(prompt)
        import base64

        restored = ingest.restore_user_prompt(
            None, base64.b64decode(encoded), "zlib"
        )
        self.assertEqual(restored, prompt)
        self.assertEqual(size, len(prompt.encode("utf-8")))

    def test_parsed_output_omits_normalized_audit_envelope(self):
        row = {
            "tier": "T2",
            "rationale": "Supported by replicated human genetics.",
            "_run_id": "run-1",
            "_model": "test-model",
            "_system_prompt": "system",
            "_user_prompt": "large exact prompt",
            "_raw_response": '{"tier":"T2"}',
            "_source_documents": [{"source_document_id": 99}],
        }

        payload = ingest.parsed_output_payload(row)

        self.assertEqual(payload["tier"], "T2")
        self.assertEqual(payload["rationale"], row["rationale"])
        self.assertEqual(payload["_run_id"], "run-1")
        self.assertEqual(payload["_model"], "test-model")
        self.assertTrue(
            ingest.REDUNDANT_PARSED_OUTPUT_FIELDS.isdisjoint(payload)
        )

    def test_evidence_snapshot_is_complete_and_defensive(self):
        citations = [123, "456"]
        snapshot = ingest.evidence_snapshot(
            subject_type="target",
            subject_id=42,
            dimension="line_c_lit",
            category="C_cell",
            source="pubmed_haiku",
            version="v1",
            model="test-model",
            value_numeric=2.0,
            confidence="high",
            citation_pmids=citations,
        )
        citations.append("789")
        self.assertEqual(snapshot["citation_pmids"], ["123", "456"])
        self.assertEqual(snapshot["value_numeric"], 2.0)
        self.assertEqual(snapshot["subject_id2"], None)
        self.assertEqual(snapshot["extracted_by"], "test-model")

    def test_nelson_snapshot_preserves_pair_key_and_details(self):
        snapshot = ingest.evidence_snapshot(
            subject_type="target_indication",
            subject_id=42,
            subject_id2=7,
            dimension="nelson_tier",
            category="A_genetics",
            source="nelson_llm",
            version="v4",
            model="test-model",
            value_text="T3",
            value_json={"dossier_sha256": "abc"},
        )
        self.assertIn("nelson-tier", ingest.TASKS)
        self.assertEqual(snapshot["subject_id2"], 7)
        self.assertEqual(snapshot["value_text"], "T3")
        self.assertEqual(snapshot["value_json"], {"dossier_sha256": "abc"})


if __name__ == "__main__":
    unittest.main()
