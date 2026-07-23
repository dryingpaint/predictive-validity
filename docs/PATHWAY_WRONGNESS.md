# How often do positive-evidence pathways fail in the clinic?

**Question:** conditional on strong target/pathway evidence, what fraction of drug programs still fail clinically?

**Interpretation guide:**
- **approved rate** = of drugs with this evidence tier, fraction that got approved
- **eff_fail rate** = fraction that failed for efficacy (real efficacy_fail + presumptive Ph3 silent kill merged)
- **any_fail rate** = 100% - approved rate = 'how often does this evidence not lead to approval'
- 'high' = evidence score ≥2 (or as noted); 'low' = evidence score 0-1

## All target-matched programs

n = 2770, approved = 230 (8.3%)

| Evidence dimension | high-ev n | high approved | high **any_fail** | high eff_fail | low-ev n | low approved | low any_fail | low eff_fail |
|---|---|---|---|---|---|---|---|---|
| Line C lit high (target cell) | 2177 | 9% | **91%** | 27% | 316 | 8% | 92% | 28% |
| Line D lit high (target animal) | 2074 | 9% | **91%** | 28% | 419 | 9% | 91% | 26% |
| Line E lit high (human PD) | 1570 | 12% | **88%** | 28% | 923 | 3% | 97% | 27% |
| ClinGen Strong/Def ≥1 (genetics) | 879 | 13% | **87%** | 25% | 231 | 6% | 94% | 26% |
| Mendelian ≥5 (genetics) | 516 | 14% | **86%** | 22% | 2124 | 7% | 93% | 29% |
| OT genetic ≥0.3 | 2327 | 9% | **91%** | 27% | 348 | 5% | 95% | 31% |
| OT animal model ≥0.3 | 2228 | 9% | **91%** | 27% | 81 | 19% | 81% | 28% |
| IMPC ≥3 KO phenotypes | 858 | 9% | **91%** | 27% | 262 | 10% | 90% | 27% |

## Reached Phase 2+ (efficacy testing)

n = 2087, approved = 209 (10.0%)

| Evidence dimension | high-ev n | high approved | high **any_fail** | high eff_fail | low-ev n | low approved | low any_fail | low eff_fail |
|---|---|---|---|---|---|---|---|---|
| Line C lit high (target cell) | 1656 | 11% | **89%** | 34% | 245 | 11% | 89% | 36% |
| Line D lit high (target animal) | 1581 | 11% | **89%** | 35% | 320 | 10% | 90% | 33% |
| Line E lit high (human PD) | 1196 | 15% | **85%** | 35% | 705 | 4% | 96% | 33% |
| ClinGen Strong/Def ≥1 (genetics) | 641 | 17% | **83%** | 33% | 177 | 8% | 92% | 32% |
| Mendelian ≥5 (genetics) | 349 | 18% | **82%** | 31% | 1644 | 9% | 91% | 35% |
| OT genetic ≥0.3 | 1745 | 11% | **89%** | 34% | 264 | 6% | 94% | 39% |
| OT animal model ≥0.3 | 1672 | 10% | **90%** | 35% | 72 | 21% | 79% | 32% |
| IMPC ≥3 KO phenotypes | 659 | 10% | **90%** | 34% | 187 | 11% | 89% | 36% |

## Reached Phase 3+ (pivotal)

n = 1182, approved = 180 (15.2%)

| Evidence dimension | high-ev n | high approved | high **any_fail** | high eff_fail | low-ev n | low approved | low any_fail | low eff_fail |
|---|---|---|---|---|---|---|---|---|
| Line C lit high (target cell) | 962 | 16% | **84%** | 53% | 131 | 18% | 82% | 59% |
| Line D lit high (target animal) | 909 | 16% | **84%** | 54% | 184 | 15% | 85% | 52% |
| Line E lit high (human PD) | 756 | 21% | **79%** | 51% | 337 | 6% | 94% | 60% |
| ClinGen Strong/Def ≥1 (genetics) | 380 | 24% | **76%** | 47% | 110 | 12% | 88% | 46% |
| Mendelian ≥5 (genetics) | 213 | 25% | **75%** | 41% | 920 | 13% | 87% | 57% |
| OT genetic ≥0.3 | 986 | 17% | **83%** | 54% | 158 | 9% | 91% | 61% |
| OT animal model ≥0.3 | 955 | 15% | **85%** | 54% | 46 | 33% | 67% | 43% |
| IMPC ≥3 KO phenotypes | 351 | 17% | **83%** | 54% | 98 | 15% | 85% | 60% |

