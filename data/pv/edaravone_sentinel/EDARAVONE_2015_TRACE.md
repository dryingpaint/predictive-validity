# Edaravone 2015 sentinel trace

Checked 2026-09-18 against `pv_literature_v2`.

## Trial and normalization

- Trial: `NCT01929096`, *Compound Edaravone Injection for Acute Ischemic Stroke*
- Status: completed
- Actual completion: `2015-02` (month precision)
- Normalized indication: ischemic stroke (`MONDO:1060198`)
- Resolved intervention: Edaravone Injection -> edaravone (`CHEMBL290916`, PubChem CID `4021`)
- Still unresolved: Compound Edaravone Injection. It must not be collapsed into
  edaravone because the product is the edaravone/dexborneol combination.

ChEMBL returns one complete mechanism row for edaravone. Its
`target_chembl_id` is null and its mechanism text is `Unknown`. The canonical
projection therefore contains:

- zero `asset_target_assertion` rows;
- one `asset_mechanism_assertion` row; and
- one mechanism entity, `therapeutic mechanism unknown`.

The targetless mechanism is sufficient to retain a verified human therapeutic
asset in development scope. It is not converted into a protein target.

## Active-policy literature behavior

The current active policy scheduled one provider query:

| Path | Result |
|---|---:|
| Asset + indication | 494 complete provider hits and 494 canonical works |
| Effective target only | Not scheduled: edaravone has no verified target |
| Local target + indication projection | Not produced: there is no target corpus |

Of the 494 asset/indication works, 487 have abstracts and 249 are marked open
access by Europe PMC. The active query is stored as retrieval query `1237`.
The replay quotes hyphenated research codes such as `MCI-186` and excludes the
pharmacopeial impurity label `Antipyrine related compound A` from search while
retaining it in the raw alias ledger. This removed seven false-positive stroke
papers from the first diagnostic run.

Representative results include:

- *Effect of a novel free radical scavenger, edaravone (MCI-186), on acute brain
  infarction* (clinical randomized trial);
- *Neuroprotective effects of edaravone: a novel free radical scavenger in
  cerebrovascular injury* (mechanistic review);
- *Edaravone, a free radical scavenger, inhibits MMP-9-related brain hemorrhage
  in rats treated with tissue plasminogen activator* (rat MCAO plus human brain
  endothelial-cell experiments);
- *Anti-inflammatory effects of Edaravone and Scutellarin ... in rats and in
  BV-2 microglia*;
- *The synergetic effect of edaravone and borneol in the rat model of ischemic
  stroke*; and
- *Edaravone protects HT22 neurons from H2O2-induced apoptosis*.

## Diagnostic mechanism-scoped searches

These counts are live diagnostic Europe PMC counts and are not active-corpus
memberships. They use only the source-grounded mechanism family `free-radical
scavenging / oxidative stress / lipid peroxidation` and conservative edaravone
aliases (`edaravone`, `MCI-186`, `Radicava`).

| Mechanism relationship being tested | Europe PMC hits |
|---|---:|
| Asset + mechanism | 916 |
| Mechanism + ischemic stroke | 7,716 |
| Asset + indication + mechanism | 235 |

Interpretation:

- Asset + mechanism efficiently finds the pharmacology and experimental
  literature, but it also retrieves work in ALS and other indications.
- Mechanism + indication is deliberately broad and contains much general
  oxidative-stress and ferroptosis literature. It supports the mechanism-to-
  disease hypothesis but must not be attributed to edaravone.
- Asset + indication + mechanism is the most specific set for experiments that
  jointly concern edaravone, stroke and the proposed mechanism.

The active pipeline currently stores only asset + indication for targetless
assets. Mechanism-specific query manifests and candidate relationships require
a mechanism analogue of the effective-target stream before these two broader
diagnostic searches should be activated at scale.

## Replay checks

- Replanning inserted zero work items.
- Completed work items: 1.
- Duplicate work keys: 0.
- Duplicate canonical candidates: 0.
- Stale running leases: 0.
