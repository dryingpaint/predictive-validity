# Trial failure modes (Section 1)

Data note for the "why do trials stop" figure. Factual reference only — narrative
lives in the post.

## What it shows

`data/failure_modes_clean.png` (+ `.svg`) — the classified reason 5,510 terminated
industry Phase 1–3 trials (2015–2025) were stopped, grouped into three families.
Publication-grade (data only); narrative lives in the post, not the figure.

| Category | % of classified terminations | Family |
|---|---|---|
| Commercial / strategic | 44.2 | Business & operational |
| Efficacy | 14.4 | Biology |
| Unclear / undisclosed | 14.4 | Other |
| Enrollment / operational | 11.4 | Business & operational |
| Regulatory / administrative | 3.2 | Business & operational |
| Planned (per protocol) | 3.2 | Other |
| COVID-19 disruption | 3.1 | Other |
| Safety / toxicity | 2.9 | Biology |
| Competitive landscape | 1.6 | Business & operational |
| Manufacturing / supply | 0.8 | Business & operational |
| PK / PD / formulation | 0.7 | Biology |

**Family totals:** Business & operational ≈ 61% · Other / undisclosed ≈ 21% ·
Biology (efficacy / safety / PK) ≈ 18%.

## Source & method

- `preclin.v_failure_taxonomy` — `why_stopped` classifications (Claude Sonnet,
  deduped one-per-trial) over industry Phase 1–3 trials in `preclin.classification`.
- Stated reasons are taken at face value; the figure carries no interpretation.

## Scope & limitations

- **Terminations only.** This is why trials were *stopped early*. A trial that ran
  to completion and missed its endpoint is not a "termination," so efficacy is
  under-counted here relative to all-cause program failure.
- **"Stopped early" was fixed at classification time; a few trials have since
  changed status in the registry.** The population was selected as
  terminated/withdrawn/suspended when the classifier ran. Re-checking all 5,510
  against the live ClinicalTrials.gov status today: 73.4% TERMINATED, 21.1%
  WITHDRAWN, 2.0% SUSPENDED, and ~3.5% (191 trials) now show a different status
  (recruiting, active, or completed) — registry updates or resumed trials since
  the snapshot. Excluding those 191 leaves every family total within 0.3pp of the
  headline (Business 58.0→57.7%, Biology 18.0→18.1%, Other 24.0→24.1%), so the
  distribution is unaffected; but any single NCT cited as an example should be
  spot-checked against its current status.
- **Masked-efficacy fraction is not measurable from this data.** The `why_stopped`
  records store only a category + confidence (no rationale text or secondary
  reason), so the share of "commercial / strategic" stops that are really quiet
  efficacy failures cannot be computed here. Quantifying it would require a new
  targeted extraction pass. (Note: only 805 / 2,434 commercial-strategic calls are
  high-confidence — a flag for follow-up, not a measurement of masking.)

## Reproduce

```bash
# figure only (uses the committed CSV, no DB):
python3 analyses/plot_failure_modes.py

# refresh the CSV from the database first:
DATABASE_URL='postgresql://…' python3 - <<'PY'
import os, psycopg2, pandas as pd
pd.read_sql("SELECT category, n_trials, pct_of_all_classified "
            "FROM preclin.v_failure_taxonomy ORDER BY n_trials DESC",
            psycopg2.connect(os.environ["DATABASE_URL"])
).to_csv("data/failure_taxonomy.csv", index=False)
PY
```
