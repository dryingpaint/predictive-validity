"""A batch run that stops before collecting its batches is resumed, not resubmitted."""
import json
import uuid
from types import SimpleNamespace

import pytest

from pipeline import llm

TASK = llm.Task(name="resume_test", prompt_version="v1", schema_version="v1", system="s",
                schema={"type": "object"}, render=lambda p: p["text"], subject_type="trial")


class FakeBatches:
    """Batches API: create records requests; results answer each request with {"key": <text>}."""

    def __init__(self, fail_polls: int = 0):
        self.created, self.requests, self.fail_polls = [], {}, fail_polls

    def create(self, requests):
        batch_id = f"b{len(self.created)}"
        self.created.append(batch_id)
        self.requests[batch_id] = requests
        return SimpleNamespace(id=batch_id)

    def retrieve(self, batch_id):
        if self.fail_polls:
            self.fail_polls -= 1
            raise RuntimeError("network down")
        return SimpleNamespace(processing_status="ended")

    def results(self, batch_id):
        for r in self.requests[batch_id]:
            text = r["params"]["messages"][0]["content"]
            msg = SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps({"key": text}))],
                                  stop_reason="end_turn",
                                  usage=SimpleNamespace(input_tokens=1, output_tokens=1, cache_read_input_tokens=0))
            yield SimpleNamespace(custom_id=r["custom_id"], result=SimpleNamespace(type="succeeded", message=msg))


@pytest.fixture
def stored(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "BATCH_MANIFESTS", str(tmp_path))
    monkeypatch.setattr(llm, "POLL_SECONDS", 0)
    rows = []
    monkeypatch.setattr(llm, "_store", rows.extend)
    return rows


def test_stopped_batch_run_is_collected_by_the_next_run(stored, monkeypatch):
    monkeypatch.setattr(llm, "BATCH_SIZE", 2)
    items = {f"NCT{i}": {"text": f"trial {i}"} for i in range(3)}
    first = FakeBatches(fail_polls=1)
    with pytest.raises(RuntimeError):
        llm._run_batches(SimpleNamespace(messages=SimpleNamespace(batches=first)), uuid.uuid4(), TASK, items, list(items))
    assert len(first.created) == 2 and not stored

    second = FakeBatches()
    second.requests = first.requests  # the same batches, still on the provider's side
    llm._run_batches(SimpleNamespace(messages=SimpleNamespace(batches=second)), uuid.uuid4(), TASK, items, list(items))
    assert second.created == []
    assert sorted(r[3] for r in stored) == sorted(items)
    assert all(json.loads(r[5])["key"] == items[r[3]]["text"] for r in stored)
    assert not json.load(open(llm._manifest_path(TASK)))


def test_changed_input_is_resubmitted(stored, monkeypatch):
    items = {"NCT1": {"text": "trial 1"}}
    first = FakeBatches(fail_polls=1)
    with pytest.raises(RuntimeError):
        llm._run_batches(SimpleNamespace(messages=SimpleNamespace(batches=first)), uuid.uuid4(), TASK, items, list(items))
    changed = {"NCT1": {"text": "trial 1, revised"}}
    second = FakeBatches()
    llm._run_batches(SimpleNamespace(messages=SimpleNamespace(batches=second)), uuid.uuid4(), TASK, changed, list(changed))
    assert second.created == ["b0"]
    assert json.loads(stored[0][5])["key"] == "trial 1, revised"
