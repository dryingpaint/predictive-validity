# The related-success reading

`report/engaged_modes.py` splits stops whose target worked only in a MONDO-"related" disease (target fate
`worked_related`) by whether that disease is a subgroup of the program's disease (wrong patients), a stage of it
(wrong time), or a different disease (not causal). The reading behind `related_success_modes.csv` was made once, on
2026-11-19, as follows.

- **Input:** `related_success_pairs.csv`, 114 headline stops, from `related_success_export.py`.
- **Reader:** one Claude model (a Claude Code subagent, Opus), given the prompt below and the input file, with no web
  access. It read the 114 rows, judged seven of them to need a specific call, and wrote the script below. The script
  labels those seven by hand and every other row with a listed success `different_disease`. That is its reading of
  the remaining rows, not a keyword rule.
- **Result:** 112 `different_disease`, 2 `wrong_patients`, 0 `wrong_time`, 0 `unclear`.
- **Check:** a 12-row random sample (seed 1) was read by the main session. All 12 were different diseases, for
  example asthma and COPD, rheumatoid arthritis and lupus, glioblastoma and brain metastases.

## Prompt

```
Read the CSV at <scratchpad>/worked_related.csv (114 rows). Each row is a drug development program (drug, phase, disease) that stopped because the drug engaged its target but the disease did not respond. Another drug on the same target later succeeded (FDA-approved, or met a Phase 2/3 primary endpoint) in a disease an ontology rated as "related"; those successes are listed in `related_successes` as "disease (drug, approved|met[, biomarker-selected])". Some rows have no listed success; treat those as `unclear`.

Classify each row into exactly one category by comparing the stopped program's disease with the related diseases where the target worked:
- `wrong_patients`: the target works in a subtype, subpopulation or biomarker-defined subset of the same disease the program treated (e.g. program in "breast cancer", success in "HER2-positive breast cancer"; program in "asthma", success in "eosinophilic asthma"; a biomarker-selected success in the same disease).
- `wrong_time`: the target works at a different stage, line of therapy or timing of the same disease (e.g. program in "metastatic X", success in "early X" or adjuvant; program in "Alzheimer disease", success in "prodromal Alzheimer").
- `different_disease`: the successful disease is a different disease, even if related or in the same organ or family (e.g. osteoarthritis vs ankylosing spondylitis; gastric cancer vs pancreatic cancer; cataract vs "eye disorder" as a generic parent). A broader parent term counts as different_disease unless it plainly is the same condition.
- `unclear`: no success listed, or you cannot tell.

Use your medical knowledge of the diseases only; do not browse. Be conservative: wrong_patients and wrong_time require that the success is genuinely in the same disease.

Write a CSV to <scratchpad>/worked_related_classified.csv with columns: key, category, reason (one short sentence naming the two diseases). Every input key exactly once. Then reply with the count per category and 3 example rows per category.
```

## Script the reader wrote

```python
import csv
rows = list(csv.DictReader(open('worked_related.csv')))
special = {
 '1316|MONDO:0005754|3': ('wrong_patients', 'Epilepsy with generalized tonic-clonic seizures vs epilepsy: same disease, but gabapentin\'s approval is in focal seizures, a different seizure-type subpopulation.'),
 '8072|MONDO:0005494|2': ('wrong_patients', 'Triple-negative breast carcinoma vs breast cancer: same disease, androgen therapy worked in hormone-receptor-positive breast cancer, not the triple-negative subset.'),
 '10137|MONDO:0018881|2': ('different_disease', 'Myelodysplastic syndrome vs FLT3-mutant acute myeloid leukemia: related myeloid neoplasms but distinct diagnoses.'),
 '1712|MONDO:0005369|3': ('different_disease', 'Carcinoid tumor vs lung/cutaneous neuroendocrine neoplasms, paraganglioma and SCLC: other neuroendocrine tumours, not plainly the same disease.'),
 '39|MONDO:0005129|3': ('different_disease', 'Cataract vs eye disorder: a generic parent term, not the same condition.'),
 '1399|MONDO:0001942|2': ('different_disease', 'Generalized anxiety disorder vs anxiety (symptom, lidocaine) and bipolar disorder: not the same disease.'),
 '1692|MONDO:0018881|2': ('different_disease', 'Myelodysplastic syndrome vs anemia: anemia is a generic condition, not MDS.'),
}
out = []
for r in rows:
    k = r['key']; succ = r['related_successes'].strip()
    if k in special:
        cat, reason = special[k]
    elif not succ:
        cat, reason = 'unclear', f"{r['disease']}: no related success listed."
    else:
        ds = []
        for s in succ.split(' | '):
            d = s.rsplit(' (', 1)[0]
            if d not in ds: ds.append(d)
        cat = 'different_disease'
        reason = f"{r['disease'][0].upper()+r['disease'][1:]} vs {', '.join(ds)}: different disease."
    out.append((k, cat, reason))
assert len(out) == len(rows) == len({o[0] for o in out})
with open('worked_related_classified.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['key', 'category', 'reason']); w.writerows(out)
from collections import Counter
print(len(rows), Counter(o[1] for o in out))
print(sum(1 for r in rows if not r['related_successes'].strip()), 'empty')
```
