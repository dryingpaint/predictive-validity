# PV Name Normalization and LLM Exchange Contract

**Status:** Implemented pilot contract
**Scope:** Entity identity, aliases, combination decomposition, and sourced
target/mechanism assertions
**Last updated:** 2026-09-16

## 1. One rule governs the whole flow

Source text is never overwritten by a normalized name. Normalization creates a
versioned assertion that a literal source mention refers to a canonical entity.
The source mention, the candidate set, the decision, and the evidence used for
the decision all remain queryable.

Raw ingestion never waits for an LLM. After the immutable trial snapshot exists,
the current pipeline runs a trial-wide LLM semantic pass first: the model
proposes assets/components, indication structure, and target or broader-
mechanism relationships. Deterministic authority lookup then normalizes those
proposals, verifies the proposed relationships, retrieves authoritative aliases,
and leaves unsupported proposals provisional. The LLM never writes canonical
entities or evidence assertions directly.

This ordering separates jobs according to their strengths: the model interprets
relations and study context; deterministic adapters assign stable identifiers,
deduplicate records, and establish source provenance.

## 2. Entities and identifiers

Each canonical entity receives an internal UUID, but an internal UUID alone is
not evidence of identity. It must be associated with one or more release-scoped
external identifiers or a documented provisional identity.

| Entity | Preferred authority | Useful cross-references |
|---|---|---|
| Small molecule or active moiety | ChEMBL or PubChem | InChIKey, UniChem, RxNorm ingredient, UNII |
| Regulated product/formulation | Regulator product/application ID or RxNorm clinical drug | active ingredients, strength, dose form, route |
| Biologic | ChEMBL molecule, UniProt, or regulator identity as applicable | sequence hash, INN/USAN, sponsor code |
| Gene | HGNC ID | NCBI Gene, Ensembl |
| Protein/isoform | UniProt accession | HGNC, Ensembl protein/transcript |
| Complex/family | declared source vocabulary | member entities and source-native ID |
| Disease/trait | MONDO or EFO where an exact mapping exists | MeSH, Orphanet, HPO disease, source-native term |
| Phenotypic feature | HPO for human; MP for mouse | source-native term |
| Biological process/pathway | GO biological process or Reactome | MeSH or source-native phrase |

An alias row is not global free text. It contains:

```text
entity_id
entity_type
alias_text
alias_normalized
alias_kind              # preferred, synonym, prior_name, brand, sponsor_code,
                        # abbreviation, salt, formulation, misspelling, etc.
language
taxon_id                 # where relevant
source_system
source_release_id
source_record_version_id
valid_from / valid_to    # when supplied by the source
is_ambiguous
```

The same alias may point to more than one candidate. For example, a short gene
symbol or trial abbreviation is never globally unique.

## 3. Exact normalization flow

### Gate 0: archive and address the source

Archive the provider-native payload first. Give each name occurrence a stable
`mention_id` derived from the source record version and its JSON/XML/table
location. For a trial intervention, retain at least:

- NCT ID and source record version;
- intervention and arm indexes;
- literal name, description, other names, and intervention type;
- arm labels, dose, route, schedule, sponsor, conditions, and protocol IDs; and
- exact character spans when a mention comes from prose.

### Gate 1: comparison form, not identity

Create a comparison form using a versioned normalizer:

1. validate UTF-8 and apply Unicode NFKC;
2. trim outer whitespace and collapse internal whitespace;
3. normalize typographic quotes/dashes only in the comparison form;
4. Unicode-casefold for comparison;
5. retain punctuation that may encode composition, especially `/`, `+`, `-`,
   parentheses, Greek letters, and allele notation; and
6. parse dose, unit, route, and formulation into separate candidate fields
   without deleting them from the literal value.

The output is a search key, never a canonical identifier. Unlike the old
`norm()` function, it does not delete all non-alphanumeric characters and then
treat the result as identity.

### Gate 2: trial-wide LLM semantic proposal

Once the raw ClinicalTrials.gov version is archived, provide the model with the
title, summaries, design, conditions, interventions, arms, outcomes,
eligibility, and derived condition terms as source-path-addressable strings.
The strict response proposes:

