# Predictive Validity

**Which lines of preclinical evidence actually predict clinical success?**

More than nine in ten drug development programs that enter Phase 1 never reach approval, and we can see little of why. Jack Scannell named the problem *predictive validity*: drug discovery stalls when the models and evidence used to pick targets fail to predict what happens in patients.

Over the past 60 years the industry has added new model organisms, large-scale in vitro and in silico screening, and large compilations of omics data. This project asks which of these lines of evidence have actually improved clinical success rates. It has two parts:

1. **Industry failure modes.** Phase transitions, likelihood of approval and the reasons programs stop, by phase, disease area and modality, for programs entering each phase in 2015–2025: an updated companion to BIO's *Clinical Development Success Rates 2011–2020*.
2. **Predictive power of preclinical evidence.** Whether a program's target had human genetic, somatic, animal-model, expression, pathway or functional-screen evidence for the program's disease, as known before the program entered the phase, and how much each line raises the chance of approval.

## Report

[REPORT.md](REPORT.md) is generated from the database by `python -m report.render`; every number and table in it comes from `report/output/`, which `make report` regenerates (only its figure PNGs are tracked). [AUDIT.md](AUDIT.md) records the audit of the earlier draft (Google Doc): each claim's verdict, the data issues found and how each was fixed, the definitions the rebuild uses, and a work log.

## How it is built

The unit is a development program: one molecular entity developed for one disease (MONDO term).

| Step | Module | Output |
| :---- | :---- | :---- |
| ClinicalTrials.gov snapshot (all interventional drug/biological studies) | `pipeline.ctgov` | `preclin.ctgov_study` |
| Posted results and results papers (PubMed) | `pipeline.outcomes results`, `publications` | `preclin.ctgov_result_summary`, `preclin.trial_publication` |
| FDA approvals: Drugs@FDA, approval letters, labels (CDER); CBER biologics | `pipeline.fda`, `pipeline.cber` | `preclin.fda_*` |
| Substance names (FDA UNII), MONDO and EFO | `pipeline.unii`, `pipeline.ontology` | `preclin.unii_*`, `preclin.ontology_*` |
| Conditions → MONDO; intervention names → molecular entities → UNII | `pipeline.indications`, `pipeline.drugs` | `preclin.indication`, `preclin.moiety`, `preclin.drug_moiety` |
| Entity role per trial; programs | `pipeline.programs` | `preclin.ctgov_study_moiety`, `preclin.dev_program` |
| Approval of each program's disease; modality; disease area; trial outcomes; targets | `pipeline.approvals`, `drugs`, `indications`, `outcomes`, `targets` | `preclin.dev_program_approval`, … |
| Open Targets associations with yearly score series | `pipeline.opentargets` | `preclin.ot_association` |
| Analyses, label-quality checks, figures, report | `report.section1`, `section2`, `quality`, `figures`, `render` | `report/output/`, `REPORT.md` |

Classification and matching are done by LLM calls recorded in `pv_evidence.llm_decision` (prompt, output schema, model, provider, input hash and code commit for every decision); a rerun reuses a decision only when its input is unchanged. Independent audits of seeded samples measure each label's accuracy (`report.quality`).

To rebuild from source:

```sh
uv sync                 # Python environment from pyproject.toml / uv.lock
make all                # migrate, sources, identity, programs, labels, evidence, report
```

This needs `DATABASE_URL` and `ANTHROPIC_API_KEY` in `.env`, and `pdftoppm` and `tesseract` on the path (OCR of scanned FDA letters). Schema changes are ledgered migrations in `db/` (`python db/migrate.py apply`).

## License

MIT. If you build something on top of this work, please cite or link back.
