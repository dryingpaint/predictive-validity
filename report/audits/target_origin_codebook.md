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
- mouse_genetics: knocked-out or mutant mice show the disease
- curated_pathway: a curated pathway shows a disease mutation disrupting the target
- cell_screen: a gene-knockout screen in human cells
- earlier_drug_other_disease: a drug on the target was approved for an unrelated disease
- observational_biomarker: the target or its product in patients' blood, another fluid or on imaging tracks the disease
- human_cell_perturbation: perturbing the target in human cells or tissue changes a disease phenotype
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
activity or course is observational_biomarker. A drug on the target approved for a related disease makes the pair
validated at entry, which is not an origin; earlier_drug_other_disease is an approval for an unrelated disease.

## Crosswalk to the evidence chart

The thirteen kinds are one list used two ways (the owner's decision of 2026-11-20 on #146): the report's evidence
chart (`report/evidence_lines.py`) asks whether each kind was present before entry, the origin asks which came first.
`pipeline.target_origin.CHART_LINE` holds the mapping; a test checks that every named column exists in the chart.

| origin | chart line (column) | the chart's wording |
|---|---|---|
| human_genetics | `g3` | inherited variants link the target to the disease (tiers: rare only, common only, both) |
| tumour_genetics | `somatic` | the gene is recurrently mutated in this cancer |
| curated_pathway | `reactome` | a curated pathway shows a disease mutation disrupting the target |
| diseased_tissue | `expression` | the gene's RNA level differs in diseased tissue; #154 adds the protein in patients' tissue |
| mouse_genetics | `altered_animal` | knocked-out or mutant mice show the disease |
| cell_screen | `crispr` | gene-knockout screens in human cells (registered line, to be drawn) |
| earlier_drug_other_disease | `approved_unrelated_only` | a drug on the target approved only for unrelated diseases |
| observational_biomarker | #154, fourth kind | its level tracking the disease in observational studies |
| human_cell_perturbation | #154, first kind | the target perturbed in human cells or tissue |
| animal_model_pharmacology | #154, second kind | the target perturbed in an animal disease model by means other than genetics |
| clinical_observation | #154, new line | an effect seen in people, such as a side effect |
| phenotypic_screen | none | not evidence about the target |
| unclear | none | |

## Reporting layers

For reporting only, never for a gate or a hypothesis, `pipeline.target_origin.LAYER` collapses the thirteen kinds into
six: genetics (human_genetics, tumour_genetics); tissue_biomarker (diseased_tissue, observational_biomarker);
model_systems (mouse_genetics, curated_pathway, cell_screen, human_cell_perturbation, animal_model_pharmacology);
earlier_drug (earlier_drug_other_disease); clinical_phenotypic (clinical_observation, phenotypic_screen); unclear. The
gate file reports kappa on this layer beside the thirteen-way kappa.

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
