### Sources in detail

Each entry gives who compiles the source and from what, what the pipeline keeps, the shape of the raw response, and a real record from the cached download, trimmed to the fields used.

#### ClinicalTrials.gov API v2

*Snapshot 2026-10-20, 222,915 studies · `GET https://clinicaltrials.gov/api/v2/studies?filter.advanced=AREA[StudyType]INTERVENTIONAL AND AREA[InterventionType](DRUG OR BIOLOGICAL)&pageSize=1000` paged by `pageToken`*

**Compiled by.** The National Library of Medicine runs the registry. Sponsors enter the protocol record and the results themselves, as FDAAA 801 requires for applicable trials. NLM reviews entries for quality but does not check them against source records.
**We use.** From the protocol section we keep status, dates, the why-stopped text, phases, sponsor and its class, design, conditions, interventions, arms, references, countries, brief summary and primary outcomes. From the results section, posted for 53,446 studies, we keep every primary outcome's values per group and every statistical analysis, plus deaths and serious adverse events per arm.
**Shape.** `{totalCount, nextPageToken, studies: [{protocolSection: {statusModule, sponsorCollaboratorsModule, designModule, armsInterventionsModule, conditionsModule, outcomesModule, referencesModule, …}, resultsSection: {participantFlowModule, baselineCharacteristicsModule, outcomeMeasuresModule, adverseEventsModule}, hasResults}]}`

```json
{"nctId": "NCT03548935", "overallStatus": "COMPLETED", "phases": ["PHASE3"],
 "leadSponsor": {"name": "Novo Nordisk A/S", "class": "INDUSTRY"},
 "startDateStruct": {"date": "2018-06-04"}, "enrollmentInfo": {"count": 1961},
 "primaryOutcomes": [{"measure": "Change in Body Weight (%)", "timeFrame": "…week 68"}],
 "outcomeMeasures[0].analyses[0]": {"pValue": "<.0001", "statisticalMethod": "ANCOVA",
   "paramType": "Treatment difference", "paramValue": "-12.44", "ciLowerLimit": "-13.37", "ciUpperLimit": "-11.51"},
 "eventGroups[0]": {"title": "Sema 2.4 mg", "deathsNumAffected": 1, "deathsNumAtRisk": 1306, "seriousNumAffected": 128}}
```

#### PubMed E-utilities

*Queried at run time; each run is recorded with its date and a hash of what it returned · `esearch.fcgi?db=pubmed&term=NCT…[si]`, then `efetch.fcgi?retmode=xml`*

**Compiled by.** NCBI indexes citations from publishers and MEDLINE. A trial registration number named in an article is recorded in its data-bank list and is searchable as a secondary identifier.
**We use.** We look up only completed industry Phase 2/3 trials, started from 2010, that posted no results. A paper links to a trial when the registry lists it as a RESULT or DERIVED reference, or when PubMed lists the NCT number. This links 2,284 trials. For each paper we keep title, first author, journal, year, DOI and abstract, and the abstracts feed the outcome classifier.
**Shape.** `<PubmedArticle><MedlineCitation><PMID/><Article><Journal/><ArticleTitle/><Abstract/><DataBankList><DataBank><AccessionNumber/></DataBank></DataBankList></Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi"/></ArticleIdList></PubmedData></PubmedArticle>`

```text
NCT03036488 (KEYNOTE-522; no posted results) -> PMID 32101663, linked by both routes
  N Engl J Med 2020, "Pembrolizumab for Early Triple-Negative Breast Cancer", Schmid P et al.
  DataBank ClinicalTrials.gov / AccessionNumber NCT03036488, doi 10.1056/NEJMoa1910549
```

#### Drugs@FDA data files

*Data to 2026-10-26 · `GET https://www.fda.gov/media/89850/download`, a zip of tab-separated tables*

