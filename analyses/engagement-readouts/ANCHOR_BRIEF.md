# Anchor brief: how was this readout tied to this target in humans? (layer 2)

You are given a CSV of readout families. Each is one (target, readout) pair: a human measurement that an
efficacy-attribution label used as evidence that a drug had engaged the target, where the measurement is not
itself the target (a downstream marker, a product other things also make, a cell count, a physiology). The
question for each family is the same: **what established, in humans, that this readout moves when this target
is modulated, and when did that become known?**

Answer from the literature, with one source per family that you have actually read (abstract level is
acceptable; say so). Budget: at most 12 tool calls and 8 sources per family. Use the PubMed tools
(`mcp__plugin_bio-research_pubmed__*`), WebSearch and WebFetch. No database access. Do not read other
batches or any file outside your batch and this brief. Work in a private scratch subdirectory named after
your batch; the scratchpad is shared with sibling agents and generic filenames get overwritten.

## The anchor kinds, strongest first

| `anchor` | meaning | example |
|---|---|---|
| `genetics` | people carrying variants in the target gene show the readout change | SLC5A2 loss of function → glucosuria; PCSK9 loss of function → low LDL-C |
| `direct_assay` | a human study related the readout to directly measured target occupancy or activity (PET, ex-vivo binding, enzyme activity in the same subjects) | D2 occupancy by PET vs prolactin rise |
| `prior_drug` | an earlier drug acting on this target moved the readout in humans, and that drug's engagement was itself established directly or by approval with this mechanism; the readout thereby became accepted class pharmacology | fingolimod lymphopenia before later S1P1 modulators |
| `pathway_only` | the link rests on preclinical or in-vitro biology (the target sits upstream of the readout in a pathway); no human anchor found | IL-13 → periostin from epithelial cell culture and mouse work only |
| `unknown` | could not be determined within budget | |

Record the **strongest** kind you can source, with its earliest year. If a weaker kind came earlier, say so in
`note`. The anchor must be independent of the programs in the family: a readout "validated" only by the same
drug's own trial is `pathway_only` unless that drug's engagement was shown directly (then `prior_drug`, year of
that evidence).

## Output: one CSV row per input family, same order, these columns

| column | values |
|---|---|
| `family` | copied from the input |
| `anchor` | one of the five kinds above |
| `anchor_year` | the earliest year the anchor was public (publication, label, or registry year); empty if `unknown` |
| `anchor_source` | one DOI, PMID, NCT id, or label URL that you read; empty if `unknown` |
| `anchor_quote` | ≤ 30 words verbatim from that source supporting the anchor; empty if `unknown` |
| `anchor_detail` | ≤ 25 words: what the anchor is (study, population, measurement) |
| `other_movers` | ≤ 15 words: what else moves this readout in humans (other mechanisms, disease state, diet); "none known" if specific |
| `specificity` | `specific` (on the human evidence, only this target's modulation moves it in the setting used) · `shared` (a few other mechanisms move it) · `nonspecific` (many things move it) · `unknown` |
| `confidence` | `high` (anchor read in full, clear) · `medium` (abstract level or indirect) · `low` (inferred) |
| `note` | ≤ 25 words, optional: weaker earlier anchors, caveats, wrong-target suspicion |

Write the CSV with a header, quote fields that contain commas, keep every input row, add no columns. Reply with
the output path and the count of rows by `anchor`.
