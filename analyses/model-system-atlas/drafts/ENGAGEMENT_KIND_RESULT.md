# The kind of engagement evidence did not separate classes that advanced from classes that did not

_Block for the report. Numbers from `engagement_kind_result.py`; the joined data are
`engagement_experiment.csv`. Suggested home: Section 3, after "Being more specific does not help", which is
the same shape of result._

## Block

**Showing the drug on its target directly did not predict better than inferring it from a downstream
marker.** For each of the 71 atlas contexts the human readout behind the engagement cell was graded by what
it measured: the target itself (receptor occupancy by PET, free target, ex-vivo blockade of a stimulus; 15
classes), the target's immediate product (transgene protein, viral load, gastric acid; 10) or a biomarker or
physiology further down the pathway (18). Three classes had the engagement prediction contradicted and 25
had no engagement comparison at all. The classes' own Phase 2 programs were then followed in the database.
Among the 2008–2019 Phase 2 entrants whose outcome is known, 42% (30 of 72; 31–53%) of the programs in
classes with direct evidence advanced to Phase 3, against 50% (29 of 58) in the product classes and 52% (55
of 106) in the downstream classes: direct against the two inferred kinds together, −10 points (−23 to +4),
p = 0.20. At Phase 3 the three kinds advanced at 71%, 68% and 74%. The interval is wide: the data cannot
rule out direct evidence predicting 20 points worse, or 4 points better, so the claim is that the atlas found
no difference, not that there is none.

Classes with any matched engagement evidence advanced more often from Phase 2 than classes with none (48%
against 29%, p = 0.006), but that is not a test of the evidence: a class whose programs reached Phase 3 is
the class that generated the trial papers in which an engagement comparison can be found, so the classes
with none are enriched for programs that stopped early. At Phase 3 the two groups are identical (71%).
Within the atlas itself, among contexts whose efficacy was also compared, the efficacy prediction held for 9
of 14 direct, 8 of 9 product and 12 of 15 downstream classes; the same readers saw the trial results, so this
is a consistency check rather than evidence.

## Table

| engagement readout behind the matched cell | classes | Phase 2 programs resolved | advanced to Phase 3 (95% CI) | Phase 3 resolved | advanced |
|---|---|---|---|---|---|
| target itself (occupancy, free target, ex-vivo blockade) | 15 | 72 | 42% (31–53) | 24 | 71% |
| target's product (transgene protein, viral load, acid, cGMP) | 10 | 58 | 50% (38–62) | 40 | 68% |
| downstream biomarker or physiology | 18 | 106 | 52% (42–61) | 38 | 74% |
| engagement contradicted | 3 | 6 | 0% (0–39) | 0 | – |
| no engagement comparison | 25 | 68 | 29% (20–41) | 14 | 71% |

Tests (two-sided Fisher): direct vs inferred p = 0.20 at Phase 2, 1.00 at Phase 3; product vs downstream
0.87 / 0.62; any vs none 0.006 / 1.00.

## Method note (appendix register)

The tier was assigned by one reader from the drafted entry's `model`, `quote` and `note` fields after the
run, without new research, and one tier per class even where its programs' evidence differed
(`engagement_kind_result.py`, the `TIER` table). Class membership and outcomes are the atlas join
(`lists.py`: strict `phase_rows` cohort, industry entry, novel entity, 2008–2019), with each program's
first Phase 2 and Phase 3 entry and its resolved event (advanced or suspended; censored programs
excluded) from `engagement_outcomes.py`. Phase 2 advancement is a sponsor decision, not an efficacy
test; the result says nothing about whether the drug worked.

## Scope of the claim

- The result supports "no detectable difference", not "the kind does not matter": the interval allows a
  20-point difference.
- The any-vs-none row is survivorship, not evidence that engagement evidence predicts advancement.
- The unit is the class (71) and the tier is a class-level label, not a per-program result.

## Rules consequence (§15)

`readout_tier` goes into schema v3 as a descriptive field (direct / proximal / downstream), drawn solid vs
hatched, and the column's headline is reported two ways: 61% "pharmacology showed up" and ~21% "target
engagement shown directly".
