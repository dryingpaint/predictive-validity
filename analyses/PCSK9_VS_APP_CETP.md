# PCSK9 vs. APP vs. CETP — three well-supported programs, one succeeded

A head-to-head for the Section 3/4 "strong evidence, still failed" story. The
question that prompted it: is **BACE1** a fair evidence-matched comparator to
**PCSK9** (the success case)? Answer: no — BACE1 ties PCSK9 on the aggregate
genetic score but not on substance (BACE1 has 0 ClinGen curations and 0
causally-linked diseases; its score is carried by association-flavored Open
Targets numbers). A BACE1-vs-PCSK9 contrast invites the true rebuttal *"PCSK9
just had better genetics."* Two targets survive as genuine head-to-heads:
**APP** (genetics as strong as / stronger than PCSK9, still failed) and **CETP**
(matched evidence *type*, still failed). This note works through both.

The figure (`data/headtohead_scorecard_clean.png`, editable `.svg`) walks the
causal chain left to right and colours where each program holds or breaks: all
three have genetics and all three moved their biomarker as designed — they only
diverge at "is the biomarker actually causal for the hard outcome?". Regenerate
with `python3 analyses/plot_headtohead_scorecard.py` (scores baked in from the
table below; no DB needed to plot). Supporting genetics components are in
`data/headtohead_scorecard.csv`.

All genetics below is from `preclin.v_target_evidence_wide` via the repo's own
`genetic_only_v1` scorer, pulled present-day (2026). **Present-day scoring is
hindsight** — same caveat as the case-scorecard and genetics-mirror PRs; the
point of this exercise is "even with everything we know now, genetics did not
guarantee success," not a time-frozen prediction.

## The evidence table

| Target | genetic_only_v1 | tier | ClinGen | Mendelian (dom) | GWAS sig | OT-genetic | n_causal_dis | LLM mech/cell/animal/PD | Outcome |
|---|---|---|---|---|---|---|---|---|---|
| **PCSK9** | **1.3** | Moderate | 1 | 4 (2) | 1,410 | 0.99 | **5** | 3/3/3/3 | **approved** |
| **APP** | **1.6** | **Strong** | 1 | **15 (7)** | 40 | 0.65 | 3 | 3/2/2/2 | failed |
| **CETP** | 0.7 | Weak | 0 | 2 (1) | 2,498 | 0.98 | 3 | 3/2/2/1 | failed |
| BACE1 (for contrast) | 1.0 | Moderate | 0 | 1 (0) | 112 | 0.88 | **0** | 3/2/3/2 | failed |

(LLM lines are present-day and leakage-prone — approved drugs accrue
confirmatory literature — so they are texture, not load-bearing here.)

Note the three "shapes" of strong genetics: PCSK9 and CETP are **Mendelian +
massive-GWAS** lipid targets; APP is **Mendelian-dominated** (rare familial
mutations, modest common-variant signal). Different architectures, same
question — did the genetics translate.

## PCSK9 — what "good genetics" looks like end-to-end (the success)

PCSK9 is the cleanest genetics-to-approval chain in the dataset:

- **A complete allelic series.** Gain-of-function variants *cause* autosomal-
  dominant hypercholesterolemia (Abifadel et al., *Nat Genet* 2003).
  Loss-of-function variants *protect*: ~15–28% lower LDL and ~47–88% lower CHD
  risk in lifelong carriers (Cohen, Boerwinkle, Mosley & Hobbs, *NEJM* 2006).
- **The genetics validates the whole chain, not just the biomarker:**
  target → LDL → **hard clinical outcome (CVD events)**, with a dose-response
  across the allelic series and a lifetime of human exposure behind it.
- **The drug recapitulates the protective LOF phenotype** — anti-PCSK9
  antibodies lower LDL ~60% and reduce events. Amgen's program reportedly began
  right after Hobbs presented the unpublished LOF data.

