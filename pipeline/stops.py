"""Stopped programs, the reason the registry gives each, why each stop for efficacy or exposure failed, and the
vocabulary of preclin.stop: the definitions pipeline.stop_causes, pipeline.attribution and the reports share.

A stopped program is one Section 1 records as suspended (report.section1.failure_modes), keyed by (entity,
disease, phase). Its stop is for efficacy or exposure when the registry says so, or when stop-cause inference
traced it there with a source. Each such stop gets an efficacy-attribution label (pipeline.attribution); the web
search label replaces a bundle label of U. The label settles the stop's cause where it contradicts it: F6 is
safety, F8 is a sponsor decision, and F9 (not an efficacy test) sends a registry efficacy stop back to inference.
The model's failure codes stay inside the decisions; preclin.stop names them (SUBCAUSE, DETAIL).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pipeline import llm
from report import frame, section1
from report.disease_match import Mondo
from report.windows import TRACING

PHASES = (1, 2, 3)  # phases whose stops are traced and labelled
EFFICACY_REASONS = ("efficacy: stated", "efficacy: primary endpoint not met")
PK_REASON = "PK, dose or formulation"
POSITIVE = "positive readout, not advanced"
UNSTATED = ("completed, no results posted, no reason stated", "stopped, no reason stated",
            "results posted, no reason stated, endpoint not assessable", "sponsor decision, unspecified",
            "other stated reason")
REGISTRY_CAUSE = {**{r: "efficacy" for r in EFFICACY_REASONS}, "safety": "safety", PK_REASON: "pk_formulation",
                  "business or strategic (explicit)": "business_strategic",
                  "enrollment, operational or regulatory": "operational", POSITIVE: "positive_not_advanced"}
EFFICACY_CAUSES = ("efficacy", "pk_formulation")
ORIGINS = {"efficacy": "efficacy", "pk_formulation": "pk"}
# The cause in preclin.stop of each cause the inference names: PK joins efficacy (an exposure failure is a failure
# to engage), business and company events are both the sponsor's decision, and continued development is no stop.
CAUSE = {"efficacy": "efficacy", "pk_formulation": "efficacy", "safety": "safety",
         "business_strategic": "sponsor_decision", "company_event": "sponsor_decision", "operational": "operational",
         "positive_not_advanced": "positive_not_advanced", "development_continued": "not_stopped",
         "unknown": "unknown"}
CAUSES = list(dict.fromkeys(CAUSE.values()))
CODE_CAUSE = {"F6": "safety", "F8": "sponsor_decision"}  # attribution codes that settle a stop's cause
# Why efficacy failed, by attribution code. F3 and F4 count as engaged without benefit only when engagement was
# shown or inferred, otherwise as trial design (subcause()). The other codes are not efficacy failures: F6 settles
# the stop as safety, F8 as a sponsor decision, and F9 is coded by its pillars (pillar_code).
SUBCAUSE = {"F1a": "not_engaged", "F1b": "not_engaged", "F2": "engaged_no_benefit", "F3": "engaged_no_benefit",
            "F4": "engaged_no_benefit", "F5": "toxicity_offset", "F7": "trial_design", "U": "no_engagement_data"}
EFFICACY_SUBCAUSES = ["not_engaged", "engaged_no_benefit", "trial_design", "toxicity_offset", "no_engagement_data"]
# The subcauses of the other causes, chosen by pipeline.stop_causes describe from what the stop's explanation says;
# not_stated where it says no more than the cause. A stop the efficacy label settles as safety is off_target_toxicity.
# A sponsor decision and a positive readout that went no further share the reasons development did not go on
# (DISCONTINUED); a positive readout may also have been approved outside the US or declined by the FDA.
DISCONTINUED = ["portfolio_prioritisation", "commercial_or_competitive", "partner_exit", "acquisition_or_merger",
                "funding_or_closure", "replaced_by_successor"]
SUBCAUSES = {
    "safety": ["on_target_toxicity", "off_target_toxicity", "tolerability", "preclinical_toxicity", "clinical_hold",
               "not_stated"],
    "sponsor_decision": [*DISCONTINUED, "not_stated"],
    "operational": ["enrollment", "site_or_supply", "covid_19", "regulatory", "not_stated"],
    "positive_not_advanced": ["approved_outside_us", "fda_declined", *DISCONTINUED, "not_stated"],
}
COMPANY_ENDED = ("acquisition_or_merger", "funding_or_closure")
DETAIL = {"F1b": "other_drug_on_target_worked", "F3": "wrong_population", "F4": "wrong_endpoint_or_timing",
          "F7": "trial_could_not_answer"}
INFERENCE_TASK, INFERENCE_VERSION = "stop_cause_inference", "v2"
ENGAGED = ("adequate", "inferred_adequate")
RELATED_DISEASE = 0.5  # MONDO Lin similarity at which another disease counts as related
BUNDLE_LABEL_TASK, SEARCH_LABEL_TASK, LABEL_VERSION = "efficacy_failure_attribution", "efficacy_attribution_search", "v1"


def subject_key(moiety_id: int, mondo_id: str | None, phase: int) -> str:
    """Key of an (entity, disease, phase); a program without a disease (None or NaN) has an empty disease."""
    return f"{moiety_id}|{mondo_id if isinstance(mondo_id, str) else ''}|{phase}"


def keys(d: pd.DataFrame) -> list[str]:
    return [subject_key(m, x, p) for m, x, p in zip(d.moiety_id, d.mondo_id, d.phase)]


def stops():
    """Every program Section 1 records as suspended with a phase entry in report.windows.TRACING, with the reason it assigns,
    its disease and its phase entry date, one row per (entity, disease, phase), and the phase rows, programs and
    trials it was built from."""
    snap = frame.snapshot()
    progs, trials = frame.programs(), frame.program_trials()
    rows = section1.phase_rows(progs, trials, snap, window=TRACING)
    modes = section1.failure_modes(rows, progs, trials, frame.trial_outcomes()).merge(
        progs[["program_id", "mondo_id"]], on="program_id").merge(
        rows[~rows.credited][["program_id", "phase", "entry"]], on=["program_id", "phase"])
    modes["key"] = keys(modes)
    if modes.key.duplicated().any():
        raise ValueError(f"programs share an (entity, disease, phase): {modes[modes.key.duplicated()].key.tolist()[:5]}")
    return modes, rows, progs, trials


def inferred_causes() -> pd.DataFrame:
    """The latest validated stop-cause inference of each program: key, llm_decision_id, parsed_output."""
    return llm.latest_decisions(INFERENCE_TASK, INFERENCE_VERSION)


def cohort(modes: pd.DataFrame) -> pd.DataFrame:
    """Stops for efficacy or exposure, with their index trial and origin: registry_efficacy and registry_pk from
    Section 1's reason, traced_efficacy and traced_pk where any other reason was traced there with a source."""
    dec = inferred_causes()
    traced = {k: o["cause"] for k, o in zip(dec.key, dec.parsed_output) if o["cause"] in EFFICACY_CAUSES}
    registry = modes.reason.isin(EFFICACY_REASONS) | modes.reason.eq(PK_REASON)
    out = modes[registry | modes.key.isin(set(traced))].copy()
    out["origin"] = [f"registry_{ORIGINS[REGISTRY_CAUSE[r]]}" if reg else f"traced_{ORIGINS[traced[k]]}"
                     for r, k, reg in zip(out.reason, out.key, registry[out.index])]
    return out


