# PV Raw Evidence Collection Contract

**Status:** Ingestion specification plus implemented-pilot status
**Scope:** Raw acquisition, source linkage, identity normalization, and reproducibility only
**Intended use:** Noncommercial research
**Last updated:** 2026-09-18

## 1. Goal

Build a reproducible collection of clinical trials, therapeutic interventions,
molecular targets or broader mechanisms, target/mechanism-associated phenotypes,
structured biological evidence, and relevant scientific documents.

The collection must retain raw source records and enough normalized identity to
answer:

1. Which interventions appear in ClinicalTrials.gov studies with an actual
   Study Completion Date from 2015 through 2025?
2. What specific molecular targets, target families/complexes, or broader
   biological mechanisms have sources attributed to each intervention?
3. Which phenotypes, diseases, genetic conditions, model phenotypes, and safety
   observations have sources associated with those targets or mechanisms?
4. Which publications and source records support each relationship?
5. Can the exact corpus be reconstructed without running a big-bang loader or
   depending on mutable local files?

This document deliberately does **not** define predictive features, success
labels, validation folds, evidence scores, or model-training decisions. Those
belong to later analytical specifications and may filter the same collected
evidence differently.

## 2. Decisions fixed for the initial collection

| Question | Initial decision |
|---|---|
| Intended use | Noncommercial research |
| Trial registry | ClinicalTrials.gov only |
| Trial-window field | ClinicalTrials.gov Study Completion Date, restricted to date type `ACTUAL` |
| Trial window | 2015-01-01 through 2025-12-31 inclusive; the replacement pilot begins with completion year 2015 |
| Registry study/intervention filter | `INTERVENTIONAL` and at least one registry intervention typed `DRUG` or `BIOLOGICAL` |
| Full text | Retain licensed or otherwise permitted full text in GCS |
| Predictive models | Out of scope for ingestion |
| LLM-assisted normalization | Deferred optional enrichment; the raw ingestion path is deterministic and preserves unresolved records |
| Historical versus current analysis | One collection; downstream queries filter dates and versions |

The actual Study Completion Date controls membership. ClinicalTrials.gov defines
this as the final data-collection date for primary outcomes, secondary outcomes,
and adverse events. Registration, first-posted, study-start, primary-completion,
results-posting, and update dates remain source facts but do not determine the
cohort. Records whose completion date is still `ESTIMATED` are not treated as
trials that ended in the range. Observational, device-only, procedure-only,
behavioral, exercise, diagnostic, radiation-only, supplement-only, and registry
`OTHER` studies are outside the development cohort.

### 2.1 Implemented pilot status as of 2026-09-18

The terms below are intentionally distinct:

- **designed** means this document specifies the behavior;
- **implemented** means code and schema exist;
- **retrieved** means a provider response was archived in Neon;
- **promoted** means a retrieved item also has an individually normalized row;
- **asserted** means a source-backed biological relationship row exists; and
- **full text retained** means a permitted JATS/PDF representation has an
  immutable source version; **GCS retained** additionally requires a linked
  `pv_source.object_blob`.

The current database is a pilot, not the completed corpus:

| Area | Current state | Not yet done |
|---|---|---|
| Schema | Migrations 28--52 are applied; source, canonical identity, LLM verification, literature, full-text, preclinical experiment, completion-date cohort, legacy-evidence bridge, durable literature-work tables, multi-subunit target components, page-streamed literature retrieval, and latest-complete query projections exist | Pinned official-release refresh adapters remain source-specific follow-up work |
| Trial cohort transition | The original first-posted-2025 pilot remains labeled legacy. The replacement cohort `pv_2015_actual_completed_drug_biological_pilot5_v1` records the first ten deterministic 2015 candidates, five reviewed inclusions, and five source-grounded exclusions | Full 2015 ingestion has not started |
| Filtered 2015 inventory | The complete manifest contains 7,064 actual-completion, interventional studies with at least one `DRUG` or `BIOLOGICAL` intervention. All ten pilot records are archived; a replay stored 0 and reused all 10 versions. The five-trial checkpoint has 24 idempotently planned active-policy literature items: 15 asset--indication and 9 distinct effective-target inventories. One one-hit boundary item completed through the orchestrator | The other 23 active-policy items remain pending; full 2015 ingestion awaits formatting review and an explicit scale-up decision |
| Asset/target resolution | The explicitly approved Terra run `46c3debc-ec74-450b-b9d2-788712685a7d` covers the five included 2015 candidates. ChEMBL parent/form/mechanism enumeration, PubChem, HGNC, and UniProt provide deterministic verification; unresolved formulations and ontology terms remain visible | Dedicated biologic/formulation authorities are still needed where ChEMBL cannot provide a unique parent |
| Literature discovery | Migration 51 activates `pv_literature_v2`. Its only provider queries are verified asset aliases + one normalized indication and one effective-target-only inventory. Target--indication is derived locally from the target-only corpus; no preclinical word list is used. Raw pages and canonical projections commit incrementally. The choriogonadotropin-alfa + female-infertility boundary query completed with one result. The 357,439 historical `asset_mention` links and older vocabulary-bounded rows remain immutable but are not active-policy input | The remaining active pilot items have not been run. Document relevance/preclinical classification, citation expansion, Crossref, and OpenAlex remain downstream |
| Promoted papers | Across all current literature families the database contains 345,505 canonical scholarly works; 322,962 have abstracts. PubMed XML enrichment exhausted every PMID-backed pending abstract, and source-absent abstracts have an explicit status | 1,776 works without a PMID remain `retrieval_pending` for another metadata source; 20,767 explicitly lacked an abstract in the retrieved sources |
| Full text | Seven rights-reviewed Europe PMC JATS files are retained as immutable Neon source versions and linked representations. Unsupported or unavailable items are recorded as per-run failures instead of aborting the batch | GCS is not configured, so there are no object URIs or PDFs in the current pilot. The configured path uploads licensed JATS and attempts advertised free PDFs only when a bucket is supplied |
| Biological evidence | Seven structured ChEMBL asset-target rows exist and keep source-native mechanism IDs. Literature co-occurrence remains a candidate relation | There are zero `target_phenotype_assertion` and zero extracted `preclinical_experiment` rows; those require later passage-backed enrichment |
| LLMs | A versioned Terra trial-semantic run covers the five-trial 2015 pilot. A separate post-ChEMBL mechanism-context run covers 17 assets and 20 fully enumerated mechanisms; its exact repeat produced 17 unchanged decisions. Exact inputs, strict JSON outputs, usage, source packets, validation status, and field-level comparisons are stored | Narrative document relevance and experiment-result extraction remain deliberately deferred |
| Related trials and indications | The source-explicit PIMPARK relationship is resolved through an archived ClinicalTrials.gov search and exact sponsor-ID match to `NCT03947216`. Six ontology-backed trial-indication links are promoted; literal trial strings and evidence quotes remain attached | Non-exact terms such as RSV infection and sedentary behavior remain in the review queue instead of being forced to an ontology ID |
| Structured phenotype/genetics | Existing HPO, GWAS Catalog, Open Targets/ClinVar lifts, ClinGen, and Mendelian rows are preserved in place and exposed through `v_structured_target_phenotype_evidence`. gnomAD-like constraint, GTEx/HPA expression, GO, Reactome, DepMap, and aggregated legacy IMPC summaries are exposed separately through `v_structured_target_context_evidence` so context is not mislabeled as causality. 52,999 source-native phenotype identifiers are bridged with no duplicate bridge keys | Legacy releases are explicitly `legacy_release_unknown` and mutable; pinned official releases must reconcile rather than overwrite them. The IMPC legacy rows are aggregate summaries, not raw procedure/MP rows |
| Retry behavior | Trial replay stored 0 and reused all 10 source versions. The phenotype/genetics bridge was committed twice with unchanged totals and zero duplicate bridge keys. Replanning the 24 active literature items adds zero work. Two-page capped streaming probes were deliberately marked `truncated` and excluded from active views. Exact target and completed asset-query repeats reused every canonical record with zero duplicate candidates; latest-complete views expose only the newest query execution. Stable work keys, leases, attempt history, and stale-lease recovery remain in place | Offline reconstruction of a literature run solely from archived search pages is not yet exposed by the CLI |
| Development scope | Policy `human_therapeutics_v2` retains every raw trial but gates expansion. Verified human-target therapeutics are in the main track; an actual verified drug asset can qualify a mixed behavioral/drug study; antibiotics and non-human therapeutic targets are excluded; vaccines remain separate | A distinct vaccine evidence model is intentionally not implemented while vaccines are outside the active development program |