- actual interventions, historical exposures, comparators, and components;
- treated/prevented/diagnosed indications separated from background disease and
  population context;
- compositional indication concepts and modifiers; and
- specific molecular targets, target families, broader processes/actions, or
  an explicit unknown mechanism.

Each field is labelled `explicit_trial`, `inferred_from_trial_context`, or
`model_prior`. Trial-grounded claims require exact source-path/quote pairs.
Model-prior pharmacology is a search and verification candidate, never evidence.

The implemented runner is `pv.ingest.trial_semantic_llm`. It stores exact input
packets, raw and parsed outputs, canonical decision hashes, provider request
IDs, usage, model parameters, source-version links, and rerun comparisons.

### Gate 3: deterministic exact matching and relationship verification

Look up the literal and comparison forms in release-scoped alias tables. A match
can be accepted automatically only when:

- the alias is unique in the relevant entity type and context;
- the external identifier exists in the pinned authority release; and
- type, species, modality, and source context do not conflict.

Context includes registry `otherNames`, sponsor, condition, intervention type,
route, neighboring component names, and source-provided identifiers. Exact
matching is performed against RxNorm, ChEMBL, PubChem/UniChem, regulatory
ingredients/products, HGNC, UniProt, and verified sponsor-code aliases as
appropriate.

### Gate 4: deterministic regimen and component decomposition

Detect possible delimiters and compositional phrases, but do not accept a split
as identity. Each token must independently pass Gate 3 or a later verification
gate. Preserve all three levels:

```text
trial mention -> regimen -> component -> active asset
```

Placebo, vehicle, sham, background therapy, device carrier, conjugate payload,
targeting moiety, salt, and formulation are typed relationships rather than
being flattened into drug names.

### Gate 5: deterministic candidate generation

For unresolved mentions, retrieve candidates by:

- source-native `otherNames` and protocol identifiers;
- exact and bounded-prefix sponsor-code lookup;
- structured product-to-ingredient relations;
- InChIKey, sequence, registry, and cross-reference joins;
- token-level combination lookup; and
- cautious fuzzy search within the correct entity type.

Fuzzy similarity only ranks candidates. It can never promote a mapping.
Candidate retrieval stores the query, authority release, returned IDs, ranks,
and scores.

### Gate 6: unresolved queue

If one identity is not established, store `unresolved` or `ambiguous` and the
candidate set. Raw trial retention and additional identity-source retrieval can
still proceed. Target/phenotype and asset/preclinical literature expansion must
wait until development scope is resolved. This is the end of the required raw
ingestion path.

### Gate 7: optional LLM conflict adjudication

When deterministic lookup returns multiple plausible identities or conflicting
relationship records, a second model pass may receive the original semantic
proposal, the bounded candidate set, and retrieved authoritative snippets. It
must be allowed to answer `unresolved` or `ambiguous`. It proposes a resolution;
it cannot create or update a canonical entity directly.

An implemented post-verification variant is
`pv.ingest.chembl_mechanism_context_llm`. It runs only after exact asset
resolution and complete ChEMBL mechanism enumeration. The model receives the
archived mechanism/target fields and component candidates, then may structure
explicit subfamily, binding-site, domain, subunit, isoform, or mutation-state
phrases. Mechanical validation requires an exact source path and quote, requires
the normalized context to occur in that quote, and forbids a component list from
becoming gene-target evidence. The immutable output is stored as an LLM decision;
exact-source contexts are projected separately and the latest validated decision
per asset is exposed without duplicating historical reruns.

### Gate 8: mechanical validation and promotion

Reject an LLM response before scientific review if:

- it fails the JSON Schema;
- request and mention IDs do not match;
- a cited source or external identifier was not in the request packet;
- a quotation and its offsets do not match the supplied source text;
- a returned component span does not occur in the literal mention/context; or
- its decision contradicts the number or type of returned components.

After mechanical validation, promote a proposal only when identity is supported
by one of:

1. an exact identifier-bearing authority record;
2. one authoritative source explicitly equating the names; or
3. two independent sources that explicitly corroborate the alias/component.