**Compiled by.** FDA's drug center (CDER) publishes these files from its own application records. They cover drugs and therapeutic biologics, not the vaccines, blood products and cell or gene therapies that CBER regulates.
**We use.** NDA and BLA applications: sponsor, products and active ingredients, every original and supplement submission with its class, status, date and review priority, and the links to approval letters. That is 6,394 applications.
**Shape.** `Applications.txt` (ApplNo, ApplType, SponsorName), `Products.txt`, `Submissions.txt` (ApplNo, SubmissionClassCodeID, SubmissionType, SubmissionNo, SubmissionStatus, SubmissionStatusDate, ReviewPriority), `ApplicationDocs.txt` (type 1 = letter, URL, date).

```text
Applications     125514  BLA  MERCK SHARP DOHME
Products         125514  001  SOLUTION;INTRAVENOUS  100MG/4ML  KEYTRUDA  PEMBROLIZUMAB
Submissions      125514  class 2 (EFFICACY)  SUPPL 89  AP  2021-07-26  STANDARD
ApplicationDocs  125514  SUPPL 89  letter  …/appletter/2021/125514Orig1s089s114ltr_.pdf
```

#### FDA approval letters (CDER)

*Actions 2008 to 2026-10-22 · PDFs at `https://www.accessdata.fda.gov/drugsatfda_docs/appletter/<year>/<ApplNo>…ltr.pdf`, from the Drugs@FDA links*

**Compiled by.** The review division sends the letter to the sponsor when it acts, and FDA posts it. It names the approved submission and, for efficacy supplements, usually the new use it provides for.
**We use.** We fetch letters for every approved original application and every efficacy supplement. Text comes from the PDF's text layer, or from OCR when that layer is empty or garbled. An LLM records each approved use from the letter: disease, verbatim indication, qualifiers, type of change and accelerated approval.

```text
BLA 125514/S-089 + S-114 (Keytruda, 2021-07-26):
"(S-089) provides for a new indication for the treatment of patients with high-risk, early-stage
 triple negative breast cancer, in combination with chemotherapy as neoadjuvant treatment, then as
 a single agent as adjuvant treatment after surgery…"
-> use: triple-negative breast cancer · new population · not accelerated
-> use (S-114): metastatic TNBC, PD-L1 CPS ≥10 · conversion of the 2020 accelerated approval to full
```

#### openFDA drug labels

*Export 2026-10-28, 262,903 labels · `GET https://api.fda.gov/download.json` lists the bulk files, e.g. `https://download.open.fda.gov/drug/label/drug-label-0001-of-0014.json.zip`*

**Compiled by.** Manufacturers submit Structured Product Labeling to FDA. openFDA republishes it in bulk with harmonised identifiers and notes that the data are not validated.
**We use.** We keep the current label of each NDA or BLA product, 5,273 in all, with its application numbers, names, UNII and the full Indications and Usage text. The approval classifier reads that text as evidence of approved uses, including uses approved before 2008.
**Shape.** `{meta, results: [{set_id, id, version, effective_time, indications_and_usage: [str], …, openfda: {application_number[], brand_name[], generic_name[], substance_name[], unii[]}}]}`

```json
{"set_id": "9333c79b-d487-4538-a9f0-71b91a02b287", "effective_time": "20260710",
 "openfda": {"application_number": ["BLA125514"], "brand_name": ["KEYTRUDA"], "unii": ["DPT0O3T46P"]},
 "indications_and_usage": ["1 INDICATIONS AND USAGE KEYTRUDA is a programmed death receptor-1 (PD-1)-blocking
   antibody indicated: Melanoma for the treatment of patients with unresectable or metastatic melanoma. …"]}
```

#### CBER biologics approvals

*Actions 2015-01-09 to 2025-12-19, 324 records on 177 applications · yearly pages `https://www.fda.gov/vaccines-blood-biologics/development-approval-process-cber/<year>-biological-license-application-approvals`, live from 2023 and from the Wayback Machine before; product pages; letter PDFs at `https://www.fda.gov/media/<id>/download`*