Counts in this section describe the concrete Neon state checked on the date
above. They are not collection targets or scientific inclusion thresholds.

## 3. Simple system boundary

```text
ClinicalTrials.gov registrations
             |
             v
 intervention names and components
             |
             v
 asset identity + sourced target/mechanism claims
             |
             v
 target/mechanism phenotype databases + literature discovery
             |
             v
 raw records, abstracts, full text, and source-linked relationships
```

Only three schemas are needed initially:

| Schema | Contents |
|---|---|
| `pv_source` | Source catalog, releases/snapshots, acquisition runs, raw record versions, documents, GCS objects, licenses, and retrieval logs |
| `pv_core` | Canonical trials, interventions/assets/components, molecular targets, mechanisms/processes, phenotypes/diseases, identifiers, aliases, and document links |
| `pv_evidence` | Sourced asset-target, asset-mechanism, target-phenotype, and mechanism-phenotype assertions |

`pv_mart`, feature matrices, outcomes, and model snapshots are not part of this
ingestion phase.

### 3.1 Development-scope boundary

Raw acquisition and analytical eligibility are deliberately separate. Every
trial selected by the reproducible registry manifest is archived even when it
is outside the current development program. The versioned
`human_therapeutics_v2` policy controls only downstream expansion:

| Class | Raw trial retained | Main target/preclinical expansion |
|---|---|---|
| Verified human-target or verified human-mechanism therapeutic | yes | yes |
| Antibiotic | yes | no; excluded |
| Therapeutic-primary bacterial, viral, fungal, or parasitic target | yes | no; excluded |
| Vaccine | yes | no; separate vaccine track |
| Device, behavioral, exercise, or diagnostic intervention with no verified drug asset | yes | no; not applicable |
| Mixed trial with a verified in-scope therapeutic asset | yes | yes for the verified asset |
| Unresolved target domain | yes | no until resolved |

Here, **non-human target** means a pathogen or other non-human biological
target. It does not mean an extracellular human protein. Asset scope is derived
from structured therapeutic-primary target taxa and explicit antibiotic ATC
classes; unknowns default to unresolved rather than included. The materialized
decision, reason, inputs, method, time, and policy version are stored in
`pv_core.asset_development_scope` and `pv_core.trial_development_scope`.
Append-only history tables retain every distinct decision hash, while the
materialized scope tables retain one current decision per entity and policy.
Literature adapters consume only `pv_core.v_asset_indication_literature_scope`
and `pv_core.v_target_phenotype_literature_scope`.

## 4. What is raw and what is normalized

### 4.1 Raw records

Every source response is stored unchanged or as a byte-identical archived object
before normalization. Raw records include:

- ClinicalTrials.gov JSON;
- database release files and native rows;
- PubMed XML and API records;
- PMC/Europe PMC JATS, permitted PDFs, figures, and supplements;
- Crossref/OpenAlex/Unpaywall metadata responses;
- regulatory labels and reviews;
- source query manifests and result pages; and
- retrieval failures, exclusions, and tombstones.

### 4.2 Normalized identity

Normalization supplies stable links across raw records. It does not replace raw
values. For example:

- `RADICAVA`, `RADICAVA ORS`, `MCI-186`, and `edaravone` can link to one active
  moiety while retaining formulation and literal-name differences.
- `CFTR`, its HGNC identifier, UniProt protein, and named isoforms remain distinct
  but connected entities.
- A ClinicalTrials.gov condition string can map to MONDO/EFO while the literal
  registry string remains stored.

### 4.3 Evidence assertions

An assertion is a sourced relationship, not a final truth. Conflicting assertions
coexist. Every assertion identifies the source record/version and, when
available, the exact supporting text or database row.

## 5. Reproducible source adapters

There is no all-or-nothing loader. Each source has an independent adapter:

```text
discover -> fetch -> checksum -> archive -> normalize -> validate -> promote
```

Planned repository layout:

```text
pv/
  cli.py
  source/
    base.py
    manifest.py
    gcs.py
    rights.py
  ingest/
    clinicaltrials_gov.py
    pubmed.py
    pmc.py
    europe_pmc.py
    crossref.py
    openalex.py
    unpaywall.py
    hgnc.py
    uniprot.py
    chembl.py
    guide_to_pharmacology.py
    pubchem.py
    gwas_catalog.py
    open_targets.py
    hpo.py
    clingen.py
    gencc.py
    clinvar.py
    orphanet.py
    gnomad.py
    gtex.py
    impc.py
    mgi.py
    depmap.py
    reactome.py
    gene_ontology.py
    regulatory_fda.py
  normalize/
    trials.py
    assets.py
    targets.py
    mechanisms.py
    phenotypes.py
    publications.py
  discover/
    literature.py
    citations.py
    fulltext.py
  schemas/
    source.sql
    core.sql
    evidence.sql
```

This is the intended completed layout. The implemented subset currently consists
of `pv/ingest/clinicaltrials_gov.py`, `pv/ingest/pilot_asset_targets.py`,
`pv/ingest/target_phenotype_literature.py`,
`pv/ingest/europe_pmc_fulltext.py`, `pv/ingest/trial_semantic_llm.py`,
`pv/ingest/trial_relationships.py`, `pv/ingest/related_trial_resolver.py`,
`pv/ingest/semantic_verifier.py`, `pv/ingest/indication_normalizer.py`,
`pv/ingest/asset_preclinical_literature.py`,
`pv/ingest/asset_mention_literature.py`, `pv/ingest/pubmed_abstracts.py`,
`pv/ingest/development_scope.py`, `pv/audit/llm_decisions.py`,
`pv/audit/pilot_readiness.py`, and migrations 28--48. The remaining paths are
planned, not existing implementations.