Otherwise it remains in review. Store the prompt template version, JSON Schema
version, model/provider, model snapshot, parameters, input hash, raw output,
validator version, decision, reviewer if any, and timestamps. Do not use a
model's self-reported numeric confidence as an acceptance rule.

### Gate 9: rerun comparison

Every LLM command must accept `--compare-decisions-to RUN_ID` and the shorthand
`--compare-decisions-to latest`. Comparison is by `(task, subject_type,
subject_key)` and by a SHA-256 of canonical, schema-validated decision fields—not
by free-form explanation or raw-response bytes. Report:

- `added`: present only in the new run;
- `removed`: present only in the comparison run;
- `changed`: the canonical decision hash differs; and
- `unchanged`: the canonical decision hash is identical.

Store both versions and the field-level JSON difference. A comparison never
overwrites or deletes the earlier result. Raw source acquisition itself makes no
LLM calls; semantic enrichment is a separate, explicitly approved run.

The read-only audit command uses the same flag independently of the model
runner:

```bash
.venv/bin/dotenv run -- .venv/bin/python -m pv.audit.llm_decisions \
  --run RUN_UUID --compare-decisions-to latest
```

### Gate 10: development-scope classification

After identity and structured pharmacology verification, apply the versioned
`human_therapeutics_v1` policy. Raw records are retained for every selected
trial, but downstream molecular literature expansion proceeds only for an
included human-biology therapeutic:

- explicit antibiotic ATC classes are excluded;
- therapeutic-primary non-human targets are excluded;
- vaccines are placed in a separate track;
- devices, behavioral interventions, exercise, and diagnostics are marked not
  applicable to molecular expansion; and
- unknown target domains remain unresolved rather than defaulting to included.

The deterministic classifier stores the decision inputs, reason, method,
policy version, and SHA-256. Distinct reruns are append-only; an identical
rerun creates no duplicate history row. The literature adapters accept only
pairs exposed by the policy-gated scope views.

## 4. LLM exchange formats

All LLM messages use JSON only. The caller generates IDs; the model may not
invent source IDs or canonical IDs. The implemented trial-wide semantic schema
is versioned in `pv.ingest.trial_semantic_llm`; the exact schema and system
prompt are also retained in each decision run. The narrower entity-adjudication
schemas are:

- [`intervention_resolution_request.schema.json`](schemas/intervention_resolution_request.schema.json)
- [`intervention_resolution_response.schema.json`](schemas/intervention_resolution_response.schema.json)
- [`target_mechanism_extraction_request.schema.json`](schemas/target_mechanism_extraction_request.schema.json)
- [`target_mechanism_extraction_response.schema.json`](schemas/target_mechanism_extraction_response.schema.json)
- [`chembl_mechanism_context_request.schema.json`](schemas/chembl_mechanism_context_request.schema.json)
- [`chembl_mechanism_context_response.schema.json`](schemas/chembl_mechanism_context_response.schema.json)

### 4.1 Intervention-resolution request

The packet contains one source mention, its trial context, the deterministic
candidate list, and the exact evidence snippets the model may use. Example:

```json
{
  "schema_version": "pv.intervention-resolution-request/1.0",
  "request_id": "018f-example-request",
  "source_record_version_id": "ctgov:NCT03525444:version-example",
  "trial": {
    "nct_id": "NCT03525444",
    "title": "A Phase 3 Study of VX-445 Combination Therapy in Subjects With Cystic Fibrosis",
    "lead_sponsor": "Vertex Pharmaceuticals Incorporated",
    "conditions": ["Cystic Fibrosis"]
  },
  "mention": {
    "mention_id": "ctgov:NCT03525444:intervention:0",
    "name": "vx-445/tez/iva",
    "description": "VX-445/tezacaftor/ivacaftor fixed-dose combination in the morning",
    "other_names": [],
    "intervention_type": "DRUG",
    "arm_labels": ["VX-445/TEZ/IVA"]
  },
  "deterministic_candidates": [
    {
      "candidate_id": "candidate:1",
      "preferred_name": "elexacaftor",
      "entity_type": "small_molecule",
      "identifiers": [{"namespace": "sponsor_code", "value": "VX-445"}],
      "matched_text": "VX-445",
      "retrieval_basis": "verified_sponsor_code_alias",
      "supporting_source_ids": ["source:regulatory-label-example"]
    }
  ],
  "evidence_snippets": [
    {
      "source_id": "source:regulatory-label-example",
      "source_record_version_id": "regulatory:label:version-example",
      "text": "VX-445 is also known as elexacaftor.",
      "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    }
  ],
  "allowed_decisions": [
    "resolved_single", "resolved_regimen", "placebo",
    "non_therapeutic", "ambiguous", "unresolved"
  ]
}
```