def decided(task: str) -> pd.DataFrame:
    """The latest validated efficacy-attribution decision of each stop for a task: key, llm_decision_id and the
    decision's fields."""
    d = llm.latest_decisions(task, LABEL_VERSION)
    return pd.concat([d[["key", "llm_decision_id"]], pd.DataFrame(list(d.parsed_output), index=d.index)], axis=1)


def labels() -> pd.DataFrame:
    """The efficacy-attribution label of each labelled stop: the web-search label where the bundle label was U,
    with the bundle's code and engagement kept as bundle_code and bundle_engagement."""
    a, s = decided(BUNDLE_LABEL_TASK), decided(SEARCH_LABEL_TASK).set_index("key")
    a["bundle_code"], a["bundle_engagement"] = a.primary_code, a.engagement
    a["searched"] = a.primary_code.eq("U") & a.key.isin(s.index)
    a["quote"] = ""
    for col in s.columns:
        a.loc[a.searched, col] = s.loc[a.key[a.searched], col].to_numpy()
    return a


def pillar_code(d: pd.DataFrame) -> pd.Series:
    """The failure code for counting: F9 (not an efficacy test) on a stop that is still for efficacy or exposure
    is coded by its pillars, engaged as F2, shown inadequate or dose-limited as F1a, otherwise U."""
    by_pillars = d.primary_code.eq("F9")
    pillars = np.select([d.engagement.isin(ENGAGED),
                         d.engagement.eq("inadequate") | d.exposure.eq("inadequate") | d.dose_limited.astype(bool)],
                        ["F2", "F1a"], "U")
    return d.primary_code.where(~by_pillars, pd.Series(pillars, index=d.index))