Each adapter must:

- require an explicit release or create a timestamped immutable API snapshot;
- archive the provider-native payload before transformation;
- store retrieval URL, parameters, time, SHA-256, size, and parser version;
- be idempotent, resumable, and safe to retry;
- expose `--dry-run` and `--commit` modes;
- record rejected rows and validation failures;
- record source deletions or corrections as new versions/tombstones;
- avoid user-specific paths;
- never log credentials or signed GCS URLs; and
- never call paid APIs or models without explicit approval.

An unchanged rerun creates a new acquisition-run observation but reuses the same
content-addressed source version and normalized version rows. Changed upstream
content creates a new immutable version. It never overwrites the prior version.

Optional LLM enrichments follow the same rule. Each run stores its exact input,
raw output, validated canonical decision, and hashes. With
`--compare-decisions-to latest` or an explicit run ID, the runner reports added,
removed, changed, and unchanged decisions without updating the prior run.

Common CLI shape:

```bash
.venv/bin/dotenv run -- .venv/bin/python -m pv.cli fetch SOURCE \
  --release RELEASE --manifest-out MANIFEST.json

.venv/bin/dotenv run -- .venv/bin/python -m pv.cli load \
  MANIFEST.json --dry-run

.venv/bin/dotenv run -- .venv/bin/python -m pv.cli load \
  MANIFEST.json --commit
```

## 6. GCS and document retention

Use immutable, content-addressed objects:

```text
gs://pv-evidence-raw/{rights_tier}/{source}/{sha256[0:2]}/{sha256}.{ext}
```

Neon stores the bucket, object name, GCS generation, SHA-256, CRC32C, byte size,
media type, source URL, retrieval time, license/rights decision, and acquisition
run. Never store a signed URL.

Initial rights tiers:

- `open_redistributable`
- `open_noncommercial`
- `internal_licensed`
- `metadata_abstract_only`
- `embargoed`
- `quarantined`

Because the intended use is noncommercial research, noncommercial sources may be
eligible, subject to their actual terms. Each representation still requires a
rights decision; noncommercial intent does not make every online PDF archivable.

Retain licensed full text in an access-controlled GCS bucket. Prefer JATS/XML
when available, while retaining permitted PDFs and supplements as separate
representations of the same work.

## 7. Minimum `pv_source` tables

| Table | Contents |
|---|---|
| `source_system` | Provider, product, access method, attribution, and terms URL |
| `source_release` | Version/snapshot, provider date, retrieval date, and manifest hash |
| `acquisition_run` | Code commit, parameters, timing, status, counts, and errors |
| `source_record` | Stable native record identity such as NCT ID, PMID, or accession |
| `source_record_version` | Immutable provider payload/version and public-availability dates |
| `scholarly_work` | DOI/PMID/PMCID/preprint identity for one intellectual work |
| `representation` | Abstract, JSON, XML, JATS, PDF, supplement, table, figure, or parsed text |
| `object_blob` | GCS object identity, integrity metadata, and rights tier |
| `license` | License/terms snapshot and attribution requirements |
| `rights_assertion` | Decision permitting or prohibiting storage/use of one representation |
| `retrieval_query` | Query text, aliases, filters, cursors, and result counts |
| `retrieval_disposition` | Accepted, duplicate, irrelevant, inaccessible, failed, or excluded |

At minimum, a publication record stores title, abstract, DOI, PMID, PMCID,
online/print/indexing dates, authors, journal, article type, correction/retraction
relations, source version, retrieval time, and representations.

## 8. Trial collection procedure

### 8.1 Inventory query

Acquire ClinicalTrials.gov records whose `completionDateStruct.type` is
`ACTUAL` and whose Study Completion Date is between 2015-01-01 and 2025-12-31
inclusive. “Trials in year X” always means this field unless a caller explicitly
requests another date basis. Restrict the development cohort to
`StudyType=INTERVENTIONAL` and at least one intervention typed `DRUG` or
`BIOLOGICAL`. For the replacement pilot, select the first ten qualifying actual
completion dates in 2015 deterministically by completion-date lower bound, date
precision, and NCT ID. Store the complete ID/date/type discovery manifest, exact
API snapshot timestamp, query parameters, and selected subset.

The registry-type filter is intentionally strict. Sponsor-misclassified assets
under `OTHER` are not recovered in this cohort. Vaccines, antibiotics, and
non-human therapeutic targets can still enter the registry-filtered candidate
set and are removed or separated only after asset/target normalization.

ClinicalTrials.gov dates may have day, month, or year precision. Preserve the
literal partial date and precision. Store lower and upper bounds for ordering
and range operations, but never present a bound as a source-reported exact day.

Do not initially restrict by phase, sponsor, or completion status beyond the
actual completion-date requirement. Intervention type is the explicit cohort
filter above; later semantic scope rules handle vaccines, antibiotics, and
non-human targets.

### 8.2 Trial fields

Retain the complete source JSON plus normalized forms of:

- NCT ID and secondary identifiers;
- first submitted, first posted, last update submitted, and last update posted;
- study start, primary completion, completion, and results-posted dates;
- study type, phase, status, sponsor, collaborators, and responsible party;
- conditions and keywords;
- arms, interventions, descriptions, other names, and combinations;
- primary and secondary outcomes;
- eligibility, enrollment, locations, and documents;
- references, result publications, and linked registry documents.

### 8.3 Trial versions

Store the initial snapshot immediately and every future changed version. Retrieve
available historical versions separately where feasible. Do not pretend a
current record is the record as first registered.

## 9. Intervention and asset identity

Normalize each intervention in stages:

```text
literal trial intervention
  -> arm/regimen
  -> component
  -> formulation/salt/device carrier as applicable
  -> canonical active asset or unresolved mention
```

Retain literal and other names, development codes, INN/USAN, brands, active
moieties, salts, stereoisomers, formulations, PubChem CID/InChIKey, ChEMBL ID,
modality, route, biologic sequence or gene/transcript payload, ADC/radioligand
components, and combination components where available.

Unresolved interventions remain in the corpus and in a review queue. Do not map
them to targets by string guess alone.

### 9.1 Resolution is a hybrid pipeline

Asset resolution is not expected to be fully deterministic. Use four gates:

1. **Deterministic exact resolution.** Match registry other-names, RxNorm,
   ChEMBL, PubChem/UniChem, regulatory product/component records, and previously
   verified sponsor-code aliases by stable identifier or exact curated synonym.
2. **Deterministic decomposition.** Parse known regimen delimiters and dosage
   descriptions, but resolve each resulting token through curated identifiers;
   string splitting alone does not establish identity.
3. **Optional later model-assisted proposal.** For unresolved sponsor codes,
   acronyms, biologics, formulations, and implicit combinations, a later
   enrichment job may give a language model only the trial record, deterministic
   candidates, and retrieved source documents. Require strict JSON, exact source
   quotations, source IDs, and an `unresolved` option. The model proposes; it
   does not directly write canonical identity or block raw ingestion.