### 4.2 Intervention-resolution response

The model selects only candidates supplied in the request, cites exact evidence,
and reports unmatched tokens. A valid regimen response has this shape:

```json
{
  "schema_version": "pv.intervention-resolution-response/1.0",
  "request_id": "018f-example-request",
  "mention_id": "ctgov:NCT03525444:intervention:0",
  "decision": "resolved_regimen",
  "components": [
    {
      "source_span": "VX-445",
      "candidate_id": "candidate:1",
      "relationship": "active_component",
      "resolution_basis": "explicit_alias_in_supplied_source",
      "support": [
        {
          "source_id": "source:regulatory-label-example",
          "quote": "VX-445 is also known as elexacaftor.",
          "start": 0,
          "end": 36
        }
      ]
    }
  ],
  "unresolved_tokens": ["TEZ", "IVA"],
  "warnings": ["Only VX-445 has adequate support in this request packet."],
  "review_required": true
}
```

This response is intentionally incomplete rather than allowing the model to fill
missing identities from memory. A production packet for this trial would include
verified candidates and excerpts for all three components.

### 4.3 Target/mechanism extraction is a separate request

Identity resolution must not simultaneously infer pharmacology. After an asset
is resolved, a second job can receive one document passage and a whitelist of
resolved entity candidates. Its response contains assertions with:

- `assertion_kind`: `molecular_target`, `broader_mechanism`, or
  `unknown_mechanism`;
- the supplied subject and object candidate IDs;
- `literal_predicate`, copied or minimally delimited from the passage;
- a normalized action from a controlled list;
- target role and directness;
- exact quotations and offsets; and
- `review_required` plus warnings.

The normalized action is a search facet, not a replacement for the literal
predicate. A phrase such as “reduces oxidative stress” can support a broader
mechanism assertion; it cannot be converted into direct binding to an oxidative
stress-related protein.

## 5. NCT03525444 end-to-end result

The ClinicalTrials.gov mention `vx-445/tez/iva` is stored unchanged. Slash-aware
tokenization creates three component mentions. Authority-backed aliases resolve
`VX-445` to elexacaftor, `TEZ` to tezacaftor, and `IVA` to ivacaftor. The result
is a regimen entity with three `active_component` relations, plus a separate
evening ivacaftor administration where the trial says so. Placebo remains a
comparator entity and does not receive a molecular target.

Only after those identities exist are regulatory or pharmacology passages used
to create separate CFTR target/action assertions for each active component. The
original strings, the component decisions, and the target claims therefore have
different provenance and can be corrected independently.

## 6. Normalization for target-to-phenotype discovery

The same pattern applies beyond drugs:

1. retain the native name and source-native ID;
2. map exact identifiers and release-scoped aliases to a typed entity;
3. keep ambiguous synonyms as one-to-many candidate links;
4. generate source-specific search bundles from aliases valid in that release;
5. record the bundle version with every literature/database query; and
6. store each returned phenotype relationship as a source assertion, not as a
   merged truth value.

For example, a target search begins from an HGNC ID and expands to the approved
symbol, prior symbols, gene name, UniProt accessions, protein names, and selected
isoform terms. A disease search begins from the native registry term plus exact
MONDO/EFO/MeSH/Orphanet mappings. Search aliases are never used to erase the
source's original term.

## 7. What is deliberately deferred

The initial raw-corpus build does not require an LLM for literature query
expansion, document relevance classification, assay identification, or
preclinical-result extraction. Those may be added later as separately versioned
enrichment passes using the same pattern: immutable input packet, strict output
schema, exact evidence spans, validation, and no direct writes to canonical
facts.
