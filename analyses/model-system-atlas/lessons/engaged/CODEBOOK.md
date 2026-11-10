# Codebook: why did a drug class that engaged its target fail on efficacy?

Unit: one class (disease × mechanism) whose engagement headline matched and whose efficacy headline was
contradicted in the atlas. Code the **primary** reason the efficacy failed, from the entry text only (reason,
note, judgement, quote across the efficacy, engagement and dose entries). Add a **secondary** code when the
text clearly supports a second reason. Give a confidence (high / medium / low) and a one-line rationale that
points at the text.

## A. Target hypothesis (this is "target selection": the target plus the sign of the intended effect)

| code | name | use when |
|---|---|---|
| A1 | not_causal | the target's output moved in patients (biomarker, pathway readout, PD) and the disease did not: the target is a marker or a non-rate-limiting node, not a cause |
| A2 | wrong_stage | the target is causal but the intervention came at a disease stage where it no longer (or not yet) drives outcome |
| A3 | subgroup_only | the target is causal only in a definable subset of patients, and the trial enrolled unselected or wrongly selected patients |
| A4 | compensated | the target is causal but redundant or compensated: feedback, bypass pathway, resistance, an alternative source of the same signal |
| A5 | too_small | the target is causal but its achievable clinical effect is too small to matter against placebo or standard of care |
| A6 | wrong_direction | right target, wrong sign: the direction of modulation, or an on-target effect that offsets the benefit, was wrong |

## B. Modulation (the drug or its dosing, not the target)

| code | name | use when |
|---|---|---|
| B1 | insufficient_degree | engagement was partial, intermittent or below the degree or duration the biology needs; the declared "enough" (occupancy, PD, exposure) was set too low |
| B2 | schedule | the regimen or schedule (intermittent vs continuous, frequency, timing relative to other therapy) was wrong |
| B3 | compartment | engagement was shown in blood or a surrogate tissue but not at the disease site (brain, tumour core, airway, synovium) |
| B4 | modality | right target but the modality could not do what the biology needs (inhibition vs degradation, ligand vs receptor, scaffolding function, antibody vs small molecule) |

## C. Trial (the test, not the target or the drug)

| code | name | use when |
|---|---|---|
| C1 | endpoint | the primary endpoint or surrogate could not show the effect, or the endpoint that moved was not the one that governs approval |
| C2 | duration_power | the trial was too short, too small or stopped early to show the effect |
| C3 | population | the enrolled population (disease too advanced or too mild, heterogeneity, placebo response, background therapy) prevented a readout, without a claim that the target is causal only in a subgroup |
| C4 | context | the drug was tested in a combination or against a standard of care where its contribution could not show (add-on to an effective regimen, a comparator that already saturates the benefit) |

## U. Unclear

| code | name | use when |
|---|---|---|
| U | unclear | the text records the failure but gives no reason that fits A, B or C |

Refinement after the two codings were compared (2026-11-09): A1 also covers saturating or near-complete target
engagement (receptor occupancy by PET, complete enzyme block) with no disease effect, when the record shows the
trial could have detected one (a positive-control arm that worked, or adequately powered trials). The first
codebook required a named downstream output to have moved; the second coder read saturating occupancy alone as U,
which was the main source of disagreement (see LEGEND.md).

Rules: code what the entries say, not what you believe about the class. A class that failed for lack of
efficacy with target engagement proven and no stated reason is U, not A1. When the text says "target reached,
no benefit" and nothing more, that is U with a note, unless another entry gives the reason. A1 requires that
the moved readout is named.