4. **Verification.** Check identifiers and component structure against
   authoritative sources. Auto-accept only deterministic or independently
   corroborated mappings; send ambiguity and conflicts to review.

Every accepted or rejected candidate is stored so that the resolver can be
replayed and audited.

The exact preprocessing, request packet, response schema, validation rules, and
NCT03525444 example are defined in
[`NAME_NORMALIZATION_AND_LLM_CONTRACT.md`](NAME_NORMALIZATION_AND_LLM_CONTRACT.md).

### 9.2 Real example: NCT03525444

ClinicalTrials.gov stores these intervention strings for NCT03525444:

- `vx-445/tez/iva`, described as a morning oral combination;
- `iva`, described as an evening oral treatment; and
- matching placebo.

The resolution should produce:

| Registry mention | Canonical result | Resolution evidence |
|---|---|---|
| `VX-445` | elexacaftor | Verified sponsor-code alias from registry/regulatory/curated compound sources |
| `TEZ` | tezacaftor | Verified abbreviation plus ChEMBL/PubChem/regulatory identity |
| `IVA` | ivacaftor | Verified abbreviation plus registry other-name/regulatory identity |
| `vx-445/tez/iva` | regimen containing elexacaftor + tezacaftor + ivacaftor | Component decomposition backed by the verified component aliases |
| evening `iva` | separate ivacaftor component/dose in the same regimen | Arm/intervention description |
| placebo | placebo comparator, not a therapeutic asset | Registry intervention type and description |

The components then receive separate target/action assertions. Regulatory
labeling identifies elexacaftor and tezacaftor as binding different CFTR sites
and improving processing/trafficking of selected mutant CFTR forms, while
ivacaftor potentiates CFTR channel opening. The regimen remains a regimen; it is
not collapsed into a fictitious fourth drug.

This example also shows why an LLM is useful for the long tail but insufficient
on its own. A model can recognize the abbreviations and composition, while the
acceptance gate verifies each identity and claim against sources.

## 10. Targets and mechanisms are separate concepts

Not every drug has one specific molecular target. The database therefore stores
two independent assertion types.

### 10.1 Molecular-target assertion

`asset_target_assertion` states that a source connects an asset/component to a
specific protein/gene product, isoform/variant, protein complex, target family,
nucleic acid/transcript, cell-surface antigen, or pathogen molecular target.

Required fields include target entity, target taxon, mechanism/action, role,
directness, source record/version, supporting text/row, and assertion date.

`directness` values are `direct`, `claimed_direct`, `indirect`, `disputed`, or
`unknown`.

### 10.2 Broader-mechanism assertion

`asset_mechanism_assertion` states that a source connects an asset/component to a
chemical action, biological process, pathway, physiological mechanism, cellular
effect, or unknown/uncertain therapeutic mechanism.

Mechanisms should use stable terms when possible—MeSH pharmacological actions,
ChEBI roles, Gene Ontology biological processes, Reactome pathways, or another
declared vocabulary—while retaining the literal source wording.

A broad mechanism is not relabeled as a protein target. A downstream pathway
effect does not establish direct binding to every component in that pathway.

### 10.3 Edaravone example

Edaravone illustrates the distinction:

- the asset identity is edaravone;
- regulatory and chemical sources describe free-radical scavenging/antioxidant
  action;
- oxidative-stress reduction can be stored as a broader mechanism/process claim;
- the FDA label states that the mechanism producing the therapeutic effect in
  ALS is unknown; and
- no single protein target should be manufactured to satisfy the schema.

Both “free-radical scavenger” and “therapeutic mechanism in ALS unknown” are
compatible sourced assertions at different levels.

## 11. Target/mechanism assignment procedure

For each normalized asset/component:

### Step 1: structured pharmacology lookup

Query regulatory labels and pharmacology reviews, ChEMBL mechanisms and target
mappings, IUPHAR/BPS Guide to Pharmacology interactions, PubChem compound
classifications/linked assays, UniProt/NCBI identifiers for named targets, and
existing `public.therapy_targets`/`preclin.drug_target` mappings as legacy
assertions.

Do not collapse results by source priority during ingestion. Store each assertion
and its provenance.

### Step 2: classify the assertion level

Classify each sourced claim as:

- `specific_molecular_target`
- `target_complex_or_family`
- `biological_pathway_or_process`
- `chemical_or_physiological_action`
- `unknown_mechanism`

This states what kind of claim the source makes; it is not an efficacy score.

### Step 3: extract action and role

Store the literal source verb and normalized action separately: binds, inhibits,
antagonizes, agonizes, degrades, stabilizes, replaces, silences, edits, scavenges,
chelates, reduces, or modulates.

Store role separately: therapeutic primary, secondary, off-target,
delivery/targeting antigen, payload target, biomarker, or unknown.

Action extraction is hybrid:

- Structured fields such as ChEMBL `action_type` are ingested directly and
  mapped through a versioned controlled-vocabulary table.
- Simple literal phrases are mapped with deterministic, boundary-aware rules;
  for example, `inhibitor of X` can propose action `inhibits` only when X is
  resolved in the same source span.
- Narrative labels, reviews, patents, and papers use model-assisted extraction
  into a strict schema containing subject, literal predicate, object, normalized
  candidate action, exact quotation/offsets, and source ID.
- Deterministic validation verifies that all returned entities and quotations
  exist in the supplied source. Unsupported or ambiguous actions remain
  `unknown` or enter review.

Always preserve the literal wording. Normalization makes actions searchable; it
does not replace what the source said.

### Step 4: retain ambiguity

- Multi-target assets keep multiple assertions.
- Combination components are resolved separately.
- Family/complex claims stay at family/complex level until a source supports a
  subunit.
- Sponsor/patent claims are `claimed_direct` unless independently verified.
- Indirect pathway effects never become direct molecular targets.
- If sources disagree, retain the disagreement.
- If no specific target is supported, keep the broader mechanism or unknown state.

### Step 5: review queue

Create deterministic review candidates for unresolved names, conflicting target
claims, broad-vs-specific mismatches, and asset/component ambiguity. The initial
system may use structured rules and human review. Scientific language models are
not required to begin raw ingestion.

## 12. Sources linking specific targets to phenotypes

### 12.1 Name and identifier normalization

Search uses versioned identifier/alias tables, not destructive text cleanup:

- human genes: HGNC ID with approved, previous, and alias symbols;
- proteins and isoforms: UniProt accession linked to HGNC/Ensembl/NCBI Gene;
- drugs/assets: ChEMBL, PubChem/UniChem, RxNorm where applicable, regulatory
  product/component identities, sponsor codes, and verified synonyms;
- diseases/traits: MONDO, EFO, MeSH, Orphanet, and retained native source terms;
- phenotypes: HPO for human, MP for mouse, plus native source identifiers;
- mechanisms/processes: ChEMBL action types, MeSH pharmacological actions,
  ChEBI roles, Gene Ontology, and Reactome.