def subcause(code: pd.Series, engagement: pd.Series) -> pd.Series:
    """Why efficacy failed, from the attribution code and engagement; null for a code that is not an efficacy
    failure (F6, F8, F9)."""
    return code.map(SUBCAUSE).where(~(code.isin(["F3", "F4"]) & ~engagement.isin(ENGAGED)), "trial_design")


def detail(code: pd.Series, dose_limited: pd.Series) -> pd.Series:
    """The finer reason under subcause(): F1a is split by whether tolerability capped the dose."""
    f1a = np.where(dose_limited.astype(bool), "dose_capped", "exposure_or_engagement_too_low")
    return code.map(DETAIL).where(code.ne("F1a"), pd.Series(f1a, index=code.index))


FATES = ["sponsor_went_quiet", "drug_approved_elsewhere", "drug_continued_elsewhere", "drug_dropped"]


def fate(sig: pd.DataFrame) -> pd.Series:
    """What the drug and its sponsor did after a stop no source explains: the subcause of an unknown cause."""
    return pd.Series(np.select([sig.sponsor_active_after.eq(False), sig.drug_approved_anywhere.astype(bool),
                                sig.drug_continued_elsewhere.astype(bool)],
                               FATES[:3], FATES[3]), index=sig.index)


def settled(modes: pd.DataFrame, lab: pd.DataFrame) -> dict[str, str]:
    """Stops whose registry reason the evidence contradicts, with what settles them: a cause (CODE_CAUSE) where
    the attribution code gives one, 'infer' where the registry efficacy stop was not an efficacy test (F9) or a
    positive readout's primary endpoint is not an efficacy endpoint."""
    code = modes.key.map(lab.set_index("key").primary_code)
    out = {k: CODE_CAUSE[c] for k, c in zip(modes.key, code) if c in CODE_CAUSE}
    out |= {k: "infer" for k in modes.key[modes.reason.isin(EFFICACY_REASONS) & code.eq("F9")]}
    pos = modes[modes.reason == POSITIVE]
    e = frame.query("SELECT nct_id FROM preclin.trial_endpoint WHERE purpose <> 'efficacy' AND nct_id = ANY(%s)",
                    (sorted(set(pos.nct_id.dropna())),))
    out |= {k: "infer" for k in pos.key[pos.nct_id.isin(set(e.nct_id))]}
    return out


class SameTarget:
    """Other entities sharing a primary target with an entity, and whether two diseases are related (MONDO Lin
    similarity >= RELATED_DISEASE), with similarities cached since the same pairs recur across programs."""

    def __init__(self, mondo: Mondo):
        t = frame.query("SELECT moiety_id, target_id FROM preclin.moiety_target WHERE is_primary")
        self.targets = t.groupby("moiety_id").target_id.apply(set)
        self.entities = t.groupby("target_id").moiety_id.apply(set)
        self.mondo = mondo
        self.lin: dict[tuple[str, str], float] = {}

    def others(self, moiety_id: int) -> set[int]:
        return {o for x in self.targets.get(moiety_id, ()) for o in self.entities[x]} - {moiety_id}

    def related(self, a, b) -> bool:
        if not (isinstance(a, str) and isinstance(b, str)):
            return False
        if (a, b) not in self.lin:
            self.lin[a, b] = self.mondo.lin(a, b)
        return self.lin[a, b] >= RELATED_DISEASE
