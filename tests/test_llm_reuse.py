"""Which earlier decisions a run reuses, on the shared database inside a transaction that is rolled back."""
import uuid

import pytest
from psycopg2.extras import Json

from pipeline import llm

SHA = "0" * 64
TASK = llm.Task(name="test_reuse_task", prompt_version="t1", schema_version="t1", system="", schema={},
                render=str, subject_type="test")


def decision(cur, run_status, key, payload, out, minutes_ago):
    run = str(uuid.uuid4())
    cur.execute("""INSERT INTO pv_evidence.llm_decision_run (decision_run_id, task, provider, model, prompt_version,
                     output_schema_version, parameters, status, started_at)
                   VALUES (%s, %s, 'anthropic', 'm', 't1', 't1', '{}', %s, now() - %s * interval '1 minute')""",
                (run, TASK.name, run_status, minutes_ago))
    cur.execute("""INSERT INTO pv_evidence.llm_decision (decision_run_id, task, subject_type, subject_key, input_sha256,
                     raw_response, parsed_output, output_sha256, canonical_decision, decision_sha256, change_status,
                     input_payload, provider_request_id, model_parameters, usage, validation_status, validation_detail,
                     created_at)
                   VALUES (%s, %s, 'test', %s, %s, '', %s, %s, %s, %s, 'not_compared', %s, '', '{}', '{}', 'validated',
                           '[]', now() - %s * interval '1 minute')""",
                (run, TASK.name, key, llm.sha256_text(llm.canonical_json(payload)), Json(out), SHA, Json(out), SHA,
                 Json(payload), minutes_ago))


@pytest.fixture
def cur():
    conn = llm.connect()
    try:
        with conn.cursor() as c:
            yield c
    finally:
        conn.rollback()
        conn.close()


@pytest.mark.db
def test_a_retracted_runs_decisions_are_neither_reused_nor_latest(cur):
    decision(cur, "completed", "s1", {"name": "x"}, {"v": "kept"}, 10)
    decision(cur, "retracted", "s1", {"name": "x"}, {"v": "withdrawn"}, 1)
    assert llm._reusable(cur, TASK, {"s1": {"name": "x"}}, "subject")["s1"][1] == {"v": "kept"}
    assert llm._reusable(cur, TASK, {"s1": {"name": "x"}}, "input")["s1"][1] == {"v": "kept"}
    assert llm._latest(cur, TASK.name, "t1").set_index("key").parsed_output["s1"] == {"v": "kept"}


@pytest.mark.db
def test_a_name_keeps_its_decision_when_only_its_siblings_change(cur):
    decision(cur, "completed", "s2", {"name": "MK-1", "siblings": [{"name": "MK-1 tab", "kind": "drug"}]},
             {"v": "decided with siblings"}, 5)
    decision(cur, "completed", "s3", {"name": "MK-2"}, {"v": "first pass only"}, 5)
    sibling_changed = {"name": "MK-1", "siblings": [{"name": "MK-1 cap", "kind": "combination"}]}
    own_changed = {"name": "MK-1 renamed", "siblings": [{"name": "MK-1 tab", "kind": "drug"}]}
    never_with_siblings = {"name": "MK-2", "siblings": [{"name": "MK-2 tab", "kind": "drug"}]}
    reused = llm._reusable(cur, TASK, {"s2": sibling_changed, "s3": never_with_siblings}, "input", ("siblings",))
    assert reused["s2"][1] == {"v": "decided with siblings"} and "s3" not in reused
    assert "s2" not in llm._reusable(cur, TASK, {"s2": own_changed}, "input", ("siblings",))
    assert "s2" not in llm._reusable(cur, TASK, {"s2": sibling_changed}, "input")  # without context: decided again


@pytest.mark.db
def test_without_retraction_input_reuse_still_takes_the_latest_matching_decision(cur):
    # current_decisions is _reusable(..., "input"): for runs nobody retracted it behaves as before
    decision(cur, "completed", "s4", {"name": "y"}, {"v": "older"}, 9)
    decision(cur, "completed", "s4", {"name": "y"}, {"v": "newer"}, 2)
    decision(cur, "completed", "s4", {"name": "other input"}, {"v": "newest, other input"}, 1)
    assert llm._reusable(cur, TASK, {"s4": {"name": "y"}}, "input")["s4"][1] == {"v": "newer"}
    decision(cur, "retracted", "s4", {"name": "y"}, {"v": "withdrawn"}, 0)
    assert llm._reusable(cur, TASK, {"s4": {"name": "y"}}, "input")["s4"][1] == {"v": "newer"}  # falls back
    assert "s5" not in llm._reusable(cur, TASK, {"s5": {"name": "never"}}, "input")  # decided fresh


@pytest.mark.db
def test_cleanup_keeps_an_entity_referenced_only_by_an_fda_application(cur):
    from pipeline.drugs import delete_unreferenced
    cur.execute("SELECT appl_no FROM preclin.fda_application LIMIT 1")
    appl = cur.fetchone()[0]
    cur.execute("""INSERT INTO preclin.moiety (moiety_key, name) VALUES ('zztestfdaonly', 'zz test fda only'),
                   ('zztestorphan', 'zz test orphan') RETURNING moiety_id""")
    fda_only, orphan = (r[0] for r in cur.fetchall())
    cur.execute("SELECT llm_decision_id FROM pv_evidence.llm_decision LIMIT 1")
    cur.execute("INSERT INTO preclin.fda_application_moiety (appl_no, moiety_id, llm_decision_id) VALUES (%s, %s, %s)",
                (appl, fda_only, cur.fetchone()[0]))
    assert delete_unreferenced(cur, {fda_only, orphan}) == 1
    cur.execute("SELECT moiety_id FROM preclin.moiety WHERE moiety_id IN (%s, %s)", (fda_only, orphan))
    assert [r[0] for r in cur.fetchall()] == [fda_only]


@pytest.mark.db
def test_names_resolve_past_entities_being_rebuilt(cur):
    from pipeline.drugs import entity_ids
    cur.execute("""INSERT INTO preclin.moiety (moiety_key, name, code_names) VALUES ('zzestablished', 'zz established',
                   '{ZZ-101}') RETURNING moiety_id""")
    old = cur.fetchone()[0]
    cur.execute("INSERT INTO preclin.moiety (moiety_key, name) VALUES ('zz101', 'ZZ-101') RETURNING moiety_id")
    new = cur.fetchone()[0]
    assert entity_ids(cur, {"zz101": "ZZ-101"})["zz101"] == new  # ambiguous: the entity named ZZ-101
    assert entity_ids(cur, {"zz101": "ZZ-101"}, before=new)["zz101"] == old  # as if the later one did not exist