Each normalized entity has a stable internal UUID, but search bundles are built
from aliases valid in the selected source release. ChEMBL synonym types are
preserved: INN/regional names, regulatory names, trade names, and genuine
research codes may enter the search projection, while generic `OTHER` strings
and class labels such as `ATC CODE ... GONADOTROPINS` remain in the ledger but
do not become automatic queries. OLS exact synonyms may enter indication
queries; related synonyms remain review-only. Aliases that collide across two
entities of the same type are excluded from automatic retrieval.

For ChEMBL protein-family and protein-complex targets, component membership is
also provenance rather than an alias expansion. A family assertion does not
become one assertion for every component gene. For example, ChEMBL mechanism
1108 identifies vincristine's target as `CHEMBL2095182` (`Tubulin`) and says it
binds beta tubulin at the vinca site. That supports a Tubulin-family target plus
a beta-tubulin/vinca-site binding context, not a specific `TUBB*` gene.

The prior loader did something weaker: `norm()` lowercased and removed all
non-alphanumeric characters, ChEMBL rows supplied some drug mappings, exact
uppercased gene symbols were matched to `public.targets`, and Haiku/Sonnet JSONL
files filled unresolved drug-target mappings. That approach loses punctuation
and component structure and does not create a release-scoped alias graph. PV
keeps the useful ChEMBL and reviewed LLM evidence but replaces normalized strings
as identity keys.

| Evidence area | Initial sources | Required boundary |
|---|---|---|
| Mendelian disease | Orphanet, ClinGen, GenCC, appropriately licensed OMIM | Preserve disease, inheritance, allele class, classification, date, and citations |
| Clinical variants | ClinVar | Preserve submitter-level assertions and conflicts |
| Common-variant genetics | GWAS Catalog | Preserve study, variant, trait, effect/statistics, ancestry and dates; mapped gene is not automatically causal |
| Integrated evidence | Open Targets | Preserve row-level datasource and originating evidence; do not count the aggregator independently |
| Human phenotypes | HPO annotations | Preserve disease mediation, negation, frequency, onset, and release |
| Model phenotypes | IMPC, MGI | Preserve allele, genotype, background, sex, procedure, endpoint, null/normal result, and release |
| Expression/context | GTEx, HPA, eQTL Catalogue | Expression/regulation is context, not phenotype causality |
| Constraint/safety | gnomAD | Constraint is not proof of unsafe pharmacologic inhibition |
| Cellular phenotypes | DepMap/CCLE, Cell Model Passports | Preserve line, genotype, assay, batch, and lineage-specific dependency |
| Mechanism/pathway | Reactome, Gene Ontology, STRING | Membership/interaction is not itself a disease phenotype |
| Literature | PubMed/PMC/Europe PMC corpus | Link exact source and preserve study/model context |

Existing GWAS and Open Targets tables remain. Import them as legacy snapshots
with known provenance, then reconcile them against pinned official releases.
Unknown legacy releases are labeled `legacy_release_unknown`, not deleted or
silently treated as new official releases.

The implemented compatibility layer is deliberately non-destructive:

- `pv_source.legacy_table_snapshot` freezes row-count/schema/statistical
  fingerprints and refuses silent drift from the first observed legacy state;
- `pv_core.legacy_target_bridge` and `legacy_phenotype_bridge` hold explicit,
  idempotent resolutions rather than using normalized strings as identity;
- `pv_evidence.v_structured_target_phenotype_evidence` provides one interface
  over HPO, GWAS Catalog, Open Targets and its retained originating-source
  label, ClinGen, and Mendelian associations;
- every row preserves `source_relation`, `source_row_key`, locator JSON, and
  native evidence detail; and
- `pv_evidence.v_structured_target_context_evidence` keeps constraint,
  expression, pathway, dependency, and aggregate IMPC context separate from
  direct target--phenotype assertions.

This completes integration of the databases already present in PostgreSQL. It
does not pretend their unknown legacy releases are official pinned releases,
and it does not turn aggregate IMPC category/count rows into raw mouse
procedure-level phenotypes. Official-release adapters reconcile into this
layer later without replacing the legacy rows.

## 13. Sources linking broader mechanisms to phenotypes

Broad mechanisms such as oxidative stress can be associated with thousands of
diseases and papers. Do not attach an entire process-wide literature universe to
every drug with that mechanism.

Use three scoped relationships:

1. `asset_mechanism_assertion`: a source states the asset has the action.
2. `mechanism_phenotype_assertion`: a source connects the mechanism/process to a
   phenotype or disease in a stated context.
3. `asset_mechanism_phenotype_assertion`: a study tests the asset, mechanism
   readout, and phenotype together.

Mechanism-to-phenotype discovery requires at least one scope constraint: trial
indication, an asset-associated phenotype, studied model/tissue/cell type, asset
name/intervention class, or a direct curated database assertion.

For edaravone, search asset aliases + ALS + oxidative-stress,
free-radical-scavenging, or lipid-peroxidation terms. Do not import every
oxidative-stress paper and imply it concerns edaravone or ALS.

Run the mechanism-indication search separately from the asset search:

1. **Asset-mechanism:** `edaravone aliases` + `free-radical scavenging/oxidative
   stress terms` establishes what sources claim the asset does.
2. **Mechanism-indication:** `oxidative stress/free-radical/lipid-peroxidation
   terms` + `ALS aliases` establishes evidence connecting the mechanism to the
   indication, without requiring edaravone to appear.
3. **Asset-indication-mechanism:** `edaravone aliases` + `ALS aliases` +
   `mechanism terms` finds studies that test all three together.

These produce different assertion types and must not be collapsed.

## 14. Literature discovery procedure

### 14.1 Versioned discovery bundles

**Asset bundle:** generic, brand, sponsor-code, chemical/biologic, active-moiety,
component/formulation names, trial IDs, sponsor protocol identifiers, and trial
condition/indication terms.

**Specific-target bundle:** HGNC symbol, previous symbols, aliases, protein names,
HGNC/NCBI Gene/Ensembl/UniProt identifiers, isoform/complex/family terms, and
structured target-associated diseases/phenotypes.

**Broader-mechanism bundle:** literal source phrases, normalized
MeSH/ChEBI/GO/Reactome terms and synonyms, trial indication, phenotype/model/
tissue terms, and asset name where needed to constrain expansion.

**Assay/model bundle:** organoid, spheroid, iPSC, patient-derived, primary cell,
explant, PDX, target engagement, occupancy, binding, rescue, challenge model,
theratyping, responder, validation cohort, matched in vitro/in vivo, and relevant
analyte/endpoint/genotype/model terms.

### 14.2 Query sequence

1. Search exact trial IDs and asset names.
2. Search asset + indication/phenotype.
3. Search verified specific target + phenotype/model/assay terms.
4. Search broader mechanism only with indication, phenotype, model, or asset
   constraints.
5. Follow references from reviews and pivotal studies.
6. Follow forward citations and related works.
7. Search registry references and regulatory-review bibliographies.
8. Store every query, result identifier, and disposition.