That last point is the standard PCSK9 gets judged against: genetics that
already proved, in humans, that hitting this node moves the *outcome you care
about*.

## APP — genetics stronger than PCSK9, and the drugs still failed

**APP scores 1.6 (Strong) — higher than PCSK9's 1.3.** And it is not a scorer
fluke; APP's genetic architecture is, if anything, richer than PCSK9's:

- **15 Mendelian variants, 7 dominant** — the familial-Alzheimer's mutations
  (APP duplications, Swedish/London missense), ClinGen-curated.
- **A protective allelic-series variant of its own** — the Icelandic *A673T*
  variant lowers Aβ and protects against AD and late-life cognitive decline
  (Jonsson et al., *Nature* 2012) — the direct structural analogue of PCSK9 LOF.
- **A human copy-number natural experiment** — Down syndrome (trisomy 21, an
  extra *APP* copy) produces near-universal early AD.

So on genetic support APP is *at least* PCSK9's equal. Yet solanezumab and
bapineuzumab (anti-Aβ antibodies) failed across multiple Phase 3 trials.

**Why the genetics didn't save it — the useful part:** APP genetics airtightly
validates **target → biomarker (Aβ)**. What it does *not* guarantee is the
**biomarker → hard-outcome (cognition)** link *for the drug, stage, and
population actually tested*:

- **Stage/reversibility.** LDL drives atherosclerosis continuously, and lowering
  it helps even late. Amyloid appears to act as an *early* trigger; by the
  dementia stage, downstream tau pathology and neurodegeneration are
  self-sustaining, so removing amyloid late does little. PCSK9's biomarker acts
  in real time; APP's is "early trigger, irreversible downstream."
- **Population.** Familial-AD genetics is airtight for *familial* disease; the
  antibodies were tested largely in *sporadic* late-onset AD.
- **Effect size / species.** The cognitive benefit implied by the genetics was
  overpredicted by mouse models, and the "toxic species" question (soluble Aβ
  vs. plaque vs. protofibrils) meant even target engagement was subtle.

And the amyloid hypothesis was **partially right**: the later, earlier-stage,
protofibril-targeted antibodies (lecanemab, donanemab) *do* slow decline ~30%.
That sharpens the lesson rather than dulling it — **genetics tells you the node
is causal; it does not tell you a given drug, at a given stage, in a given
population, will clear the efficacy bar.**

> **APP's lesson:** genetics can be as strong as or stronger than the success
> case and the program still fails — on the *therapeutic proposition* (stage,
> population, effect size, reversibility), not on target validity. "Right
> target, wrong drug/stage." You cannot wave this away as weak genetics, which
> is exactly why it's a better flagship than BACE1.

## CETP — the genetics existed, and was misread

CETP is the tightest **conceptual** head-to-head with PCSK9, even though the
scorer calls it "Weak" (0.7):

- **Same disease area, same logic.** Human LoF carriers with a favorable lipid
  phenotype — PCSK9 LOF → low LDL; CETP LOF → high HDL.
- **Same pharmacological success.** Torcetrapib raised HDL ~60%, exactly as
  designed — the biomarker moved as predicted, just like anti-PCSK9's LDL drop.
- **Opposite outcome.** Torcetrapib *increased* mortality (ILLUMINATE, 2006) via
  an off-target aldosterone/blood-pressure effect; and the *clean* successors
  that removed the off-target effect (anacetrapib — modest; evacetrapib,
  dalcetrapib — failed) showed the **on-target HDL-raising hypothesis itself
  didn't deliver outcomes.**

**The discriminating variable is Mendelian randomization.** LDL is causal for
CVD (so PCSK9 works); **HDL is not** — HDL-raising alleles don't reduce
myocardial infarction (Voight et al., *Lancet* 2012), and CETP-variant effects
on CVD track their LDL/apoB change, not their HDL change. The genetics pointed
at a biomarker (HDL) that turned out to be a *bystander*, not on the causal path.

