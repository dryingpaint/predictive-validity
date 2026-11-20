import pytest

from report.__main__ import selected


def names(steps):
    return [s.__name__.rsplit(".", 1)[-1] for s in steps]


def test_no_step_named_runs_the_whole_build():
    assert names(selected([]))[0] == "quality" and names(selected([]))[-1] == "render"
    assert len(selected([])) == 11


def test_a_named_analysis_reruns_the_steps_that_use_it_in_build_order():
    assert names(selected(["evidence_analysis"])) == ["evidence_analysis", "failure_modes", "figures", "render"]


def test_a_figure_change_redraws_only_the_figures_and_a_render_change_redraws_them_too():
    assert names(selected(["figures"])) == ["figures"]  # REPORT.md names figures by path
    assert names(selected(["render"])) == ["figures", "render"]  # figures draw with render's labels


def test_an_early_step_reruns_everything_downstream():
    assert names(selected(["section1"])) == ["section1", "section2", "section3", "evidence_analysis", "attribution",
                                             "stop_causes", "failure_modes", "methods", "figures", "render"]


def test_an_unknown_step_is_refused():
    with pytest.raises(SystemExit):
        selected(["section9"])