Use PubMed/MEDLINE, Europe PMC, Crossref, OpenAlex, and Unpaywall. PubTator and
Europe PMC annotations may suggest entities but are not independent evidence.

Europe PMC is the first implemented literature adapter because one API supplies
PubMed-indexed metadata and abstracts, PMCID/DOI identity, citation metadata,
open-access indicators, and permitted JATS full text for the Europe PMC open
access subset. This reduces identity joins during the pilot. It is not intended
to be the only discovery source: relying on it alone omits source-specific
records and cannot substitute for the planned PubMed, Crossref, OpenAlex,
Unpaywall, regulatory-bibliography, and citation-expansion adapters.

Query construction and retrieval are programmatic and reproducible. The
identifier/alias tables feed versioned templates; API calls, cursors, results,
and exclusions are stored. Citation expansion is also programmatic.

LLM-based candidate-document classification, query expansion, and experimental
result extraction are deferred until after the raw corpus and deterministic
query manifests exist. Initial literature acquisition does not depend on an LLM.

The system claims a reproducible high-recall corpus over declared sources and
queries—not “all literature.” Measure coverage with known-item recall, blinded
sentinel recall, alias false-positive review, and citation-expansion saturation.

For the earlier first-posted-2025 pilot, Europe PMC ran separate target-wide and
indication-specific queries for ADRB2--asthma, HTR2A--impulse-control disorder,
DNMT1--AML, and DNMT3A--AML. It also runs separate asset-preclinical-wide and
asset-indication-preclinical queries for salbutamol, pimavanserin, and
azacitidine. Search hits are candidate documents only; ingestion does not
convert co-mention into a target-phenotype assertion or a passed experiment.

The active policy is `pv_literature_v2`. It runs exactly two provider-query
families:

1. verified asset aliases AND aliases for one normalized trial indication; and
2. a verified effective target without indication or preclinical vocabulary.

Target--indication documents are the local lexical projection
`pv_evidence.v_target_indication_literature_candidate` over the completed
target-only corpus. This projection searches titles and abstracts using the
normalized phenotype label and safe ontology synonyms; it makes no additional
Europe PMC request and remains a candidate relation rather than evidence.

Provider retrieval is uncapped in production and page-streamed. Before the
next page is requested, the exact byte-hashed `resultType=core` page is archived
and committed. Canonical source/work/candidate projection commits in 200-record
batches. `retrieval_query` stores page count, projected-result count, next
cursor, status, and an ordered page-hash manifest. Exact result identities can
be reconstructed from the immutable pages and `retrieval_disposition` rows.
A positive debug limit always produces `stream_status='truncated'`; active
views require both a completed stream and a completed acquisition run.
They select only the latest completed execution of each stable query key, so an
exact rerun updates provenance without multiplying analytical rows.

The 17 historical `asset_mentions_v1` work items and older preclinical-word-list
queries remain immutable audit data. They are not inputs to the active policy.
An offline promote-from-archived-page command remains to be implemented for
strict replay without a live query.

The CFTR organoid sentinel demonstrates why both active query families are
needed. `NCT02934698` was ingested by explicit NCT ID and deterministically
normalized to ivacaftor, CFTR, and `MONDO:0009061` cystic fibrosis without an
LLM. The complete ivacaftor + cystic-fibrosis query returned 2,268 records but
did not include PMID `36529661`, because the paper's title/abstract do not name
ivacaftor. The complete CFTR-only query returned 15,880 records and captured the
paper at provider rank 4,575; the local phenotype projection then matched
`cystic fibrosis`. The exact queries, identifiers, rights state, and replay
checks are recorded in
`data/pv/cftr_sentinel/ORGANOID_SENTINEL_TRACE.md`.

A read-only cutoff audit on 2026-09-18 tested Europe PMC's default relevance
top 100 for five completed-corpus assets. It is not an acceptable standalone
retention rule for broad assets. All of the first 100 results for rituximab and
nicotine were published in 2026, while clearly material older mechanistic and
in-vivo papers were absent even from the relevance-ranked first 1,000. Citation
ranking recovered some, but not all, of those examples: the rituximab/anti-CD47
study was citation rank 36, while other in-vitro rituximab studies were ranks
189, 199, and 342; an in-vivo nicotine dose-selection paper was rank 63, while
a rat nicotine-seeking study was rank 386. Follitropin beta had only 92 total
matches, so a top-100 cap lost nothing in that boundary case. The executable
audit is `pv/audit/top100_asset_relevance.py`; its complete result is
`data/pv/2015_pilot/TOP100_RELEVANCE_AUDIT.md`. No rows were deleted or
reclassified by the audit.

A second read-only audit on 2026-09-18 tested the replacement search
policy on the five included 2015 trials: (1) asset plus normalized trial
indication and (2) verified target alone. Target--indication is a local
projection of the target-only corpus, not a third provider query. Thirteen
asset--indication queries produced 28,516 summed provider hits (median 57;
range 1--12,378), and fourteen target-only queries produced 72,709 (median
607; range 0--39,193). Tubulin and NR3C1 contributed 58,142 target hits,
about 80% of the target-only total. The reduction from 40,606 to 39,193 for
Tubulin is intentional: the old audit incorrectly ORed 30 component labels
(gene symbol and protein name for 15 components) into the family query. These
are query-hit sums rather than
deduplicated works. The low fertility counts remain even after archived
ChEMBL and OLS synonyms are projected, so they are a genuine consequence of the
strict asset--indication title/abstract query rather than a missing-alias bug.
The executable count audit and output are
`pv/audit/literature_search_policy_pilot.py` and
`data/pv/2015_pilot/LITERATURE_SEARCH_POLICY_HIT_COUNTS.md`. That artifact is a
pre-activation count audit, not the active work plan. Migration 51 subsequently
made source-grounded target context operational: vincristine now searches
`TITLE_ABS:"beta tubulin"` (5,065 current hits), while the broad ChEMBL parent
`Tubulin` and `vinca site` remain query provenance rather than OR terms. The
current normalized pilot plan contains 15 asset--indication and 9 distinct
effective-target queries.

The rights-aware full-text pilot retains seven permitted JATS representations.
Unsupported or unavailable licenses become acquisition-run failures rather than
aborting the batch. No GCS bucket is configured, so the exact XML remains in
immutable Neon source versions and `pv_source.object_blob` is empty. When a
bucket is supplied, the same adapter uploads licensed JATS and attempts the
provider-advertised free PDF; PDF bytes are stored only in GCS and are linked by
checksum, generation, source URL, and rights assertion.

### 14.3 Why a document is linked

`document_entity_link` records one of:

- `registry_reference`
- `mentions_asset`
- `supports_asset_identity`
- `supports_target_assertion`
- `supports_mechanism_assertion`
- `supports_target_phenotype`
- `supports_mechanism_phenotype`
- `reports_preclinical_study`
- `reports_clinical_outcome`
- `review_discovery_source`
- `citation_expansion`

A discovery link is not automatically a scientific evidence assertion.

