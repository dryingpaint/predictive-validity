import pytest

from report.__main__ import name, selected


def names(steps):
    return [name(s) for s in steps]


def test_no_step_named_runs_the_whole_build():
    assert names(selected([]))[0] == "quality" and names(selected([]))[-1] == "render"
    assert len(selected([])) == 13


def test_a_named_analysis_reruns_the_steps_that_use_it_in_build_order():
    assert names(selected(["evidence_analysis"])) == ["evidence_analysis", "failure_modes", "target_origin",
                                                          "polygenicity", "figures", "render"]


def test_a_figure_change_redraws_only_the_figures_and_a_render_change_redraws_them_too():
    assert names(selected(["figures"])) == ["figures"]  # REPORT.md names figures by path
    assert names(selected(["render"])) == ["figures", "render"]  # figures draw with render's labels


def test_an_early_step_reruns_everything_downstream():
    assert names(selected(["section1"])) == ["section1", "section2", "section3", "evidence_analysis", "attribution",
                                             "stop_causes", "failure_modes", "target_origin", "polygenicity", "methods",
                                             "figures", "render"]


def test_the_target_origin_step_redraws_its_figures_and_rewrites_the_text():
    assert names(selected(["target_origin"])) == ["target_origin", "figures", "render"]


def test_an_unknown_step_is_refused():
    with pytest.raises(SystemExit):
        selected(["section9"])


def test_a_step_that_stands_aside_keeps_its_cached_outputs_and_is_not_recached(tmp_path, monkeypatch):
    """Review of 2026-11-27: a step may stand aside (frame.StandAside) when the database is not the one it was
    registered on; the runner then carries the step's cached outputs forward and does not re-cache them."""
    import types
    from report import __main__ as runner
    from report import frame
    out, cache = tmp_path / "output", tmp_path / "cache"
    (cache / "aside").mkdir(parents=True)
    (cache / "aside" / "numbers.json").write_text("{}")
    (cache / "aside" / runner.MANIFEST).write_text('{"built_at": "then", "commit": "abc", "branch": "b", "snapshot": "s"}')
    monkeypatch.setattr(runner, "OUTPUT", str(out))
    monkeypatch.setattr(runner, "CACHE", str(cache))
    step = types.SimpleNamespace(__name__="report.aside", main=lambda: (_ for _ in ()).throw(frame.StandAside("not the registered build")))
    assert runner.run_step(step) is False
    assert (out / "aside" / "numbers.json").read_text() == "{}"
    ran = types.SimpleNamespace(__name__="report.ran", main=lambda: None)
    assert runner.run_step(ran) is True
