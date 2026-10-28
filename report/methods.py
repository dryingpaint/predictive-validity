"""The methods document for the stop-cause and efficacy-failure figure, with its examples and the full prompts.

    python -m report.methods

Writes report/methods_stops_and_engagement.md from the prompts in the pipeline modules and the checks in
report/output/stop_causes and report/output/attribution, so the document matches the code and the numbers.
"""
from __future__ import annotations

import json
import os

from pipeline import attribution as a, outcomes as oc, stop_causes as sc
from report import frame

DOC = os.path.join(frame.REPO, "report", "methods_stops_and_engagement.md")
OUT = os.path.join(frame.REPO, "report", "output")


def pm(x: str) -> str:
    return f"[PMID {x}](https://pubmed.ncbi.nlm.nih.gov/{x}/)"


def nct(x: str) -> str:
    return f"[{x}](https://clinicaltrials.gov/study/{x})"


def pct(x: float) -> str:
    return f"{x:.0%}"


def main() -> None:
    v = json.load(open(os.path.join(OUT, "stop_causes", "numbers.json")))["validation"]
    n = json.load(open(os.path.join(OUT, "attribution", "numbers.json")))
    r, j = n["rederivation"], n["adjudication"]
    doc = f"""# How the stop-cause and efficacy-failure figure is built

Figure: `report/output/figures/efficacy_attribution.png`. Code: `pipeline/outcomes.py` (registry
classification), `report/section1.py` (stops and their registry reason), `pipeline/stops.py` (the shared
definitions: cohort, final labels, which label settles which cause), `pipeline/stop_causes.py` (tracing),
`pipeline/attribution.py` (efficacy-failure labels), `report/stop_causes.py` and `report/attribution.py`
(analysis), `report/figures.py` (figure). Every model decision is stored with its full input, output, sources and
rationale in `pv_evidence.llm_decision`; each step's method is recorded in `preclin.analysis_method`.

The efficacy-failure codes, estimands and checks were fixed before any program was labelled. Three steps were
added after the first results: the web search for programs with no engagement evidence, the inclusion of traced
efficacy and PK stops, and the rules by which an efficacy label settles a stop's cause.

A **program** is one drug developed for one disease. Both bars cover industry programs whose Phase 2 or Phase 3
began 2015–2025 (ClinicalTrials.gov). Every model step uses Claude Opus 5.5 except the re-derivation check, which uses Claude Sonnet 5.

## Top bar: why programs stopped

**Stopped** means no trial of the program active, or active within 24 months of the data snapshot, no later-phase
trial and no FDA approval for the disease (`report/section1.py`). Programs the web tracing found still in
development (another registry, region, name or combination) are removed from the figure.

**Step 1: the registry reason.** A model reads each trial's ClinicalTrials.gov record (stated reason for stopping,
posted results) and classifies it (prompt A below). Each program then takes one reason from the trials of the phase
it stopped in, by this priority: sponsor-stated efficacy failure → primary endpoint not met → safety → PK, dose or
formulation → business → bare "sponsor decision" → operational → positive readout → other → no reason stated.

**Step 2: tracing.** Where there is no usable reason (none stated, bare "sponsor decision", unspecified "other",
an efficacy reason the efficacy analysis showed wrong, or a "positive readout" whose primary endpoint was only
safety or PK), a model reads the program's trials, results, linked papers and structured signals (did the drug
continue elsewhere, did the sponsor start any later trial, did same-target drugs stop at the same time) and searches
the web, with ClinicalTrials.gov blocked (prompt B). It names a cause only where a source supports it, and may cite
only pages its own searches returned; where none does, it gives a *likely* cause. The figure counts sourced and
likely causes together.

**Step 3: consistency with the efficacy analysis.** Any stop for efficacy or exposure that the efficacy analysis
codes F6 (off-target toxicity) or F8 (business) takes safety or business as its cause. A registry efficacy stop coded
F9 (not an efficacy test) is traced again like an unexplained stop. The bottom bar is exactly the stops whose final
cause, sourced, is efficacy or exposure.

**Merges in the figure:** company events are shown with business; PK, dose or formulation is shown with efficacy
(as "efficacy or exposure"), since an exposure failure is the same biology as a failure to engage.

### Categories, with examples

| Category | Rule | Examples |
|---|---|---|
| Efficacy | Futility, missed primary endpoint, efficacy not competitive | Registry: pamrevlumab, Duchenne ({nct('NCT03955146')}): "Study did not meet its primary endpoint." Traced: FMX114 (fingolimod) in atopic dermatitis: "did not meet its primary endpoint" ([BioSpace](https://www.biospace.com/vyne-therapeutics-atopic-dermatitis-topical-fails-to-meet-primary-endpoint)); CMV immune globulin in pregnancy ({nct('NCT05170269')}): "terminated early as the number of maternal–fetal transmissions was close to the … historical control group" ([Arch Gynecol Obstet](https://link.springer.com/article/10.1007/s00404-026-08311-8)) |
| PK, dose or formulation (shown with efficacy) | Exposure, PK, dosing, formulation or manufacturability | Registry: interleukin-7 in sepsis ({nct('NCT03821038')}): "PK issue detected after bolus IV route administration." Traced: GSK2838232 in HIV: "its pharmacokinetic properties required it to be boosted … which led to the termination of its development" ([eClinicalMedicine](https://www.sciencedirect.com/science/article/pii/S2589537025005061)); fezagepras in IPF: dropped "following the analysis of the preliminary pharmacokinetic data" ([Fierce](https://www.fiercebiotech.com/biotech/liminal-stops-plan-to-advance-fibrosis-drug-after-seeing-pk-data)) |
| Safety | Adverse events, tolerability, a clinical hold for safety (on- or off-target) | Registry: IC265 in dry eye ({nct('NCT05992922')}): "Unexpected adverse events were observed." Traced: seladelpar in NASH: biopsies "revealed atypical histological findings … interface hepatitis" ([CymaBay release](https://www.globenewswire.com/news-release/2019/11/25/1951942/0/en/CymaBay-Therapeutics-Halts-Clinical-Development-of-Seladelpar.html)); batoclimab in warm AIHA: paused after "a physiological signal consisting of elevated total cholesterol" ([Fierce](https://www.fiercebiotech.com/biotech/immunovant-hits-pause-button-for-eye-drug-after-unexpected-cholesterol-spike)) |
| Business or strategic (incl. company events) | Portfolio prioritisation, commercial or competitive reasons, licence returned; or the company was acquired, ran out of money or closed | Registry: AVROBIO Fabry gene therapy ({nct('NCT03454893')}): "AVROBIO has deprioritized its Fabry disease program." Traced: PN-943 in UC: "De-prioritization of the PN-943 program … to focus resources toward the rusfertide program" ([Protagonist Q3 2022](https://www.prnewswire.com/news-releases/protagonist-reports-third-quarter-2022-financial-results-and-provides-corporate-update-301672171.html)); GDA-201 in lymphoma, dropped the day Gamida Cell agreed a go-private debt restructuring ([SEC filing](https://www.sec.gov/Archives/edgar/data/1600847/000121390024026228/ea020263101ex99-1_gamida.htm)) |
| Operational | Enrollment, sites, supply, COVID-19, a regulatory or procedural hold not about safety | Registry: nomacopan in atopic keratoconjunctivitis ({nct('NCT04037891')}): "terminated early due to the disruptions caused by the ongoing COVID-19 pandemic." Traced: zolmitriptan patch in cluster headache: enrollment "at a rate slower than originally anticipated … decided to end enrollment" ([Zosano 8-K](https://www.sec.gov/Archives/edgar/data/1587221/000119312521202089/d175431d8k.htm)); avasopasem in COVID-19: "not feasible to complete the trial" as hospitalisations fell ([Galera 10-K](https://www.sec.gov/Archives/edgar/data/1563577/000095017022003292/grtx-20211231.htm)) |
| Positive readout, not yet advanced | The trial met its efficacy endpoint (fully or partly) and the program did not move on in this disease in the US | Traced: linperlisib in follicular lymphoma, approved in China after its Phase 2 ([Synapse](https://synapse.patsnap.com/drug/cdfe08a2ecab4b6ca83fab8af44a8671)); alidornase alfa in cystic fibrosis, positive Phase 2 then waiting for a partner ([Protalix](https://www.sec.gov/Archives/edgar/data/1006281/000114420417031384/v468532_ex99-1.htm)); imlifidase in Guillain-Barré, positive Phase 2 then replaced by a next-generation enzyme ([Hansa](https://www.hansabiopharma.com/media/press-releases/2024/hansa-biopharma-announces-positive-full-results-from-15-hmedides-09-phase-2-study-and-comparative-analysis-of-imlifidase-in-patients-with-guillain-barre-syndrome/)) |
| Did not actually stop (removed) | Development continued under another registry, region, name or combination | HS-20004 (noiiglutide) in type 2 diabetes went on to Phase 3 ({nct('NCT06649773')}); T89 in acute mountain sickness went on to a pivotal Phase 3 ({nct('NCT04993729')}) |
| Unknown (likely cause counted) | No source states a cause; the likely cause is the model's inference | DMT210 in atopic dermatitis: no results announced and both indications ended together → likely efficacy; icosapent in COVID-19: enrollment fell as vaccines spread, no results → likely operational |

**Known weaknesses.** On {v['n']} stops whose registry reason is known, run with the reason hidden, the traced cause
matched {pct(v['cause_accuracy_resolved'])} of the time (κ = {v['cause_kappa_resolved']:.2f}). Efficacy stops were recognised
{pct(v['by_truth']['efficacy']['likely_correct'])} of the time, but only {pct(v['precision_likely']['efficacy']['correct'])} of the stops it called efficacy were, and
safety stops were recognised {pct(v['by_truth']['safety']['likely_correct'])} of the time, so efficacy is an upper estimate and **safety is a floor** (sponsors also rarely state safety, and
a missed endpoint takes precedence over a safety signal). **Business** is the least reliable category: the model's
business calls were right {pct(v['precision_likely']['business_strategic']['correct'])} of the time, often confused with operational. "Positive readout" includes programs
whose primary endpoints were only partly met, and some recently quiet ones may still advance.

## Bottom bar: why efficacy failed

**Cohort.** Phase 2 and 3 programs stopped for efficacy or for PK, dose or formulation, as recorded in the registry
or as traced with a source. Efficacy causes that are only the model's likely cause are not broken down. Programs the
model refused to label (mostly gene and cell therapies) are left out.

**Evidence bundle.** For each program: the failed (index) trial's record, posted results and linked papers; the
drug's other trials with their classified outcomes; results posted by its Phase 1 trials; its FDA approvals; other
drugs on the same primary target in the same or a related disease; and PubMed abstracts on the drug's human
pharmacology (PK, occupancy, target engagement, biomarkers) and on the drug in the disease.

**Labelling (prompt C).** The model judges, in humans at the doses tested, the three pillars of Morgan et al.
(2012): exposure at the site of action, engagement of the target, and the expected pathway effect, each as
adequate, inferred adequate (the drug worked in another disease through the same target and tissue at a comparable
dose), inadequate, or no human data. It then gives one failure code, citing only the bundle. Validation rejects a
citation outside the bundle and a code that contradicts the pillars.

**Web search (prompt D).** Where the bundle had no human evidence on engagement (code U), the same model gets the
same bundle and searches the web (full-text papers, conference reports, FDA and EMA reviews, company releases),
citing only pages its searches returned. Its label replaces U where it decides one.

**F9 on a stop that is still for efficacy or exposure.** For traced and PK stops the index trial is the program's
last trial, not one the registry named as a failed efficacy test, and a registry stop traced again may still come
back as efficacy. Such a stop stays in the breakdown, coded by its pillars (engaged → F2; exposure or engagement
inadequate, or dose-limited → F1a; otherwise U).

### Groups and codes, with examples

| Group | Codes | Examples |
|---|---|---|
| Not engaged | **F1a**: exposure or engagement shown inadequate, or dose capped by tolerability below adequate engagement | Nemiralisib in activated PI3Kδ syndrome: "no convincing evidence of target engagement in the lung", sputum PIP3 unchanged ({nct('NCT02593539')}, {pm('36841351')}). Gefapixant in endometriosis: 38 of 94 patients on drug had no detectable drug at one or more visits ({pm('39260540')}). Bemnifosbuvir in COVID-19: lung levels above EC90, but no viral load reduction in patients ({pm('37338393')}, {pm('37928891')}) |
| Not engaged | **F1b**: another drug on the same target succeeded in this disease, and no evidence shows this one engaged | Topical TLR7 agonist LFX453 in actinic keratosis: 1/20 cleared vs 13/21 on imiquimod, an approved TLR7 agonist, in the same trial ({nct('NCT02404389')}). Topical JAK inhibitor ATI-50002 in alopecia areata, where oral JAK inhibitors are approved ({nct('NCT03354637')}). Ichorcumab in VTE: blocks only thrombin exosite 1, partial thrombus reduction, while other thrombin inhibitors work ({pm('31529590')}, {pm('30184110')}) |
| Engaged, no benefit | **F2**: engagement adequate or inferred, no benefit | Lacnotuzumab in triple-negative breast cancer: engaged circulating CSF1, PFS 5.6 vs 5.5 months ({pm('34615719')}). Entinostat in ovarian cancer: target inhibition shown at the dose used, no PFS gain ({nct('NCT02915523')}, {pm('34357781')}). Also venglustat in GBA1 Parkinson's and CSL112 after myocardial infarction (report text) |
| Engaged, no benefit | **F3**: wrong population or subtype, mechanism engaged | Histamine glutarimide in asthma: engaged (CCL2, CXCL10 fell), benefit confined to high-eosinophil patients ({pm('33095411')}). Vidofludimus in UC: miss tied to concomitant corticosteroids ({nct('NCT03341962')}) |
| Engaged, no benefit | **F4**: wrong endpoint or timing, a proximal effect shown | Lenabasum in dermatomyositis: improved skin activity in Phase 2, failed a muscle-weighted Phase 3 endpoint ({nct('NCT03813160')}, {pm('35490744')}). Evogliptin in aortic valve calcification: PET calcification activity fell, CT calcium volume did not ({pm('39260927')}) |
| Trial design, population, endpoint | **F7** (and F3/F4 without shown engagement) | Rezpegaldesleukin in UC: terminated for enrollment futility at 81 patients, 14 on placebo ({nct('NCT04677179')}). Idasanutlin in colorectal cancer: 4 patients in the arm ({nct('NCT03555149')}) |
| Toxicity offset efficacy | **F5**: on-target toxicity cancelled the benefit | Dilpacimab (VEGF/DLL4) with FOLFIRI in colorectal cancer: worse PFS than bevacizumab (HR 3.57), more deaths, a fatal perforation ({nct('NCT03368859')}, {pm('35920133')}) |
| No engagement data | **U**: no human evidence of engagement either way, even after the web search | VX-210 in spinal cord injury: only serum PK in humans, Rho inactivation shown only in rats ({nct('NCT02669849')}). Napabucasin in colorectal cancer: plasma PK measured, no human evidence of STAT3 inhibition ({nct('NCT02753127')}). HL301, a 7-plant extract with no defined target, in radiation pneumonitis ({pm('38565405')}) |
| Removed (not a failed efficacy test) | **F6** off-target toxicity, **F8** business; **F9** endpoint met or not an efficacy test, when tracing finds another cause | Counted under that cause in the top bar |

### Analysis

Programs are keyed by (drug, disease, phase), so labels survive a rebuild of the program table. Shares carry 95%
intervals from a bootstrap that resamples drugs (1,000 draws), since one drug's programs share its pharmacology.

- **Shares** of each group and code, Phase 2 and 3 together, by phase, outside oncology, and by origin.
- **Headline:** among failures whose mechanism was tested (engagement known either way), the share not engaged
  (F1a + F1b) against engaged without benefit (F2 + F3 + F4, with F3/F4 counted as trial design unless engagement
  was shown).
- **Timing:** how often adequate engagement was known before the index trial started, and whether it was shown in
  patients with the program's disease.
- **Sensitivity variants:** Phase 2 only; Phase 3 only; outside oncology; oncology; sponsor-stated efficacy
  reason; primary endpoint missed; registry-recorded efficacy only; traced stops only; direct pillar evidence only
  (inferred engagement counted as unknown); engagement counted only if shown before the index trial; one program
  per drug; high or medium confidence; the bundle labels before the web search.
- **Bounds:** the not-engaged share if every program with no engagement data were not engaged.
- **Source coverage:** share of programs with any human pillar source, and with engagement known, by modality and
  entry year, so "no engagement data" can be read as a gap in public data.
- **Construct checks** on data the labeller does not use as a rule, each a two-sided Fisher test: programs coded
  F2 should more often share their target with drugs that also failed in a related disease than F1a programs;
  F1a should more often have a same-target drug that reached Phase 3 or approval in the disease; F2 should be
  rarer with germline genetic support (Section 3) than F1a.

**Checks.** A second model (Claude Sonnet 5) with a stepwise prompt (prompt E) relabelled a seeded random sample of {r['sampled']} registry efficacy stops
and agreed on the not engaged / engaged / other split {pct(r['three_way_agree'])} of the time. Web-research agents labelled
{j['n']} programs from scratch, blind to the pipeline, and agreed {pct(j['three_way_agree'])} of the time
(κ = {j['three_way_kappa']:.2f}), with {j['contradictions']} programs called engaged by one and not engaged by the other. A deeper web search on 22 programs both had left undecided resolved 2.

## Appendix: full prompts

### A. Registry classification of each trial (`pipeline/outcomes.py`, task `trial_outcome`)

```text
{oc.CLASSIFY_SYSTEM}
```

### B. Tracing an unexplained stop (`pipeline/stop_causes.py`, task `stop_cause_inference` v2; web search, ClinicalTrials.gov blocked)

```text
{sc.SYSTEM}
```

### C. Efficacy-failure labelling from the bundle (`pipeline/attribution.py`, task `efficacy_failure_attribution` v1)

```text
{a.SYSTEM}
```

### D. Web search where the bundle had no engagement evidence (task `efficacy_attribution_search` v1)

The system prompt is prompt C with its second paragraph ("Judge only from the bundle…") replaced by:

```text
{a.SEARCH_JUDGE.rstrip()}
```

### E. Re-derivation check (task `efficacy_failure_attribution_check` v1)

```text
{a.CHECK_SYSTEM}
```
"""
    with open(DOC, "w") as f:
        f.write(doc)


if __name__ == "__main__":
    main()