### 14.4 Concrete unresolved pilot cases

The initial target-search stage can proceed only after the asset or mechanism
subject has a source-backed identity. The following are not generic warnings;
they are the specific missing records or decisions in the current first-ten
pilot:

| Trial case | What ClinicalTrials.gov currently supplies | What is concretely missing before literature expansion |
|---|---|---|
| Azacitidine (`NCT06754540`) | A registered intervention named `Azacitidine (AZA)` in an AML relapse-prevention trial | No azacitidine asset row, PubChem/ChEMBL/regulatory identity record, or asset-mechanism assertion has been promoted into PV. An authoritative mechanism source must first support the broad DNA/RNA methyltransferase or hypomethylation claim. A DNMT1-specific target search is permitted only if an ingested source explicitly supports DNMT1 rather than inferring it from the broad mechanism. The subsequent discovery must keep asset--mechanism, mechanism--AML, and asset--mechanism--AML searches separate. |
| Pimavanserin (`NCT06754553`) | The title names pimavanserin and calls it a selective 5-HT2A inverse agonist, but the registered intervention list contains assessments and monitoring rather than pimavanserin | A title-level asset mention policy and link are required so the database does not misrepresent pimavanserin as a registered administered intervention. The asset still needs a stable chemical identity, an ingested pharmacology source, normalized HTR2A and any genuinely supported secondary targets, and explicit primary/secondary roles. Only then should target-wide and Parkinson disease/impulse-control-disorder searches run, retaining the title-only trial provenance. |
| SCTV02 (`NCT06754605`) | A sponsor code for a recombinant RSV vaccine plus placebo | No authoritative construct/composition record has been ingested: antigen identity, sequence or construct, RSV strain/subtype, adjuvant/carrier, and component structure are unresolved. A sponsor protocol, regulatory record, trial document, or publication must establish these facts. The resolved subject may be a pathogen antigen and vaccine mechanism rather than a human protein target; it needs an appropriate taxon/protein identifier before antigen/mechanism literature expansion. |
| Device, procedure, behavioral, exercise, education, and placebo mentions | Literal registered interventions or assessments | These remain valuable trial records but ordinarily receive `not_applicable` for molecular-target resolution unless a source establishes a molecular asset. They must not be forced through the drug-target pipeline. |

None of the first three rows is currently represented as a completed normalized
asset/mechanism/target chain in PV. Earlier discussion of their likely identity
or pharmacology was planning, not ingestion.

## 15. Asset-level preclinical test inventory

Collect every discoverable preclinical test for each asset/component—not only
tests reported as passed. Restricting collection to successes would create
severe survivorship and publication bias.

The inventory covers:

- biochemical binding, potency, kinetics, and selectivity;
- cellular target engagement and proximal functional assays;
- immortalized, primary-human, patient-derived, iPSC, organoid, explant, and
  other functional disease models;
- genetic or pharmacological perturbation/rescue experiments;
- rodent and non-rodent efficacy models;
- PK, exposure, tissue distribution, PK/PD, and dose-response studies;
- off-target panels, safety pharmacology, toxicology, genotoxicity,
  reproductive/developmental toxicology, immunogenicity, and tolerability; and
- negative, failed, mixed, inconclusive, and unpublished-but-regulator-disclosed
  tests available in declared sources.

For every test retain:

- asset and exact component/formulation tested;
- target or broader mechanism under test;
- indication/phenotype and experiment purpose;
- model species, strain/line, genotype, donor, tissue/cell type, sex/age, and
  induction/background;
- assay/protocol, analyte/readout, units, controls, dose/exposure, duration, and
  timepoint;
- sample size, value/effect, variability/interval, statistic, and p/q-value when
  reported;
- source-defined success criterion or threshold;
- observed result and normalized result status;
- whether the test was replicated and by whom; and
- exact source passage/table/figure and public-availability date.

`result_status` values are:

- `meets_reported_criterion`
- `does_not_meet_reported_criterion`
- `mixed`
- `null_no_effect`
- `inconclusive`
- `criterion_not_reported`
- `result_not_reported`

`meets_reported_criterion` means the source itself defines a threshold or
acceptance criterion and the reported measurement satisfies it. For example, if
a source declares a chloride-transport response of at least 10% of normal to be
responsive, a reported value above that threshold meets the source criterion.
It does not mean the assay predicted clinical success.

No pass/fail state is inferred merely because a development program advanced.
When a source supplies no threshold, use `criterion_not_reported` and retain the
raw measurement. A separately defined analytical rule may be applied later, but
must not rewrite the ingestion status.

No public corpus can guarantee every test a sponsor ever conducted. The claim is
“every test found in the declared structured, regulatory, and literature sources,”
with source coverage and unavailable documents reported.

## 16. Minimum `pv_core` tables

| Table | Purpose |
|---|---|
| `entity` | Stable internal UUID and entity type |
| `identifier_namespace` | NCT, HGNC, UniProt, ChEMBL, PubChem, MONDO, HPO, PMID, DOI, etc. |
| `entity_identifier` | Stable/native identifiers and preferred status |
| `entity_name_assertion` | Current, previous, brand, development-code, synonym, and literal names |
| `trial` | Canonical trial identity |
| `trial_record_link` | ClinicalTrials.gov record/version to trial |
| `trial_intervention_mention` | Literal intervention in arm/regimen context |
| `asset` | Canonical active asset or unresolved placeholder |
| `asset_component` | Combination, ADC, radioligand, gene/cell payload components |
| `intervention_asset_assertion` | Sourced mention-to-asset resolution |
| `molecular_target` | Protein/gene/isoform/complex/family/nucleic-acid/pathogen target |
| `mechanism_concept` | Chemical action, process, pathway, or physiological mechanism |
| `phenotype_condition` | Disease, trait, phenotype, safety finding, or endpoint |
| `ontology_release` | Release-scoped vocabulary identity |
| `ontology_term_version` | Label, synonyms, obsolete/replacement state by release |
| `document_entity_link` | Auditable reason a document is linked to an entity/relation |
| `preclinical_test` | Stable test identity and source-defined purpose |
| `experimental_model` | Cell, tissue, organoid, animal, genotype, donor, and repository identity |
| `assay_definition` | Method, readout, analyte, units, controls, and protocol identity |
| `development_scope_policy` | Immutable policy definition controlling downstream expansion, not raw retention |
| `literature_retrieval_policy` | Immutable provider-query and local-projection policy; exactly one version is active |
| `asset_development_scope` | Current asset decision per policy version |
| `trial_development_scope` | Current trial decision per policy version |
| `asset_development_scope_history` | Append-only distinct asset decisions and hashes |
| `trial_development_scope_history` | Append-only distinct trial decisions and hashes |

## 17. Minimum `pv_evidence` tables

