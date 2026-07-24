# Genetics mirror: same rubric, opposite result

Originally scoped as Section 4 ("1-2 case studies that succeeded on thin
evidence" — PCSK9, semaglutide). Scoring both against the repo's own rubric,
**time-sliced to what was known when each program actually started** (not
present-day DB/API values), showed neither is a clean "thin evidence"
example — so this replaces that framing with a sharper one.

## Why PCSK9 and semaglutide don't work as "thin evidence" cases

- **PCSK9**: human genetics came *first* and drove the program. GOF variants
  causing autosomal-dominant hypercholesterolemia (Abifadel et al.,
  *Nature Genetics* 2003) and LOF variants protective against CHD (Cohen,
  Boerwinkle, Mosley & Hobbs, *NEJM* 2006) were both published before
  Amgen/Regeneron/Sanofi's antibody programs started (~2005-07) — indeed
  Amgen's program reportedly began right after Hobbs presented the
  then-unpublished LOF data. Scored honestly it's strong-to-maxed on every
  category, genetics included — the mirror of Section 3 in the *other*
  direction (strong evidence, and this time it worked), not a counterexample
  to "genetics matters."
- **Semaglutide**: by the time its own program started (~2006-09), GLP1R was
  already de-risked — exenatide was approved in 2005, liraglutide in 2009.
  Its own program wasn't thin-evidence; it inherited a validated target.

The real thin-evidence moment is the **class-founding program: exenatide**
(Byetta, Amylin/Eli Lilly), developed off Gila-monster-venom pharmacology in
the 1990s, before GWAS existed as a technology at all.

## The pairing

`genetics_mirror_clean.png` (publication-grade, data only) — two rows, same five-column rubric as
`CASE_SCORECARD.md` (Genetics + Mechanistic + Cell-pathway + Animal in-vivo +
Human PD, each 0-3), opposite genetics status, opposite outcome:

| | Genetics | Mechanistic | Cell-pathway | Animal in-vivo | Human PD | Outcome |
|---|---|---|---|---|---|---|
| **Anti-Aβ mAbs** (APP · Alzheimer's, program start ~2000s) | **Strong (3)** | 3 | 3 | 3 | 2 | FAILED |
| **Exenatide** (GLP1R · T2D, program start ~1990s) | **Absent (0)** | 2 | 2 | 3 | 3 | SUCCESS |

Anti-Aβ scores are from `CASE_STUDIES.md` (unchanged). Exenatide scores are
new, sourced below.

## Exenatide scoring — sources (all predate or coincide with the program, not present-day)

- **Genetics: 0 (Absent).** GWAS did not exist as a technology at exenatide's
  program start (~1990s) or even at its 2005 approval — the first T2D GWAS
  (Saxena et al., *Science* 2007) postdates approval, and GLP1R-specific
  common-variant associations came later still. There was no genetic
  evidence to score, for or against, because the method to produce it hadn't
  been invented yet. (Scoring GLP1R with *today's* data would give it nonzero
  genetic support — its current Open Targets genetic-association sub-score is
  ~0.78, which clears that component's ≥0.5 threshold. Its *aggregate*
  `genetic_only_v1` score comes to ~0.7, i.e. the "Weak" tier — not "Strong,"
  but not zero either. The point stands: hindsight would credit GLP1R with
  genetics it did not have when the program started — the same leakage problem
  already excluded from the Section 2 figures, showing up in genetics here
  instead of literature.)
- **Mechanistic: 2.** The GLP-1 hormone (proglucagon-derived) and its
  insulinotropic action were characterized through the 1980s; the GLP-1
  receptor was cloned in 1992 (Thorens, *PNAS*). Receptor pharmacology was
  established, but not atomic/crystal-structure characterization (that came
  much later) — hence 2, not 3.
- **Cell-pathway: 2.** GLP-1-stimulated cAMP/insulin secretion in isolated
  islets and β-cell lines was established by the early 1990s, alongside the
  receptor cloning.
- **Animal in-vivo: 3.** Eng's 1992 discovery of exendin-4 in Gila monster
  venom included its potent insulinotropic activity; follow-on studies
  through the mid-1990s showed strong glucose-lowering in diabetic rodent
  models (ob/ob, db/db mice; ZDF rats).
- **Human PD: 3.** Native GLP-1 infusion studies in type 2 diabetes patients
  — Gutniak et al., *NEJM* 1992; Nauck et al., *Diabetologia* 1993 — showed
  near-normalization of fasting and postprandial glucose. This human
  proof-of-concept existed *before* exenatide-specific Phase 1 trials began.
- **Outcome:** exenatide (Byetta) approved 2005; founded the GLP-1 receptor
  agonist class that liraglutide, semaglutide, dulaglutide, and tirzepatide
  later built on.

Sources: [Eng/exendin-4, NIA](https://www.nia.nih.gov/news/exendin-4-lizard-laboratory-and-beyond);
[GLP-1 discovery-to-therapy timeline, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10786682/).

## The honest takeaway

There isn't a clean "thin evidence everywhere, succeeded anyway" case in
either direction we checked. Successes cluster around either strong human
genetics (PCSK9-style) or strong, convergent *non-genetic* evidence
(exenatide-style) — never around uniformly weak evidence across the board.
Genetics is the single most informative category on average (Section 2's
ablation), but it isn't the only route to success: a target with no genetic
signal can still succeed if mechanistic, cell, animal, and human-PD evidence
all converge and reinforce each other, the way they did for GLP-1. (This is
one illustrative case, n=1 — exenatide shows genetics is not *necessary*, not
that convergent non-genetic evidence is generally *sufficient*; the average
still favors genetics per Section 2.)

This reframes Melissa's original Section 4 question ("what evidence is
useful when genetics is thin?") into a more precise one: not "how little
evidence is needed," but "what does it take to succeed *without* genetics" —
and the answer here is: everything else, maxed and convergent.

## Reproduce

`python3 analyses/plot_genetics_mirror.py` — writes `data/genetics_mirror.csv`
+ `genetics_mirror(.png|.svg)` and `_clean` variants (600 dpi PNG + editable
SVG). No DB access needed; all scores are cited above and baked into the
script.