**Compiled by.** FDA's biologics center posts a yearly table of original licence approvals and noteworthy supplements, and a page per product linking its letters. None of these products are in Drugs@FDA.
**We use.** We keep original licences and supplements that add or change an indication, population, dose or formulation, with each letter's text. 53 letters came from Wayback captures. For the 10 records without a letter, the yearly-table entry stands in.

```json
{"appl_no": "125646", "submission_type": "ORIG", "approval_date": "2017-08-30",
 "product_brand": "KYMRIAH", "proper_name": "tisagenlecleucel", "product_class": "cell_therapy",
 "url": "https://www.fda.gov/media/106989/download", "pdf_source": "fda.gov",
 "yearly_listing_text": "KYMRIAH Tisagenlecleucel | For the treatment of patients up to 25 years of age with B-cell precursor ALL …"}
```

#### FDA Global Substance Registration System (UNII)

*2026-08-04, 171,912 substances and 1,047,975 names · `https://precision.fda.gov/uniisearch/archive/2026-08-04/UNII_Data_20260804.zip`, plus the matching names file*

**Compiled by.** FDA assigns each Unique Ingredient Identifier from a substance's structure or defining information. It collects the substance's names from INN, USAN, JAN, brands and sponsor codes, each tagged with its type.
**We use.** Substances, with their INN, RxNorm and PubChem cross-references, and every name in normalised form. These resolve trial intervention names to one molecular entity and merge entities that are the same substance.
**Shape.** Records: 25 tab-separated columns, including UNII, DISPLAY_NAME, RXCUI, PUBCHEM, INN_ID, INCHIKEY and SUBSTANCE_TYPE. Names: NAME, TYPE (brand, code, common, official or systematic), UNII.

```text
53AXN4NNHX  SEMAGLUTIDE  RXCUI 1991302  PUBCHEM 56843331  INN_ID 9113  SUBSTANCE_TYPE protein
  names: NN9535 (code) · NNC-0113-0217 (code) · OZEMPIC (brand) · WEGOVY (brand) · SEMAGLUTIDE [JAN] (common)
```

#### MONDO disease ontology

*2026-10-06 · `https://github.com/monarch-initiative/mondo/releases/latest/download/mondo.obo`*

**Compiled by.** The Monarch Initiative merges disease terms from OMIM, Orphanet, DOID, NCIT, EFO and others into one hierarchy. Each cross-reference is tagged as an exact equivalence or a looser relation.
**We use.** We keep terms, exact synonyms, obsolete flags, the is-a hierarchy with its full ancestor closure, and the cross-references with their equivalence flag. MONDO is the target vocabulary for trial conditions and for Open Targets diseases. Its hierarchy defines disease similarity: subtypes, and Lin ≥ 0.8.

```text
id: MONDO:0005439
name: familial hypercholesterolemia
synonym: "hyperlipoproteinemia type II" EXACT []
xref: EFO:0004911 {source="MONDO:equivalentTo"}      -> equivalent
xref: ICD9:V19.8 {source="MONDO:relatedTo"}          -> not equivalent
is_a: MONDO:0001336 ! familial hyperlipidemia
```

#### EFO

*Reaches the analysis only as Open Targets disease identifiers*

**Compiled by.** EMBL-EBI maintains EFO for Open Targets, the GWAS Catalog and Expression Atlas. It imports disease classes from MONDO and other ontologies and adds terms of its own.
**We use.** No EFO file. Open Targets keys 9,257 of its diseases by EFO identifiers. Each is mapped to MONDO through the disease's own MONDO cross-reference, then MONDO's declared equivalence to the EFO term. Failing both, it maps through a DOID, Orphanet, NCIT or MeSH cross-reference that points to a single MONDO term.

```text
EFO_0000768 idiopathic pulmonary fibrosis: no MONDO xref, and no MONDO term lists EFO:0000768
  -> DOID:0050156 and Orphanet:2032 are both equivalent to MONDO:0800504
```

#### Mammalian Phenotype ontology

*2026-09-23 · `http://purl.obolibrary.org/obo/mp.obo`*