> **CETP's lesson:** the *presence* of human genetics is not the same as the
> *correct causal interpretation* of it. CETP had LoF carriers with a
> good-looking lipid phenotype, and it was misread — association ≠ causation,
> even for a Mendelian-flavored signal. This is precisely the distinction the
> aggregate genetic score cannot make on its own.

## The two failures are orthogonal — that's why you want both

| | PCSK9 (success) | APP (fail) | CETP (fail) |
|---|---|---|---|
| Human genetics present? | yes | yes (stronger) | yes (misread as strong) |
| target → biomarker validated? | yes (LDL) | yes (Aβ) | yes (HDL) |
| **biomarker → hard outcome causal?** | **yes (LDL, by MR)** | yes for familial AD, but tested where downstream is irreversible | **NO (HDL non-causal by MR)** |
| drug moved the biomarker? | yes (~60%) | yes (Aβ cleared) | yes (~60%) |
| Outcome | **approved** | failed | failed |
| Why genetics didn't save it | — | right node, wrong **stage/population/effect-size** | biomarker **off the causal path** |

Two distinct ways strong genetics fails to guarantee success:
**APP = right target, wrong therapeutic execution; CETP = the genetics was
misread (association mistaken for causation).** PCSK9 succeeded because its
genetics validated the *entire* chain to the hard outcome and the drug
recapitulated a protective human variant.

## Scorer-calibration note (flag for Melissa)

- **PCSK9 1.3 vs. CETP 0.7 — the entire 0.6 gap is the ClinGen term.** PCSK9 has
  a curated gene-disease validity entry (familial hypercholesterolemia, a
  *disease* with hard outcomes); CETP does not (CETP deficiency is a lab value —
  high HDL — not a curated disease). This is arguably *signal*: the scorer is
  separating "monogenic-disease genetics" from "quantitative-trait genetics," and
  the disease-anchored kind is what tracked the outcome here. But it means the
  scorer **undervalues strong-MR quantitative-trait genetics** — exactly the
  PCSK9/CETP flavor — so a "Weak 0.7" for CETP understates how much genetic
  information actually existed (it was strong and *misleading*, not absent).
- **APP 1.6 > PCSK9 1.3** shows the scorer correctly ranks APP's genetics as
  top-tier — and APP *still failed*. That is the whole point: the score measures
  genetic *support*, not therapeutic *tractability*.

## Recommendation for the piece

1. **Promote APP to the flagship "strong genetics, still failed" case** (replaces
   or leads BACE1). It's unassailable on genetics (Mendelian familial disease +
   protective allelic-series variant + Down-syndrome natural experiment), so the
   failure lands squarely on execution, not on weak evidence.
2. **Pair CETP with PCSK9 as the "genetics misread" companion** — same disease
   area, same LoF-carrier logic, opposite outcome, discriminator = MR causality.
   It's the most surgical "why did one lipid-LoF drug work and the other kill
   people."
3. **Keep BACE1 only as an optional "on-target tox + wrong hypothesis" example,
   not framed as evidence-matched to PCSK9** (its genetics is genuinely weaker
   and non-causal).
4. Whatever the final lineup, add the standing hindsight caveat: all genetics
   here is present-day, consistent with the PR #3 / PR #4 disclosures.

## Sources (for fact-checking, not reproduction)

- Abifadel et al., *Nat Genet* 2003 (PCSK9 GOF → ADH); Cohen et al., *NEJM*
  2006 (PCSK9 LOF protective).
- Jonsson et al., *Nature* 2012 (APP A673T protective variant).
- Voight et al., *Lancet* 2012 (HDL non-causal by MR); CETP-variant CVD effects
  proportional to LDL/apoB.
- Torcetrapib ILLUMINATE (2006, increased mortality, off-target aldosterone);
  anacetrapib / evacetrapib / dalcetrapib outcomes trials.
- Consistent with the CETP and amyloid write-ups already in the repo's
  `CASE_STUDIES.md`.
