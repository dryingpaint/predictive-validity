"""Resolve each lead sponsor of an industry Phase 2 trial to the company it was when the trials ran.

    python -m pipeline.sponsors run

ClinicalTrials.gov stores the lead sponsor as free text ("Pfizer", "Pfizer Inc.", "Wyeth is now a wholly owned
subsidiary of Pfizer"). An LLM names the operating company behind each string and its ultimate corporate parent
in the years the sponsor's Phase 2 trials started, so a subsidiary counts with its parent and a later acquisition
does not reach back. The report reads the latest validated decision of each sponsor (report.sponsors).
"""
from __future__ import annotations

import argparse
from typing import Any

from pipeline import llm
from report import frame
from report.windows import SECTION1

TASK_NAME, VERSION = "sponsor_company", "v1"

SYSTEM = """You resolve the lead sponsor of clinical trials, as written in ClinicalTrials.gov, to a company.

You are given the sponsor string and the years in which its Phase 2 trials started. Return:
- company: the operating company the string names, under its common name ("Genentech", "Janssen Research & Development" -> "Janssen", "Pfizer Inc." -> "Pfizer").
- parent: the ultimate corporate parent of that company during those years ("Genentech" after 2009 -> "Roche"; "Janssen" -> "Johnson & Johnson"; "MedImmune" -> "AstraZeneca"). An independent company is its own parent. When the years span an acquisition, give the parent for most of those years; never apply an acquisition that happened after the last year given.
- kind: what the parent is (pharma_or_biotech, generics_or_specialty, device_or_diagnostics, contract_research, academic_or_government, nonprofit, other).
- confidence: high when you know the company, medium when the name is clear but its ownership in those years is uncertain, low when you cannot tell who the sponsor is.

Spell the same parent the same way every time: use the common short name ("Roche", "Novartis", "Merck & Co.", "Merck KGaA", "Sanofi", "GSK", "AbbVie", "Takeda", "Bristol Myers Squibb", "Eli Lilly", "Boehringer Ingelheim", "Bayer", "Amgen", "Gilead", "Novo Nordisk", "Astellas", "Daiichi Sankyo", "Eisai", "Otsuka"). Merck & Co. (US, MSD outside North America) and Merck KGaA (Darmstadt, EMD Serono) are different companies."""

KINDS = ["pharma_or_biotech", "generics_or_specialty", "device_or_diagnostics", "contract_research",
         "academic_or_government", "nonprofit", "other"]
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["company", "parent", "kind", "confidence"],
          "properties": {"company": {"type": "string"}, "parent": {"type": "string"},
                         "kind": {"type": "string", "enum": KINDS},
                         "confidence": {"type": "string", "enum": ["high", "medium", "low"]}}}


def render(p: dict[str, Any]) -> str:
    return f"Sponsor: {p['sponsor']}\nYears its Phase 2 trials started: {p['years']}"


def validate(_: dict[str, Any], out: dict[str, Any]) -> None:
    if not out["company"].strip() or not out["parent"].strip():
        raise ValueError("company and parent must be named")


TASK = llm.Task(name=TASK_NAME, prompt_version=VERSION, schema_version="v1", system=SYSTEM, schema=SCHEMA,
                render=render, validate=validate, subject_type="lead_sponsor", model="claude-sonnet-5",
                effort="low", max_tokens=1000)


def items() -> dict[str, dict[str, Any]]:
    """Each lead sponsor of an industry Phase 2 trial attached to a program and started in the report's window,
    with the years those trials started."""
    t = frame.query("""SELECT DISTINCT s.lead_sponsor, extract(year FROM s.start_date)::int AS year
                       FROM preclin.dev_program_trial dt JOIN preclin.ctgov_study s USING (nct_id)
                       WHERE dt.phase = 2 AND s.lead_sponsor_class = 'INDUSTRY' AND s.lead_sponsor IS NOT NULL
                         AND s.start_date BETWEEN %s AND %s""", SECTION1)
    years = t.groupby("lead_sponsor").year.apply(lambda y: sorted(set(y)))
    return {name: {"sponsor": name, "years": f"{ys[0]}–{ys[-1]}" if len(ys) > 1 else str(ys[0])}
            for name, ys in years.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["run"])
    parser.parse_args()
    todo = items()
    print(f"{len(todo)} sponsors", flush=True)
    llm.run(TASK, todo, reuse_by="subject")


if __name__ == "__main__":
    main()