**Compiled by.** Mouse Genome Informatics at the Jackson Laboratory maintains it. MGI and IMPC curators use it to annotate phenotypes of mutant mice.
**We use.** The hierarchy only. A target counts as "knockout lethal before weaning" when any of its Open Targets mouse phenotypes is MP:0010770 *preweaning lethality* or a descendant. That flags 688 genes.

```text
id: MP:0011100
name: preweaning lethality, complete penetrance
is_a: MP:0010770 ! preweaning lethality
```

#### Gene symbols and identifiers

*Project catalogue, resolved through HGNC 2026-10-16 · `https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt`*

**Compiled by.** HGNC approves one symbol per human gene and records each gene's previous symbols and aliases. The project's own catalogue of 26,957 human proteins adds Ensembl identifiers, Pharos development level and family, and RefSeq summaries; some of its symbols predate HGNC renames.
**We use.** A target the LLM names is accepted when the symbol is a catalogue protein, or an HGNC approved, previous or alias symbol of one (an alias two genes share is not used). Ensembl identifiers join targets to Open Targets, gnomAD and DepMap.
**Shape.** Tab-separated, one approved gene per row: `hgnc_id, symbol, name, locus_group, alias_symbol, prev_symbol, entrez_id, ensembl_gene_id, uniprot_ids, …`, with lists separated by `|`.

```text
HGNC:11701  CRIPTO  cripto, EGF-CFC family member  protein-coding gene  prev_symbol TDGF1  ensembl ENSG00000241186
TDGF1 (previous) -> CRIPTO · CTGF (previous) -> CCN2 · CD20 (alias) -> MS4A1 · TIM3 (alias) -> HAVCR2
```

#### ChEMBL mechanisms of action

*ChEMBL 37 (2026-05-01), 7,561 mechanisms · `GET https://www.ebi.ac.uk/chembl/api/data/mechanism.json?limit=1000&offset=…`, then `target.json` and `molecule.json` for the ids they name*

**Compiled by.** EMBL-EBI curators assign each approved or clinical-stage drug its molecular targets and action type, with references from labels and the literature.
**We use.** Only as hints. When the LLM assigns an entity's targets, it sees every mechanism of the parent molecule of each of its ChEMBL ids, as "SYMBOL: action" for each human gene of the target; its own answer is what we store. A target's genes are its UniProt components mapped to HGNC, so a complex or receptor family keeps all of them (1,257 mechanisms name more than one gene); mechanisms with no human gene, such as antibacterials, are shown as text.
**Shape.** `{mechanisms: [{mec_id, molecule_chembl_id, parent_molecule_chembl_id, target_chembl_id, action_type, mechanism_of_action, …}], page_meta: {next, …}}`; a target's `target_components[{accession}]` give its genes.

```json
{"mec_id": 8862, "molecule_chembl_id": "CHEMBL4297839", "target_chembl_id": "CHEMBL4383", "action_type": "AGONIST",
 "mechanism_of_action": "Gastric inhibitory polypeptide receptor agonist"}
{"mec_id": 8994, "molecule_chembl_id": "CHEMBL4297839", "target_chembl_id": "CHEMBL1784", "action_type": "AGONIST",
 "mechanism_of_action": "Glucagon-like peptide 1 receptor agonist"}
```

Tirzepatide's hints: GIPR: agonist, GLP1R: agonist.

#### gnomAD constraint

*v4.1 · loaded by earlier project code*

**Compiled by.** The Broad Institute's gnomAD compares each gene's observed loss-of-function variants, in exomes and genomes from about 800,000 people, with the number a mutation model expects. LOEUF is the upper bound of the 90% interval of observed over expected, and a low value means the gene does not tolerate loss of function.
**We use.** A target is LoF-intolerant when its LOEUF is below 0.35. That flags 1,385 of 18,164 genes. The value is today's, not the value at phase entry.

```text
PCSK9   pLI 1.1e-20  LOEUF 1.25    missense z 0.59
POLR2A  pLI 1.0      LOEUF 0.161   missense z 9.21
```

#### DepMap gene essentiality

