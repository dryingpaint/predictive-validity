# How the stop-cause and efficacy-failure figure is built

Figure: `report/output/figures/efficacy_attribution.png`. Code: `pipeline/outcomes.py` (registry
classification), `report/section1.py` (stops and their registry reason), `pipeline/stops.py` (the shared
definitions: cohort, final labels, which label settles which cause), `pipeline/stop_causes.py` (tracing),
`pipeline/attribution.py` (efficacy-failure labels), `report/stop_causes.py` and `report/attribution.py`
(analysis), `report/figures.py` (figure). Every model decision is stored with its full input, output, sources and
rationale in `pv_evidence.llm_decision`; each step's method is recorded in `preclin.analysis_method`.

The efficacy-failure codes, estimands and checks were fixed before any program was labelled. Three steps were
added after the first results: the web search for programs with no engagement evidence, the inclusion of traced
efficacy and PK stops, and the rules by which an efficacy label settles a stop's cause.

A **program** is one drug developed for one disease. Every industry program whose Phase 1, 2 or 3 began 2008–2025
(ClinicalTrials.gov) and stopped is traced and labelled (`pipeline.stops.TRACING_WINDOW`, `pipeline.stops.PHASES`).
The figure's bars show Phase 2 and 3 entries from 2008–2019, the Section 1 headline window; a second figure shows Phase
1 the same way, since Phase 1 trials rarely test efficacy; and the report compares entry periods and the 2015–2025
window. Registry
outcomes and endpoints are classified for every Phase 2/3 trial started from 2008 (`pipeline.outcomes.TRIALS_FROM`). Every model step uses Claude Opus 5.5 except the re-derivation check, which uses Claude Sonnet 5.

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
| Efficacy | Futility, missed primary endpoint, efficacy not competitive | Registry: pamrevlumab, Duchenne ([NCT03955146](https://clinicaltrials.gov/study/NCT03955146)): "Study did not meet its primary endpoint." Traced: FMX114 (fingolimod) in atopic dermatitis: "did not meet its primary endpoint" ([BioSpace](https://www.biospace.com/vyne-therapeutics-atopic-dermatitis-topical-fails-to-meet-primary-endpoint)); CMV immune globulin in pregnancy ([NCT05170269](https://clinicaltrials.gov/study/NCT05170269)): "terminated early as the number of maternal–fetal transmissions was close to the … historical control group" ([Arch Gynecol Obstet](https://link.springer.com/article/10.1007/s00404-026-08311-8)) |
| PK, dose or formulation (shown with efficacy) | Exposure, PK, dosing, formulation or manufacturability | Registry: interleukin-7 in sepsis ([NCT03821038](https://clinicaltrials.gov/study/NCT03821038)): "PK issue detected after bolus IV route administration." Traced: GSK2838232 in HIV: "its pharmacokinetic properties required it to be boosted … which led to the termination of its development" ([eClinicalMedicine](https://www.sciencedirect.com/science/article/pii/S2589537025005061)); fezagepras in IPF: dropped "following the analysis of the preliminary pharmacokinetic data" ([Fierce](https://www.fiercebiotech.com/biotech/liminal-stops-plan-to-advance-fibrosis-drug-after-seeing-pk-data)) |
| Safety | Adverse events, tolerability, a clinical hold for safety (on- or off-target) | Registry: IC265 in dry eye ([NCT05992922](https://clinicaltrials.gov/study/NCT05992922)): "Unexpected adverse events were observed." Traced: seladelpar in NASH: biopsies "revealed atypical histological findings … interface hepatitis" ([CymaBay release](https://www.globenewswire.com/news-release/2019/11/25/1951942/0/en/CymaBay-Therapeutics-Halts-Clinical-Development-of-Seladelpar.html)); batoclimab in warm AIHA: paused after "a physiological signal consisting of elevated total cholesterol" ([Fierce](https://www.fiercebiotech.com/biotech/immunovant-hits-pause-button-for-eye-drug-after-unexpected-cholesterol-spike)) |
| Business or strategic (incl. company events) | Portfolio prioritisation, commercial or competitive reasons, licence returned; or the company was acquired, ran out of money or closed | Registry: AVROBIO Fabry gene therapy ([NCT03454893](https://clinicaltrials.gov/study/NCT03454893)): "AVROBIO has deprioritized its Fabry disease program." Traced: PN-943 in UC: "De-prioritization of the PN-943 program … to focus resources toward the rusfertide program" ([Protagonist Q3 2022](https://www.prnewswire.com/news-releases/protagonist-reports-third-quarter-2022-financial-results-and-provides-corporate-update-301672171.html)); GDA-201 in lymphoma, dropped the day Gamida Cell agreed a go-private debt restructuring ([SEC filing](https://www.sec.gov/Archives/edgar/data/1600847/000121390024026228/ea020263101ex99-1_gamida.htm)) |
| Operational | Enrollment, sites, supply, COVID-19, a regulatory or procedural hold not about safety | Registry: nomacopan in atopic keratoconjunctivitis ([NCT04037891](https://clinicaltrials.gov/study/NCT04037891)): "terminated early due to the disruptions caused by the ongoing COVID-19 pandemic." Traced: zolmitriptan patch in cluster headache: enrollment "at a rate slower than originally anticipated … decided to end enrollment" ([Zosano 8-K](https://www.sec.gov/Archives/edgar/data/1587221/000119312521202089/d175431d8k.htm)); avasopasem in COVID-19: "not feasible to complete the trial" as hospitalisations fell ([Galera 10-K](https://www.sec.gov/Archives/edgar/data/1563577/000095017022003292/grtx-20211231.htm)) |
| Positive readout, not yet advanced | The trial met its efficacy endpoint (fully or partly) and the program did not move on in this disease in the US | Traced: linperlisib in follicular lymphoma, approved in China after its Phase 2 ([Synapse](https://synapse.patsnap.com/drug/cdfe08a2ecab4b6ca83fab8af44a8671)); alidornase alfa in cystic fibrosis, positive Phase 2 then waiting for a partner ([Protalix](https://www.sec.gov/Archives/edgar/data/1006281/000114420417031384/v468532_ex99-1.htm)); imlifidase in Guillain-Barré, positive Phase 2 then replaced by a next-generation enzyme ([Hansa](https://www.hansabiopharma.com/media/press-releases/2024/hansa-biopharma-announces-positive-full-results-from-15-hmedides-09-phase-2-study-and-comparative-analysis-of-imlifidase-in-patients-with-guillain-barre-syndrome/)) |
| Did not actually stop (removed) | Development continued under another registry, region, name or combination | HS-20004 (noiiglutide) in type 2 diabetes went on to Phase 3 ([NCT06649773](https://clinicaltrials.gov/study/NCT06649773)); T89 in acute mountain sickness went on to a pivotal Phase 3 ([NCT04993729](https://clinicaltrials.gov/study/NCT04993729)) |
| Unknown (likely cause counted) | No source states a cause; the likely cause is the model's inference | DMT210 in atopic dermatitis: no results announced and both indications ended together → likely efficacy; icosapent in COVID-19: enrollment fell as vaccines spread, no results → likely operational |

**Known weaknesses.** On 141 stops whose registry reason is known, run with the reason hidden, the traced cause
matched 59% of the time (κ = 0.52). Efficacy stops were recognised
88% of the time, but only 69% of the stops it called efficacy were, and
safety stops were recognised 52% of the time, so efficacy is an upper estimate and **safety is a floor** (sponsors also rarely state safety, and
a missed endpoint takes precedence over a safety signal). **Business** is the least reliable category: the model's
business calls were right 42% of the time, often confused with operational. "Positive readout" includes programs
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
| Not engaged | **F1a**: exposure or engagement shown inadequate, or dose capped by tolerability below adequate engagement | Nemiralisib in activated PI3Kδ syndrome: "no convincing evidence of target engagement in the lung", sputum PIP3 unchanged ([NCT02593539](https://clinicaltrials.gov/study/NCT02593539), [PMID 36841351](https://pubmed.ncbi.nlm.nih.gov/36841351/)). Gefapixant in endometriosis: 38 of 94 patients on drug had no detectable drug at one or more visits ([PMID 39260540](https://pubmed.ncbi.nlm.nih.gov/39260540/)). Bemnifosbuvir in COVID-19: lung levels above EC90, but no viral load reduction in patients ([PMID 37338393](https://pubmed.ncbi.nlm.nih.gov/37338393/), [PMID 37928891](https://pubmed.ncbi.nlm.nih.gov/37928891/)) |
| Not engaged | **F1b**: another drug on the same target succeeded in this disease, and no evidence shows this one engaged | Topical TLR7 agonist LFX453 in actinic keratosis: 1/20 cleared vs 13/21 on imiquimod, an approved TLR7 agonist, in the same trial ([NCT02404389](https://clinicaltrials.gov/study/NCT02404389)). Topical JAK inhibitor ATI-50002 in alopecia areata, where oral JAK inhibitors are approved ([NCT03354637](https://clinicaltrials.gov/study/NCT03354637)). Ichorcumab in VTE: blocks only thrombin exosite 1, partial thrombus reduction, while other thrombin inhibitors work ([PMID 31529590](https://pubmed.ncbi.nlm.nih.gov/31529590/), [PMID 30184110](https://pubmed.ncbi.nlm.nih.gov/30184110/)) |
| Engaged, no benefit | **F2**: engagement adequate or inferred, no benefit | Lacnotuzumab in triple-negative breast cancer: engaged circulating CSF1, PFS 5.6 vs 5.5 months ([PMID 34615719](https://pubmed.ncbi.nlm.nih.gov/34615719/)). Entinostat in ovarian cancer: target inhibition shown at the dose used, no PFS gain ([NCT02915523](https://clinicaltrials.gov/study/NCT02915523), [PMID 34357781](https://pubmed.ncbi.nlm.nih.gov/34357781/)). Also venglustat in GBA1 Parkinson's and CSL112 after myocardial infarction (report text) |
| Engaged, no benefit | **F3**: wrong population or subtype, mechanism engaged | Histamine glutarimide in asthma: engaged (CCL2, CXCL10 fell), benefit confined to high-eosinophil patients ([PMID 33095411](https://pubmed.ncbi.nlm.nih.gov/33095411/)). Vidofludimus in UC: miss tied to concomitant corticosteroids ([NCT03341962](https://clinicaltrials.gov/study/NCT03341962)) |
| Engaged, no benefit | **F4**: wrong endpoint or timing, a proximal effect shown | Lenabasum in dermatomyositis: improved skin activity in Phase 2, failed a muscle-weighted Phase 3 endpoint ([NCT03813160](https://clinicaltrials.gov/study/NCT03813160), [PMID 35490744](https://pubmed.ncbi.nlm.nih.gov/35490744/)). Evogliptin in aortic valve calcification: PET calcification activity fell, CT calcium volume did not ([PMID 39260927](https://pubmed.ncbi.nlm.nih.gov/39260927/)) |
| Trial design, population, endpoint | **F7** (and F3/F4 without shown engagement) | Rezpegaldesleukin in UC: terminated for enrollment futility at 81 patients, 14 on placebo ([NCT04677179](https://clinicaltrials.gov/study/NCT04677179)). Idasanutlin in colorectal cancer: 4 patients in the arm ([NCT03555149](https://clinicaltrials.gov/study/NCT03555149)) |
| Toxicity offset efficacy | **F5**: on-target toxicity cancelled the benefit | Dilpacimab (VEGF/DLL4) with FOLFIRI in colorectal cancer: worse PFS than bevacizumab (HR 3.57), more deaths, a fatal perforation ([NCT03368859](https://clinicaltrials.gov/study/NCT03368859), [PMID 35920133](https://pubmed.ncbi.nlm.nih.gov/35920133/)) |
| No engagement data | **U**: no human evidence of engagement either way, even after the web search | VX-210 in spinal cord injury: only serum PK in humans, Rho inactivation shown only in rats ([NCT02669849](https://clinicaltrials.gov/study/NCT02669849)). Napabucasin in colorectal cancer: plasma PK measured, no human evidence of STAT3 inhibition ([NCT02753127](https://clinicaltrials.gov/study/NCT02753127)). HL301, a 7-plant extract with no defined target, in radiation pneumonitis ([PMID 38565405](https://pubmed.ncbi.nlm.nih.gov/38565405/)) |
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

**Checks.** A second model (Claude Sonnet 5) with a stepwise prompt (prompt E) relabelled a seeded random sample of 150 registry efficacy stops
and agreed on the not engaged / engaged / other split 69% of the time. Web-research agents labelled
65 programs from scratch, blind to the pipeline, and agreed 82% of the time
(κ = 0.67), with 0 programs called engaged by one and not engaged by the other. A deeper web search on 22 programs both had left undecided resolved 2.

## Appendix: full prompts

### A. Registry classification of each trial (`pipeline/outcomes.py`, task `trial_outcome`)

```text
You read a clinical trial's registry record (title, phase, status, the sponsor's stated reason for stopping if any, and posted results if any) and record what happened. Keep four questions separate.

1. execution: withdrawn_before_enrollment (status WITHDRAWN or zero enrolled), stopped_early (terminated or suspended after enrolling), completed.
2. stop_reason (only when not completed; otherwise "not_applicable"): the sponsor's stated reason, by meaning not wording.
   efficacy_futility: lack of efficacy, futility, failed or negative interim/primary analysis.
   safety_tolerability: adverse events, safety signal, DSMB stop for harm, tolerability.
   pk_pd_or_formulation: pharmacokinetic, exposure, dose-finding or formulation problems.
   business_portfolio: an explicit business reason: portfolio prioritisation, strategic or commercial decision, funding, acquisition or merger, licence return, development programme discontinued for business reasons.
   sponsor_decision_unspecified: only "sponsor decision" (or equivalent) with no further reason.
   competitive_landscape: a competing therapy or changed standard of care made the trial unnecessary or unfeasible.
   enrollment_feasibility: slow or insufficient enrollment, recruitment difficulty.
   operational_or_site: site, investigator, logistics, contract or data-management problems.
   regulatory: regulator request, clinical hold, ethics/IRB issues, regulatory strategy change.
   manufacturing_supply: drug supply or manufacturing problems.
   covid19: stopped or paused because of COVID-19.
   replaced_by_new_protocol: superseded by another study or a protocol amendment.
   objectives_met_or_early_success: stopped because objectives were met, early efficacy, or planned completion.
   other / not_stated.
   secondary_reasons: other reasons stated (same vocabulary), possibly empty.
3. primary_endpoint (from posted results; "no_results" when none are posted): met (the prespecified primary comparison favoured the drug with statistical significance, or a single-arm primary objective was achieved), not_met (no significant difference, or a negative result on the primary objective), mixed (some primary endpoints met, others not, or significant only in a subgroup), not_assessable (results posted but the primary analysis was not performed or is uninterpretable, e.g. stopped early, purely descriptive PK/safety outcomes).
4. safety_signal: notable (the record shows a safety problem: stated in the stop reason, or a clear excess of deaths or serious adverse events in the drug arm), none_evident, unknown.
Then efficacy_failure: true when the record shows the drug failed to show efficacy (an efficacy_futility stop reason, or primary_endpoint not_met in a trial designed to test efficacy); false otherwise.
evidence: a short quote from the record supporting the stop reason or the endpoint judgement.
```

### B. Tracing an unexplained stop (`pipeline/stop_causes.py`, task `stop_cause_inference` v2; web search, ClinicalTrials.gov blocked)

```text
You find out why a drug development program stopped. A program is one drug developed for one disease; it stopped in the phase given, and its registry records state no reason, or only "sponsor decision", or a reason that turned out to be wrong. You are given the program's trials in that phase (records, posted results, linked papers), structured signals, and the drug's other programs.

Search the web for what happened: company press releases, quarterly and annual reports and SEC filings (10-K, 10-Q, 20-F, 8-K), pipeline updates, investor presentations, conference abstracts, publications and trade news (Fierce, Endpoints, BioSpace, Evaluate, company sites). Search for the drug's name and code names with the disease, and with words like discontinued, terminated, deprioritized, pipeline. ClinicalTrials.gov is not available to search. Use at most a handful of searches; stop when you have the answer or the trail is cold.

Give the cause of the stop:
- efficacy: no or insufficient efficacy, futility, a missed endpoint, or efficacy not competitive with standard of care.
- safety: adverse events, tolerability, a safety signal or clinical hold for safety (on- or off-target).
- pk_formulation: exposure, pharmacokinetics, dosing, formulation or manufacturability of the drug.
- business_strategic: portfolio prioritisation, commercial or competitive reasons, a partner returning rights, refocusing.
- company_event: the sponsor was acquired or merged and the program was dropped in integration, ran out of money, wound down or went bankrupt.
- operational: enrollment, site or supply problems, COVID-19, a regulatory or procedural hold not about safety.
- positive_not_advanced: the trial succeeded (met its endpoint) and the program still did not move on in this disease (e.g. approved outside the US, partnered and stalled, development moved to another formulation).
- development_continued: the program did not actually stop: it continued under another trial registry, region, name or combination.
- unknown: no source says or allows a reasoned inference.
evidence_kind: explicit_program (a source states the reason for this drug in this disease), explicit_drug (a source states why the drug as a whole was discontinued), results (published or posted results show the outcome, e.g. a missed endpoint, without a stated decision), context (an inference from circumstances, e.g. the company was acquired and the pipeline cut, or every program of the drug stopped together), none (unknown).
A cause other than unknown needs evidence_kind other than none. Quote the decisive sentence from a source in quote when evidence_kind is explicit_program or explicit_drug. Cite only URLs your searches returned, NCT ids and PMIDs from the bundle. Do not guess; prefer unknown to a cause no source supports.
confidence: high when a source states it for this program; medium when stated for the drug or strongly implied; low when inferred from context.
likely_cause: your best inference of the cause. When cause is known, likely_cause equals cause. When cause is unknown, reason from what the bundle and your searches show: e.g. the trial completed, results were never posted and every program of the drug stopped together (often efficacy or safety, judged by what else is known); the sponsor was a small private company that stopped all activity (company_event); the drug kept going in its other diseases and this indication was dropped quietly (business_strategic, unless results point to efficacy). Use unknown only when nothing tilts it. likely_basis: one sentence on what the likely cause rests on.
rationale: at most 100 words.
```

### C. Efficacy-failure labelling from the bundle (`pipeline/attribution.py`, task `efficacy_failure_attribution` v1)

```text
You explain why a drug development program stopped after a failed efficacy readout. You are given an evidence bundle: the program's index trial (the trial that failed), the drug's other trials with their classified outcomes, results posted by its Phase 1 trials, its FDA approvals, other drugs on the same target in the same or a related disease, and PubMed abstracts about the drug. Every source has an id (an NCT id or PMID:n).

Judge only from the bundle. Never fill a gap from memory: if the bundle does not show something, it was not shown. Cite the ids you relied on.

First, the three pillars (Morgan et al. 2012), each for humans, at the doses taken into the index trial or comparable ones:
1. exposure: the drug reached its site of action (plasma exposure for a systemic target; CSF or tissue levels, or brain penetration, for a CNS or tissue target).
2. engagement: the drug bound or engaged its target (receptor occupancy, enzyme inhibition, target protein or ligand lowered, knockdown of the transcript).
3. pathway: the expected immediate functional or pathway effect followed (a downstream biomarker moved as the mechanism predicts).
For each answer:
- adequate: shown in humans at a level the sources treat as sufficient (e.g. high occupancy, near-complete inhibition, a clear dose-dependent biomarker change);
- inferred_adequate: not measured directly, but the drug met a clinical efficacy endpoint in another disease through the same target and tissue compartment at a comparable dose, so the pillar must have held there (state this in the rationale);
- inadequate: shown insufficient (low or partial occupancy, poor tissue penetration, biomarker unchanged), or the dose was capped by tolerability below the level needed;
- no_human_data: the bundle has no human evidence either way. Animal or in vitro data do not count.
Also: engagement_in_disease (was engagement shown in patients with this program's disease, not only in healthy volunteers or another disease), engagement_before_index (was that engagement evidence registered or published before the index trial started), dose_limited (tolerability capped the dose below what engagement needed).

Then the primary failure code:
- F1a: exposure or engagement inadequate, or dose capped by tolerability below adequate engagement. The mechanism was not properly tested.
- F1b: the molecule, not the target: another drug on the same target succeeded (approved or met a pivotal endpoint) in this disease or a close subtype, and no pillar evidence shows this drug engaged adequately.
- F2: engagement adequate or inferred_adequate, and at least one other pillar not inadequate, yet no clinical benefit: the target or mechanism does not drive the disease as tested.
- F3: wrong population or subtype: benefit confined to a subgroup, or the sources attribute the failure to patient selection or disease heterogeneity, with the mechanism engaged or not in question.
- F4: wrong endpoint or timing: a proximal or biomarker effect was shown in this disease and the clinical endpoint, duration or disease stage is what the sources blame.
- F5: efficacy offset by on-target toxicity.
- F6: off-target or molecule-specific toxicity ended the program.
- F7: trial design or execution: high placebo response, underpowered, operational problems, the sources say the trial could not answer the question.
- F8: commercial: the bundle shows the program stopped for business reasons and the readout was not a failure.
- F9: not an efficacy failure of the drug: the index trial met its primary endpoint, missed only a non-inferiority margin against an active drug, or was not an efficacy test of this drug.
- U: indeterminate. Engagement is no_human_data and nothing in the bundle separates a drug that never engaged from a target that does not matter. Use U whenever that is the case; it is a correct answer, not a failure.
Rules: F2 requires engagement adequate or inferred_adequate. F1a requires exposure or engagement inadequate, or dose_limited. F1b requires engagement not adequate. U requires engagement no_human_data. Pick the code the evidence supports most directly; list other codes that also apply in secondary_codes.

confidence: high when the sources state the reason or the pillars are measured directly; medium when inferred; low when the bundle is thin. rationale: at most 120 words, citing ids.
```

### D. Web search where the bundle had no engagement evidence (task `efficacy_attribution_search` v1)

The system prompt is prompt C with its second paragraph ("Judge only from the bundle…") replaced by:

```text
The bundle does not show human evidence of whether this drug engaged its target. Search the web for it: full-text papers (PubMed Central, journal sites), conference abstracts and posters, FDA and EMA review documents (Drugs@FDA reviews, EPARs), company presentations and press releases, and Phase 1 or pharmacology results published outside ClinicalTrials.gov. Look for, in humans: drug levels at the site of action, receptor occupancy, target enzyme inhibition, target protein or ligand lowering, transcript knockdown, and a downstream biomarker moving as the mechanism predicts; and for what the sponsor or investigators said about why the program failed. Search the drug's name and code names with words like pharmacodynamics, target engagement, occupancy, biomarker, first-in-human, phase 1, and with the program disease. Use at most a handful of searches; stop when you have the answer or the trail is cold.

From here on, "the bundle" means the bundle together with the pages your searches return. Judge only from them. Never fill a gap from memory. Cite bundle ids and the URLs of the pages you relied on, and put the decisive sentence from a source in quote (empty if none).
```

### E. Re-derivation check (task `efficacy_failure_attribution_check` v1)

```text
You review one failed drug development program to decide whether the drug's target was ever properly tested in humans. You are given an evidence bundle with ids (NCT ids, PMID:n). Use only the bundle; when it does not show something, treat it as not shown. Cite the ids you used.

Work through these questions in order, writing a short note for each in `notes` before choosing anything:
Q1. Is there human evidence that the drug reached its site of action at the doses used in the failed (index) trial? (exposure)
Q2. Is there human evidence that it bound or engaged its target at those doses? (engagement)
Q3. Is there human evidence that the expected pathway or biomarker effect followed? (pathway)
For Q1-Q3 answer adequate, inferred_adequate (not measured, but the drug met a clinical efficacy endpoint in another disease through the same target and compartment at a comparable dose), inadequate (shown insufficient, or dose capped by tolerability) or no_human_data. Animal data do not count.
Q4. Did tolerability cap the dose below what engagement needed? (dose_limited)
Q5. Has another drug on the same target succeeded in this disease?
Q6. Did the index trial really fail on efficacy, or did it meet its endpoint, fail only a non-inferiority margin, or stop for business reasons?
Q7. Do the sources blame the population, the endpoint or timing, toxicity, or the trial's design or execution?

Only then choose the primary code:
F1a not adequately exposed or engaged (or dose-capped); F1b another drug on the target worked here and this one was not shown to engage; F2 engaged (adequate or inferred) yet no benefit; F3 wrong population or subtype; F4 wrong endpoint, duration or stage after a proximal effect in this disease; F5 on-target toxicity offset efficacy; F6 off-target or molecule-specific toxicity; F7 trial design or execution; F8 commercial stop, not a failed readout; F9 not an efficacy failure of the drug; U engagement unknown from the bundle, so no engagement and a wrong target cannot be told apart.
F2 needs engagement adequate or inferred_adequate; F1a needs an inadequate exposure or engagement, or dose_limited; F1b needs engagement not adequate; U needs engagement no_human_data.
```