| Table | Purpose |
|---|---|
| `asset_target_assertion` | Sourced asset/component-to-molecular-target relationship |
| `asset_mechanism_assertion` | Sourced asset/component-to-broader-mechanism relationship |
| `target_phenotype_assertion` | Sourced target-to-phenotype/disease relationship |
| `mechanism_phenotype_assertion` | Sourced mechanism/process-to-phenotype relationship |
| `asset_mechanism_phenotype_assertion` | Study-level asset + mechanism readout + phenotype relationship |
| `assertion_source` | Exact source record/version, native row, passage, table, or figure |
| `assertion_context` | Species, tissue, cell type, variant, perturbation, dose, and model context |
| `assertion_relation` | Contradicts, replicates, refines, supersedes, or different-context |
| `review_queue` | Unresolved identity, ambiguity, conflict, or source-boundary issue |
| `preclinical_test_execution` | Asset/component, model, assay, dose, controls, timing, and source |
| `preclinical_measurement` | Raw endpoint value, unit, estimate, uncertainty, and statistic |
| `preclinical_result` | Source criterion, normalized result status, replication, and interpretation |

All assertions retain literal source wording plus normalized subject, predicate,
object, directness, and context. No scoring is required during ingestion.

## 18. Existing data migration

Do not discard existing databases. For each current source:

1. inventory table, row count, native identifiers, known release, and provenance;
2. register it as a legacy source snapshot;
3. retain current raw/native rows unchanged;
4. acquire a pinned official release where feasible;
5. reconcile additions, removals, corrections, and duplicates;
6. create old-to-new entity bridges;
7. retain the legacy row even when superseded; and
8. mark missing release information explicitly.

Current `source_document` rows are reusable cached representations and discovery
seeds. Resolve them into canonical works, verify metadata against pinned
PubMed/PMC records, reuse valid bytes by checksum, and independently run the new
discovery procedure to fill coverage gaps.

Current aggregate evidence scores remain legacy derived records. They are not
substitutes for their source documents or database rows.

## 19. Reproducibility

Each collection snapshot is a manifest of source releases and archived objects,
not a database dump or analytical dataset.

```yaml
collection_snapshot: pv-collection-2026-09-16
intended_use: noncommercial_research
trial_scope:
  registry: clinicaltrials_gov
  completion_date_type: ACTUAL
  completion_from: 2015-01-01
  completion_through: 2025-12-31
  study_type: INTERVENTIONAL
  intervention_types_any: [DRUG, BIOLOGICAL]
sources:
  clinicaltrials_gov: snapshot-2026-09-16T00:00:00Z
  gwas_catalog: r2026-08-03
  hpo: 2026-06-23
code_commit: GIT_SHA
```

Starting from an empty database and authorized GCS access, replaying the snapshot
must reproduce the same raw hashes, normalized identity links, assertions, and
query-result memberships without calling live source APIs.

Schema migrations perform DDL only. Source adapters and collection snapshots
carry data provenance independently.

## 20. Initial quality gates

### Source integrity

- Every record resolves to a source, release/snapshot, run, native ID, and hash.
- Retries create no duplicate record versions or assertions.
- Corrections and deletions remain historical.
- Every GCS object has a verified rights decision.
- A snapshot can be replayed without network access.

### Orchestration and resume validation

Migration 44 stores each target--phenotype or asset-preclinical unit under a
SHA-256 work key. Planning the five-trial pilot twice must add zero items on the
second call. A worker obtains a committed lease before network retrieval and
records a separate attempt. `recover-stale` marks the interrupted attempt and
returns only the work item to `pending`; already archived source versions and
canonical candidates remain protected by their content/identity unique keys.

The pilot validation consists of four explicit checks:

1. plan twice and require zero second-pass inserts;
2. simulate one two-hour-old lease, recover it, and require
   `attempt=interrupted` plus `item=pending`;
3. interrupt/replay a real retrieval and require unchanged canonical candidate
   uniqueness; and
4. audit for zero duplicate work keys, zero duplicate canonical candidate
   identities, and zero stale running leases.

### Intervention identity

- Combination components are not collapsed.
- Unresolved assets remain visible.
- Salts/formulations link to active moieties without losing literal identity.
- Target, biomarker, antigen, payload target, and mechanism roles stay distinct.

### Target/mechanism integrity

- No asset is forced to have a protein target.
- Broad processes never become direct targets.
- Every claim retains source wording and provenance.
- Conflicting and unknown claims remain queryable.
- Edaravone is represented without a manufactured single-protein target.

### Literature coverage

- Store every query, result identifier, and disposition.
- Recover the cystic-fibrosis patient-derived-model review and primary citation
  chain in the sentinel set.
- Recover a declared edaravone mechanism/ALS sentinel set.
- Report blinded known-item recall before declaring target-wide coverage.
- Inaccessible full text remains `metadata_abstract_only`, not negative evidence.

### Preclinical test inventory

- Every asset has a search/coverage record even when no tests are found.
- Positive and negative/null tests use the same ingestion path.
- Every result status traces to a raw measurement and reported criterion or is explicitly
  `criterion_not_reported`.
- Regulator-disclosed nonclinical tests are linked even when no journal article
  exists.
- Tests are deduplicated by experiment, not merely by repeated publication.

## 21. Implementation order

1. Create `pv_source` and GCS object/manifest support.
2. Implement the ClinicalTrials.gov actual-completion-date 2015-2025 adapter.
3. Run the separate, explicitly approved trial-semantic LLM pass over immutable
   trial versions to propose assets/components, compositional indications, and
   target or broader-mechanism candidates.
4. Normalize the proposals through deterministic authority lookup and retain an
   unresolved/review queue. Never invoke a model during raw source acquisition.
5. Verify asset-target and asset-mechanism proposals against FDA, ChEMBL, Guide to
   Pharmacology, PubChem, and legacy mappings.
6. Implement HGNC/UniProt/RxNorm and mechanism vocabulary identity.
7. Migrate and reconcile existing GWAS and Open Targets data. **Implemented for
   current legacy tables; official pinned-release reconciliation remains.**
8. Add HPO, ClinGen, GenCC, ClinVar, Orphanet, gnomAD, IMPC/MGI, DepMap, GTEx,
   Reactome, and Gene Ontology independently.
9. Implement PubMed/PMC/Europe PMC/Crossref/OpenAlex/Unpaywall discovery and
   rights-aware full-text retention.
10. Ingest structured preclinical assay/test records and link all candidate
    preclinical documents to assets. Narrative experiment extraction is a later
    stage over this frozen raw corpus.
11. Run target-specific and separate scoped mechanism-specific literature
    discovery.
12. Validate replay, identity, source-link, preclinical-test, and sentinel gates.

## 22. Explicitly deferred decisions

The following are not required to gather the raw evidence:

- predictive feature definitions;
- clinical success/failure labels;
- target-selection model design;
- training/test splits and validation methodology;
- evidence tier scores;
- one “best” target or mechanism per asset;
- one “best” phenotype assertion;
- report row limits or rendering rules; and
- LLM-based unresolved-name proposals, narrative target/mechanism extraction,
  literature relevance classification, query expansion, and narrative
  experiment-result extraction; and
- whether current-evidence and historical analyses use separate datasets.

Current and historical analyses can query the same evidence ledger with different
source-version and availability-date filters. Separate raw collections are not
required.