*DepMap Public 24Q4 · `CRISPRInferredCommonEssentials.csv` from the release's figshare record, `https://api.figshare.com/v2/articles/27993248/files`*

**Compiled by.** The Broad Institute's Cancer Dependency Map knocks out every gene by CRISPR in about a thousand cancer cell lines, and Chronos estimates each gene's effect on growth. DepMap's inferred common-essential list holds the genes whose knockout ranks among the most depleting in most lines.
**We use.** That list, 1,523 genes keyed by Entrez id and mapped to Ensembl through HGNC, as the pan-essential flag. It is the 24Q4 release, not the state at phase entry; it is the newest release the DepMap portal's download block leaves reachable to scripts.
**Shape.** One column, `Essentials`, each row `SYMBOL (Entrez id)`.

```text
Essentials
AAMP (14)
AARS1 (16)
POLR2B (5431)
```

#### Open Targets Platform: associations

*26.09 · `https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.09/output/association_by_datasource_direct/*.parquet` and `…/disease/`*

**Compiled by.** EMBL-EBI, the Wellcome Sanger Institute and partners run Open Targets. It maps evidence from about 20 resources to Ensembl genes and to disease terms (MONDO, EFO, HP, Orphanet) and scores each item from 0 to 1. Per target, disease and datasource, it combines the items into one association score with a weighted harmonic sum. A "direct" association counts only evidence annotated to that exact disease, not to its subtypes. Each association carries a yearly series of its cumulative score.
**We use.** Direct associations from the 17 datasources below, for targets of drugs in industry programs. We keep the score, the evidence count and the yearly series, so evidence is taken as of the year before phase entry. The yearly series leaves out undated evidence.
**Shape.** `targetId, diseaseId, aggregationValue (datasource), associationScore, evidenceCount, timeseries[{year, associationScore, yearlyEvidenceCount}]`; diseases: `id, name, dbXRefs[], therapeuticAreas[]`.

```json
{"targetId": "ENSG00000169174", "diseaseId": "MONDO_0005439", "aggregationValue": "eva",
 "associationScore": 0.875, "evidenceCount": 829,
 "timeseries": [{"year": 2018, "associationScore": 0.0}, {"year": 2019, "associationScore": 0.704},
                {"year": 2021, "associationScore": 0.800}, {"year": 2026, "associationScore": 0.875},
                {"year": null, "associationScore": 0.875}]}
```

PCSK9 · familial hypercholesterolemia, ClinVar evidence.

#### Open Targets Platform: evidence

*26.09 · `…/output/evidence_<datasource>/*.parquet` and `…/mouse_phenotype/`*

**Compiled by.** One row per supporting item: a variant, study, curated assertion, mouse model, expression contrast or reaction. Each row has a 0–1 score and the upstream statistic. Where the source allows, it also has a date, a confidence grade, and the direction of effect on the target (loss or gain of function) and on the trait (risk or protection).
**We use.** Every row for program targets. Section 3 groups them into families and strength tiers, such as locus-to-gene ≥ 0.8, burden p < 2.5e-6, ClinGen definitive or strong, and PanelApp green. Mouse phenotypes give the knockout-lethality flag.
**Shape.** `id, targetId, diseaseId, datasourceId, score, resourceScore, confidence, publicationDate, directionOnTarget, directionOnTrait, variantFunctionalConsequenceId, literature[]`, plus source-specific fields such as `studyLocusId`, `beta`, `pValueMantissa`/`pValueExponent`, `clinicalSignificances`, `biologicalModelAllelicComposition`, `log2FoldChangeValue`.

```json
{"datasourceId": "gene_burden", "targetId": "ENSG00000169174", "diseaseId": "EFO_0022275",
 "projectId": "AstraZeneca PheWAS Portal", "cohortId": "UK Biobank 470k", "statisticalMethod": "flexdmg",
 "studyCasesWithQualifyingVariants": 584, "beta": -0.527, "pValueMantissa": 2.107, "pValueExponent": -40,
 "score": 1.0, "directionOnTarget": "LoF", "directionOnTrait": "protect", "publicationDate": "2021-08-10"}
```