## Intersection: what if MULTIPLE evidence lines are strong?

Programs where BOTH cell (Line C≥2) AND animal (Line D≥2) AND human PD (Line E≥2) are all high:

n = 1011

| outcome | n | % |
|---|---|---|
| approved | 147 | 14.5% |
| eff_fail | 361 | 35.7% |
| safety_fail | 17 | 1.7% |
| commercial_fail | 135 | 13.4% |
| enrollment_fail | 40 | 4.0% |
| silent_kill_ph2 | 172 | 17.0% |
| unclassified_fail | 132 | 13.1% |
| other | 7 | 0.7% |

**Adding genetic support (Mendelian≥5 OR ClinGen Strong/Def≥1):** n = 422

| outcome | n | % |
|---|---|---|
| approved | 93 | 22.0% |
| eff_fail | 136 | 32.2% |
| safety_fail | 1 | 0.2% |
| commercial_fail | 51 | 12.1% |
| enrollment_fail | 17 | 4.0% |
| silent_kill_ph2 | 69 | 16.4% |
| unclassified_fail | 52 | 12.3% |
| other | 3 | 0.7% |

## Absolute count: pathways that had positive evidence and still failed

**Line C lit high (target cell)** — Phase 3+ programs with high evidence: **1053**
- Approved: 220 (21%)
- Failed for efficacy: 526
- Failed for safety: 16
- Commercial/silent/other fail: 242
- **Total failed at Phase 3 despite strong evidence: 833 (79%)**

**Line D lit high (target animal)** — Phase 3+ programs with high evidence: **1004**
- Approved: 217 (22%)
- Failed for efficacy: 509
- Failed for safety: 14
- Commercial/silent/other fail: 216
- **Total failed at Phase 3 despite strong evidence: 787 (78%)**

**Line E lit high (human PD)** — Phase 3+ programs with high evidence: **855**
- Approved: 228 (27%)
- Failed for efficacy: 404
- Failed for safety: 13
- Commercial/silent/other fail: 175
- **Total failed at Phase 3 despite strong evidence: 627 (73%)**

**ClinGen Strong/Def ≥1 (genetics)** — Phase 3+ programs with high evidence: **380**
- Approved: 91 (24%)
- Failed for efficacy: 178
- Failed for safety: 4
- Commercial/silent/other fail: 92
- **Total failed at Phase 3 despite strong evidence: 289 (76%)**

**Mendelian ≥5 (genetics)** — Phase 3+ programs with high evidence: **213**
- Approved: 53 (25%)
- Failed for efficacy: 87
- Failed for safety: 3
- Commercial/silent/other fail: 59
- **Total failed at Phase 3 despite strong evidence: 160 (75%)**

**OT genetic ≥0.3** — Phase 3+ programs with high evidence: **986**
- Approved: 163 (17%)
- Failed for efficacy: 529
- Failed for safety: 16
- Commercial/silent/other fail: 226
- **Total failed at Phase 3 despite strong evidence: 823 (83%)**

**OT animal model ≥0.3** — Phase 3+ programs with high evidence: **955**
- Approved: 146 (15%)
- Failed for efficacy: 515
- Failed for safety: 17
- Commercial/silent/other fail: 221
- **Total failed at Phase 3 despite strong evidence: 809 (85%)**

**IMPC ≥3 KO phenotypes** — Phase 3+ programs with high evidence: **351**
- Approved: 61 (17%)
- Failed for efficacy: 188
- Failed for safety: 5
- Commercial/silent/other fail: 82
- **Total failed at Phase 3 despite strong evidence: 290 (83%)**

