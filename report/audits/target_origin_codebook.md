# Target origin hand check: codebook

One row per target × disease pair. The question: what first proposed this target for this disease, before any drug on
it was tested in patients for it? Read the records in the package (the same ones the model saw: the earliest 25 and
the latest 15 dated before the cutoff year, abstracts cut at 1,500 characters; the link opens the full record). You
may also follow the two search links, PubMed and Google Patents, which are already restricted to dates before the
cutoff year. Anything you find that way counts only if its own date is before the cutoff year. You never see the
model's answer.

## Origin (one primary; the definitions are the database's own)

- human_genetics: germline variants link the target to the disease (GWAS, gene burden, Mendelian)
- tumour_genetics: the gene is recurrently mutated in the cancer
- diseased_tissue: the gene's RNA or protein level differs in diseased tissue
- mouse_genetics: a genetic change in an animal links the target to the disease: knocked-out or mutant animals show the disease, or a knockout or transgene alters an animal model of it
- curated_pathway: a curated pathway shows a disease mutation disrupting the target
- cell_line_perturbation: changing the target in an established cell line (a genome-wide screen or a targeted experiment) changes a disease feature
- earlier_drug_other_disease: a drug on the target was approved for another disease, one not close enough to the program's to make the pair validated at entry
- observational_biomarker: the target or its product in patients' blood, another fluid or on imaging tracks the disease
- human_cell_perturbation: perturbing the target in primary human cells or tissue (not an established cell line) changes a disease phenotype
- animal_model_pharmacology: modulating the target by means other than genetics changes an animal model of the disease
- clinical_observation: an effect seen in people, such as a side effect
- phenotypic_screen: a molecule found without a target hypothesis came first
- unclear: no source settles it

The origin is the kind of evidence that first proposed the pair, not the strongest evidence and not the latest. Where
the sources show two kinds, the earlier is the origin and the other goes in secondary_origin. The provisional origin
shown on each card is the earliest dated item in the evidence databases; the model saw it too. Confirm or correct it
from the sources; do not copy it without a source.

Two boundaries the definitions draw. A change in the diseased tissue itself (RNA or protein, against normal tissue) is
diseased_tissue; a measurement outside it (blood, another fluid, imaging) that tracks the disease's presence,
activity or course is observational_biomarker. A drug on the target approved for the same or a very close disease
(MONDO Lin 0.8 or more) makes the pair validated at entry, which is not an origin; earlier_drug_other_disease is an
approval for any other disease, related or not. A genetic change to the target in an established cell line is
cell_line_perturbation; in primary human cells or tissue, human_cell_perturbation; in an animal, mouse_genetics,
whether the altered animal shows the disease or a knockout alters a model of it.

## Crosswalk to the evidence chart

The kinds are one list used two ways (the owner's decision of 2026-11-20 on #146, final structure of 2026-11-20 on
#159): the report's evidence chart asks whether each kind was present before entry, the origin asks which came first.
Each origin but phenotypic_screen and unclear is a kind of `report.evidence_lines.KINDS` under the same key, and
`pipeline.target_origin.CHART_LINE` reads each kind's chart column from there; a kind still planned (#154) has none
yet. The kind's definition in KINDS is the chart's wording.

## Reporting categories

For reporting only, never for a gate or a hypothesis, the gate file also reports kappa on the broad category of each
kind (`report.evidence_lines.CATEGORIES`: human genetics, in vitro and ex vivo, animals, human, the drug, target
safety risk), with phenotypic_screen and unclear each their own.

## Grade

- stated: a source says why the target was chosen for the disease (a rationale in an introduction or discussion, a
  review written before the cutoff, a patent's background).
- pattern: no source says so, but a source shows the defining observation of the category, published before any
  other kind of evidence for the pair.
- none: the sources would leave the origin to inference. Then the origin is unclear, and quote and source stay empty.

A label graded stated or pattern carries a verbatim quote from its source, the source's id as shown on the card
(PMID:… or the Europe PMC id) or its URL, and the source's own publication year.

## Discovery route (optional, descriptive)

Where did the first program's drug come from? phenotypic_screen (a screen with no target hypothesis), target_screen
(a high-throughput, fragment or virtual screen against the target; immunization or display for a biologic),
de_novo_design (antisense, siRNA, structure-based design), derived_from_active (a known drug, an endogenous ligand, a
natural product), repurposed_drug (an existing drug tried in this disease), unclear. Fill it in when a record settles
it; leave it blank otherwise.

## Filling the form

Every pair needs an origin and a grade. Quote, source and source year are required when the grade is stated or
pattern. Note is free text for anything the next reader should know. Answers save in the browser as you type; when
done, use "Copy answers as CSV" and send the text, or "Download CSV".

## Disputes sheet (`report/audits/target_origin_disputes.csv`)

One row per disputed field of a graded label (check method v2, `target_origin_run.md`, last section). Columns:
`subject_key` (ensembl_id|mondo_id), `symbol`, `disease`, `cutoff_year`, `origin` and `grade` as read, `definition`
(the origin's, from the column comment), `quote`, `sources`, `field` (quote, year or category), `fact` (the Drugs@FDA
approval fact for an earlier-drug label, on the pair's gene: close, an approval within Lin 0.8 of the disease before
entry; related, within 0.5; unrelated; none; empty for other origins), `first_drug`, `entry`, `sonnet`
and `sonnet_note`, `opus` and `opus_note` (each checker's answer to the field and its one-sentence reason), then
`verdict`, `reader`, `note` for the person. The question per field: quote, is the quote in a cited source; year, is
every cited web source dated before the cutoff year; category, does the quoted passage, with the sources, establish
the origin as defined. `verdict` is `yes` (the field holds) or `no`; leave it empty to leave the row open; any other
value stops `check`. `reader` is the person's name, `note` free text. Commit the sheet and run
`python -m pipeline.target_disease check --pairs window`: it applies each verdict to its field, restores a label whose
three fields are then yes, keeps the rest unclear, and rewrites the sheet with the rows still open. A verdict applies
only to a field the checkers left disputed; it never overrides a field the code or both checkers settled.

## Research file (`report/audits/target_origin_disputes_research.csv`)

A filled copy of the factual rows of the disputes sheet, written by `python -m pipeline.target_disease research`
(method `target_origin_research@v1`, `target_origin_run.md`, last section): the quote and year rows, and the category
rows of earlier-drug labels whose approval fact is none. Same columns as the sheet plus `decision_id` (the row in
`pv_evidence.llm_decision`). `reader` is the method name on every row the model answered; `verdict` is `yes` or `no`
where the answer settles the field and empty where it does not (a source no copy of could be read, an approval whose
date's precision cannot place it before or after entry, an indication without a MONDO id in the ontology); `note` is the evidence: the copy the
passage was read in and the words, or each source's year and where it was read, or each approval with its regulator,
date, indication and MONDO label and the tier the index's rule gives it. The committed sheet is not changed by the
pass. To apply the research verdicts, run `check --pairs window --disputes report/audits/target_origin_disputes_research.csv`;
to apply a person's verdicts instead, fill the committed sheet. A verdict from either file applies only to a field the
checkers left disputed.