PCSK9 loss of function lowers free cholesterol in very small VLDL.

| Datasource | Upstream and how Open Targets builds it | A row asserts | Example (target · disease · value) |
| :---- | :---- | :---- | :---- |
| GWAS credible sets | GWAS Catalog and summary statistics, fine-mapped; genes assigned by the locus-to-gene model | A fine-mapped locus implicates the gene; score = locus-to-gene | PCSK9 · LDL cholesterol · 0.987 |
| Gene burden | Rare-variant burden tests in exome cohorts (AstraZeneca PheWAS, Genebass, Regeneron, FinnGen and others) | Qualifying variants associate with the trait; effect, p, direction | PCSK9 · VLDL free cholesterol · β −0.53, p 2e-40, LoF protective |
| ClinVar (EVA) | ClinVar germline submissions via EMBL-EBI | A variant is classified for the disease; review status as confidence | PCSK9 · hypercholesterolemia AD3 · pathogenic, multiple submitters |
| Genomics England PanelApp | Diagnostic gene panels | Gene is on the disease's panel; green (diagnostic grade) or amber | PCSK9 · familial hypercholesterolaemia panel · green |
| Orphanet | Expert-curated gene–rare disease links | Gene causes or is associated with the disease | PCSK9 · homozygous FH · assessed |
| Gene2Phenotype | EMBL-EBI curated panels | Gene–disease link with allelic requirement; definitive to limited | LDLR · hypercholesterolemia · definitive, monoallelic |
| ClinGen | Gene–disease validity expert panels | Validity classification, definitive to refuted | PCSK9 · hypercholesterolemia AD3 · definitive (2018) |
| UniProt literature | UniProtKB disease annotations, from OMIM and the literature | Gene is involved in the disease | PCSK9 · hypercholesterolemia AD3 · high, 5 papers |
| UniProt variants | UniProtKB curated disease variants | A specific variant causes the disease | LDLR · FH type 1 · rs879254753 |
| Cancer Gene Census | COSMIC census drivers with per-tumour mutation counts | Gene drives the tumour type; oncogene (GoF) or suppressor (LoF) | EGFR · ovarian adenocarcinoma · GoF, 24/54 samples |
| IntOGen | Driver discovery over tumour cohorts (TCGA, PCAWG) | Gene is a significant driver in the cohort | EGFR · lung adenocarcinoma · p 2e-48, 7 methods |
| ClinVar somatic | ClinVar somatic submissions | A somatic variant is classified for the disease | LDLR · FH type 1 · pathogenic, expert panel |
| IMPC | IMPC and MGI mouse models, matched to diseases by PhenoDigm phenotype similarity | The mutant's phenotypes resemble the disease's | PCSK9 · hyperlipoproteinemia V · knockout, PhenoDigm 95 |
| Expression Atlas | Disease-versus-normal differential expression experiments | Gene is differentially expressed in the disease | PCSK9 · psoriasis · log2FC +2.5 |
| Reactome | Curated disease reactions | A variant perturbs a reaction in a disease pathway | CFTR · cystic fibrosis · F508del binds ERAD machinery |
| CRISPR | Project Score knockout fitness screens in cancer lines | Gene is a fitness dependency in that cancer type | KRAS · plasma cell myeloma · priority 78 |
| CRISPR screens | CRISPRbrain screens in iPSC-derived neurons | Perturbing the gene shifts a screen phenotype | LDLR · neurodegeneration · log2FC −5.8 |
| Mouse phenotypes | IMPC and MGI phenotype annotations (MP terms), not linked to a disease | A mutant allele shows the phenotype | PCSK9 · decreased circulating LDL cholesterol |

We leave out three datasources. Clinical precedence and cancer biomarkers come from drugs' clinical records, so they would leak the outcome. Europe PMC counts literature co-mentions of gene and disease, which is attention, not evidence. For PCSK9 and familial hypercholesterolemia, clinical precedence alone scores 0.97.
