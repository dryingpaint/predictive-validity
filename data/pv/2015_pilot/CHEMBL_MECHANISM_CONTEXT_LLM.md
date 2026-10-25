# ChEMBL mechanism-context LLM pilot

Date: 2026-09-18

This is the second semantic stage. Trial extraction proposes an asset;
deterministic ChEMBL resolution then enumerates every parent/form mechanism.
Only after enumeration does the model receive archived ChEMBL mechanism and
target records. It cannot introduce identifiers or use component membership as
evidence that an asset targets every component.

## Completed pilot

- Model: `gpt-5.6-terra`, reasoning effort `none`
- Full run: `7c7286d6-cbc6-4789-b8c1-17f21c5e8667`
- Exact repeat: `42f61b2c-9a85-4ec4-ad50-9e765cb6e3f0`
- Assets: 17
- ChEMBL mechanisms: 20
- Validated decisions: 17
- Extracted target-context assertions: 4
- Specific-gene targets inferred from family/complex components: 0
- Review-required decisions: 0
- Repeat comparison: 17 unchanged, 0 changed, 0 added, 0 removed
- Per-full-run usage: 32,001 input tokens and 2,991 output tokens
- Per-full-run estimated cost: $0.099894

## Extracted contexts

| Asset | Canonical target | Context type | Context | Exact ChEMBL support |
|---|---|---|---|---|
| vincristine | Tubulin | subfamily | beta tubulin | Binds to beta tubulin, vinca site (PMID: 15057285) |
| vincristine | Tubulin | binding site | vinca site | Binds to beta tubulin, vinca site (PMID: 15057285) |
| digoxin | Sodium/potassium-transporting ATPase | subunit | Alpha subunit | Alpha subunit is binding site |
| interferon alfa-2b | Interferon alpha/beta receptor | subunit | Alpha subunit | Alpha subunit is binding site |

All other pilot mechanism rows produced empty context and gene-target arrays.
That is expected: the second stage structures source specificity; it does not
fill absent specificity from model knowledge.

## Vincristine output

```json
{
  "source_mechanism_id": "ChEMBL mechanism:1108",
  "target_entity_id": "b8d4de7c-af07-5d4b-ba74-ebe50dcffed8",
  "canonical_target_name": "Tubulin",
  "target_level": "protein_family",
  "target_contexts": [
    {
      "context_type": "subfamily",
      "normalized_name": "beta tubulin",
      "source_path": "mechanisms[1108].binding_site_comment",
      "quote": "Binds to beta tubulin, vinca site (PMID: 15057285)"
    },
    {
      "context_type": "binding_site",
      "normalized_name": "vinca site",
      "source_path": "mechanisms[1108].binding_site_comment",
      "quote": "Binds to beta tubulin, vinca site (PMID: 15057285)"
    }
  ],
  "specific_gene_targets": [],
  "component_membership_is_target_evidence": false,
  "warnings": []
}
```

## Count-only retrieval probe

Europe PMC counts at the time of the pilot:

| Query | Hits |
|---|---:|
| `TITLE_ABS:Tubulin` | 39,192 |
| `TITLE_ABS:"beta tubulin"` | 5,065 |
| `TITLE_ABS:"vinca site"` | 21 |
| `TITLE_ABS:"beta tubulin" OR TITLE_ABS:"vinca site"` | 5,084 |
| `TITLE_ABS:vincristine AND (TITLE_ABS:"beta tubulin" OR TITLE_ABS:"vinca site")` | 41 |

These probes were not ingested. They demonstrate that the source-derived
subfamily context is materially narrower than the broad family query. Whether
subfamily contexts replace or supplement family-level hypothesis discovery is
a search-policy decision, not an LLM decision.

## Engineering validation runs

The database also retains two failed run rows. One caught an invalid strict
JSON-Schema declaration before generation. A later full set of model calls
completed but a Python UUID adapter error prevented the transaction from
storing any decisions; the run was marked failed and no partial projections
were committed. Both defects were corrected before the completed full runs.
