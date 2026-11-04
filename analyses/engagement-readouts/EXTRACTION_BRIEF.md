# Extraction brief: name the engagement readout (layer 1)

You are given a CSV of efficacy-failed drug programs. Each row carries an LLM-written `rationale` that
judged whether the drug engaged its target in humans, plus the drug, its primary targets, the disease
and the three pillar verdicts. Your job is mechanical: say what readout the rationale relied on. Use the
rationale text only. Do not research, do not second-guess the verdict, do not read other rows' sources.

## Output: one CSV row per input row, same order, these columns

| column | values |
|---|---|
| `content_sha` | copied from the input |
| `key` | copied from the input |
| `readout` | what was measured, ≤ 12 words, in the rationale's own terms (e.g. "plasma HSP70 induction", "D2 receptor occupancy by PET", "serum LDL-C"); empty if none named |
| `readout_kind` | `occupancy` (PET/SPECT occupancy, free or total target level, receptor or enzyme activity measured in blood cells, ex-vivo blockade of a stimulus) · `target_product` (the target's own immediate output: an enzyme's product or substrate, a hormone the target controls, a transgene protein, viral load, phosphorylation of the target or its direct substrate in tissue) · `downstream_marker` (a biomarker or physiology further down the pathway: cell counts, lipids, HbA1c, FEV1, imaging, gene signatures) · `clinical_response` (efficacy in a trial used as evidence of engagement) · `exposure_only` (only PK or dose cited) · `none` |
| `matrix` | `blood` · `tissue` · `imaging` · `physiology` · `csf` · `urine` · `other` · empty |
| `subjects` | `patients_this_disease` · `patients_other_disease` · `healthy_volunteers` · `mixed` · `unknown` |
| `inference_basis` | `measured` (this drug, measured in people) · `other_disease` (engagement or efficacy of this drug in another disease) · `class` (another drug on the same target) · `none` |
| `specific_to_target` | `yes` if, on the face of it, only modulating this target moves the readout (free PCSK9, D2 occupancy, factor IX activity); `no` if other mechanisms move it too (eosinophils, FEV1, HbA1c, tumour shrinkage); `unsure` |
| `readout_canonical` | a short canonical name for the (target, readout) pair, lower-case, no spaces: `<TARGET>:<readout>` such as `HSP90:hsp70_induction`, `PCSK9:ldl_c`, `DRD2:pet_occupancy`. Reuse a name from the existing vocabulary list if one fits; otherwise coin one in the same form |
| `quote` | ≤ 25 words from the rationale that name the readout |
| `note` | ≤ 15 words, only if something needs saying (e.g. "two readouts cited; took the proximal one") |

## Rules

1. If the rationale names more than one readout, take the most proximal one (occupancy > target product >
   downstream > clinical) and mention the other in `note`.
2. If the verdict is `inadequate`, `readout` is what failed to move or was never shown; the other fields
   describe it the same way.
3. If the verdict rests on the drug having worked or engaged elsewhere, `inference_basis` is
   `other_disease` and `readout_kind` is whatever was measured there, if named, else `clinical_response`.
4. `readout_kind` is `none` only when the rationale gives no readout at all; then `readout` is empty.
5. Write the CSV with a header, quote fields that contain commas, keep every input row, and do not add
   columns. Report back the output path and the count of rows by `readout_kind`.
