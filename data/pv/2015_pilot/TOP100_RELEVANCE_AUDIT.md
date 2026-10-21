# Europe PMC top-100 relevance cutoff audit

Retrieved: 2026-09-18T22:25:33.556103+00:00

This is a read-only cutoff audit. Europe PMC's `sort` parameter was omitted, so the provider's default relevance order was used. The comparator is the complete asset-mention corpus already retained in Neon. Text rules are only review probes and are not evidence labels or ingestion filters.

| Asset | Provider hits | Top publication-year span | Strong probes in top | Strong probes below | Old indication-query papers below |
|---|---:|---:|---:|---:|---:|
| follitropin beta | 92 | 1978–2026 | 4 | 0 | 0 |
| interferon alfa-2b | 1,038 | 2012–2026 | 0 | 2 | 0 |
| filgrastim | 2,342 | 2022–2026 | 4 | 51 | 1 |
| rituximab | 34,767 | 2026–2026 | 4 | 2,804 | 327 |
| nicotine | 60,006 | 2026–2026 | 13 | 2,343 | 538 |

## Cutoff result

The hard provider-relevance cutoff is not cleared by this audit for interferon alfa-2b, filgrastim, rituximab, nicotine: the retained full corpus contains purpose-oriented review probes outside the cutoff. These require manual adjudication before the cutoff can be accepted or rejected.
The cutoff does not truncate follitropin beta because the complete provider result set is at most 100.

Manual review rejects relevance top 100 as a standalone policy for broad
assets. The below-cutoff rituximab set contains the Cell anti-CD47/rituximab
phagocytosis and tumor-eradication study and multiple primary in-vitro mechanism
studies. The nicotine set contains an in-vivo dose-selection paper and rat
behavioral studies of nicotine seeking and vulnerability. These are directly
material to preclinical model and endpoint assessment. The first 100 relevance
results for both assets were all published in 2026, and these older papers were
not in the first 1,000.

Citation top 100 only partly rescues the problem. It includes the anti-CD47
paper (citation rank 36) and the nicotine in-vivo dose-selection paper (rank
63), but misses primary rituximab in-vitro papers at ranks 199 and 342 and the
rat nicotine-seeking paper at rank 386. By contrast, the leading below-cutoff
interferon and filgrastim probes are mostly clinical, economic, or supportive-
care studies, showing that the text probe is useful for audit sampling but is
not itself a relevance classifier.

Therefore a strict retained-paper budget of 100, if adopted, must be filled by
a purpose-aware composite selection after scanning metadata—not by taking the
first 100 from either provider relevance or citation order. Known sentinel
papers also need a pinned exception independent of rank.

## follitropin beta

Phenotype context: female infertility. Europe PMC reported 92 matches.

Highest-priority audit probes below the cutoff:

No paper met the strong audit-probe rule below the cutoff.

## interferon alfa-2b

Phenotype context: carcinoma of urethra, urinary bladder carcinoma, urothelial carcinoma. Europe PMC reported 1,038 matches.

Highest-priority audit probes below the cutoff:

- Phase II trial of intravenous flourouracil and subcutaneous interferon alfa-2b for biliary tract cancer.
  `doi:10.1200/jco.1996.14.8.2311`; published=1996-08-01; title mentions=1; abstract mentions=1; model groups=0; endpoint groups=2; citations=74; citation rank=138; relevance rank within scan=728
- Prophylaxis of superficial bladder cancer with mitomycin or interferon alfa-2b: results of a multicentric Italian study.
  `doi:10.1200/jco.1994.12.1.7`; published=1994-01-01; title mentions=1; abstract mentions=1; model groups=0; endpoint groups=1; citations=28; citation rank=312; relevance rank within scan=770

## filgrastim

Phenotype context: diffuse large B-cell lymphoma. Europe PMC reported 2,342 matches.

Highest-priority audit probes below the cutoff:

- Recombinant methionyl human stem cell factor and filgrastim for peripheral blood progenitor cell mobilization and transplantation in non-Hodgkin's lymphoma patients--results of a phase I/II trial.
  `doi:10.1182/blood.v89.9.3136`; published=1997-05-01; title mentions=1; abstract mentions=7; model groups=0; endpoint groups=1; citations=51; citation rank=225; relevance rank within scan=not in scan
- Cost-effectiveness of filgrastim and pegfilgrastim as primary prophylaxis against febrile neutropenia in lymphoma patients.
  `doi:10.1093/jnci/djt182`; published=2013-07-19; title mentions=1; abstract mentions=7; model groups=0; endpoint groups=1; citations=27; citation rank=470; relevance rank within scan=616
- A randomised phase II study of the efficacy, safety and cost-effectiveness of pegfilgrastim and filgrastim after autologous stem cell transplant for lymphoma and myeloma (PALM study).
  `doi:10.1016/j.ejca.2011.12.016`; published=2012-01-14; title mentions=1; abstract mentions=6; model groups=0; endpoint groups=2; citations=23; citation rank=550; relevance rank within scan=695
- A randomized, non-inferiority study comparing efficacy and safety of a single dose of pegfilgrastim versus daily filgrastim in pediatric patients after autologous peripheral blood stem cell transplant.
  `doi:10.1371/journal.pone.0053252`; published=2013-01-07; title mentions=1; abstract mentions=5; model groups=0; endpoint groups=2; citations=16; citation rank=758; relevance rank within scan=675
- Results of a Prospective Randomized, Open-Label, Noninferiority Study of Tbo-Filgrastim (Granix) versus Filgrastim (Neupogen) in Combination with Plerixafor for Autologous Stem Cell Mobilization in Patients with Multiple Myeloma and Non-Hodgkin Lymphoma.
  `doi:10.1016/j.bbmt.2017.07.023`; published=2017-08-07; title mentions=2; abstract mentions=20; model groups=0; endpoint groups=2; citations=15; citation rank=785; relevance rank within scan=327
- Evaluation of the efficacy and safety of original filgrastim (Neupogen®), biosimilar filgrastim (Leucostim®) and Lenograstim (Granocyte®) in CD34(+) peripheral hematopoietic stem cell mobilization procedures for allogeneic hematopoietic stem cell transplant donors.
  `doi:10.1016/j.transci.2016.03.003`; published=2016-03-24; title mentions=2; abstract mentions=6; model groups=0; endpoint groups=1; citations=15; citation rank=787; relevance rank within scan=499
- Tbo-Filgrastim versus Filgrastim during Mobilization and Neutrophil Engraftment for Autologous Stem Cell Transplantation.
  `doi:10.1016/j.bbmt.2015.05.024`; published=2015-05-30; title mentions=2; abstract mentions=13; model groups=0; endpoint groups=2; citations=15; citation rank=791; relevance rank within scan=446
- Pegfilgrastim compared with filgrastim for cytokine-alone mobilization of autologous haematopoietic stem and progenitor cells.
  `doi:10.1038/bmt.2012.145`; published=2012-07-30; title mentions=1; abstract mentions=6; model groups=0; endpoint groups=1; citations=13; citation rank=872; relevance rank within scan=688
- Cost effectiveness of pegfilgrastim versus filgrastim after high-dose chemotherapy and autologous stem cell transplantation in patients with lymphoma and myeloma: an economic evaluation of the PALM Trial.
  `doi:10.1007/s40258-013-0011-7`; published=2013-04-01; title mentions=1; abstract mentions=8; model groups=0; endpoint groups=1; citations=10; citation rank=1017; relevance rank within scan=740
- Four doses of unpegylated versus one dose of pegylated filgrastim as supportive therapy in R-CHOP-14 for elderly patients with diffuse large B-cell lymphoma.
  `doi:10.1111/bjh.13358`; published=2015-03-29; title mentions=1; abstract mentions=6; model groups=0; endpoint groups=1; citations=9; citation rank=1066; relevance rank within scan=535

## rituximab

Phenotype context: diffuse large B-cell lymphoma. Europe PMC reported 34,767 matches.

Highest-priority audit probes below the cutoff:

- Anti-CD47 antibody synergizes with rituximab to promote phagocytosis and eradicate non-Hodgkin lymphoma.
  `doi:10.1016/j.cell.2010.07.044`; published=2010-09-01; title mentions=1; abstract mentions=5; model groups=1; endpoint groups=1; citations=946; citation rank=36; relevance rank within scan=not in scan
- Rituximab in B-Cell Hematologic Malignancies: A Review of 20 Years of Clinical Experience.
  `doi:10.1007/s12325-017-0612-x`; published=2017-10-05; title mentions=1; abstract mentions=7; model groups=2; endpoint groups=1; citations=472; citation rank=103; relevance rank within scan=not in scan
- From the bench to the bedside: ways to improve rituximab efficacy.
  `doi:10.1182/blood-2004-03-1110`; published=2004-06-29; title mentions=1; abstract mentions=6; model groups=2; endpoint groups=1; citations=363; citation rank=179; relevance rank within scan=not in scan
- lenalidomide enhances natural killer cell and monocyte-mediated antibody-dependent cellular cytotoxicity of rituximab-treated CD20+ tumor cells.
  `doi:10.1158/1078-0432.ccr-07-4405`; published=2008-07-01; title mentions=1; abstract mentions=5; model groups=2; endpoint groups=1; citations=354; citation rank=189; relevance rank within scan=not in scan
- Biologic response of B lymphoma cells to anti-CD20 monoclonal antibody rituximab in vitro: CD55 and CD59 regulate complement-mediated cell lysis.
  `doi:10.1182/blood.v95.12.3900`; published=2000-06-01; title mentions=1; abstract mentions=6; model groups=3; endpoint groups=3; citations=343; citation rank=199; relevance rank within scan=not in scan
- Rituximab: a review of its use in non-Hodgkin's lymphoma and chronic lymphocytic leukaemia.
  `doi:10.2165/00003495-200363080-00005`; published=2003-01-01; title mentions=1; abstract mentions=38; model groups=2; endpoint groups=4; citations=341; citation rank=203; relevance rank within scan=not in scan
- Past, Present, and Future of Rituximab-The World's First Oncology Monoclonal Antibody Therapy.
  `doi:10.3389/fonc.2018.00163`; published=2018-06-04; title mentions=1; abstract mentions=8; model groups=2; endpoint groups=3; citations=282; citation rank=292; relevance rank within scan=not in scan
- The mechanism of tumor cell clearance by rituximab in vivo in patients with B-cell chronic lymphocytic leukemia: evidence of caspase activation and apoptosis induction.
  `doi:10.1182/blood.v99.3.1038`; published=2002-02-01; title mentions=1; abstract mentions=5; model groups=1; endpoint groups=1; citations=270; citation rank=318; relevance rank within scan=not in scan
- In vitro mechanisms of action of rituximab on primary non-Hodgkin lymphomas.
  `doi:10.1182/blood-2002-02-0469`; published=2002-10-03; title mentions=1; abstract mentions=6; model groups=2; endpoint groups=4; citations=260; citation rank=342; relevance rank within scan=not in scan
- Rituximab and CHOP induction therapy for newly diagnosed mantle-cell lymphoma: molecular complete responses are not predictive of progression-free survival.
  `doi:10.1200/jco.2002.20.5.1288`; published=2002-03-01; title mentions=1; abstract mentions=5; model groups=1; endpoint groups=3; citations=258; citation rank=348; relevance rank within scan=not in scan

## nicotine

Phenotype context: nicotine dependence. Europe PMC reported 60,006 matches.

Highest-priority audit probes below the cutoff:

- Guidelines on nicotine dose selection for in vivo research.
  `doi:10.1007/s00213-006-0441-0`; published=2006-08-09; title mentions=1; abstract mentions=9; model groups=4; endpoint groups=1; citations=673; citation rank=63; relevance rank within scan=not in scan
- Nicotine activation of alpha4* receptors: sufficient for reward, tolerance, and sensitization.
  `doi:10.1126/science.1099420`; published=2004-11-01; title mentions=1; abstract mentions=6; model groups=1; endpoint groups=1; citations=526; citation rank=108; relevance rank within scan=not in scan
- Impulsive choice and impulsive action predict vulnerability to distinct stages of nicotine seeking in rats.
  `doi:10.1016/j.biopsych.2007.07.011`; published=2007-09-19; title mentions=1; abstract mentions=9; model groups=1; endpoint groups=1; citations=301; citation rank=386; relevance rank within scan=not in scan
- Sex differences in nicotine effects and self-administration: review of human and animal evidence.
  `doi:10.1080/14622299050011431`; published=1999-12-01; title mentions=1; abstract mentions=9; model groups=1; endpoint groups=1; citations=273; citation rank=455; relevance rank within scan=not in scan
- Nicotine-induced increase in neuronal nicotinic receptors results from a decrease in the rate of receptor turnover.
  `doi:10.1016/s0026-895x(25)09730-5`; published=1994-09-01; title mentions=1; abstract mentions=10; model groups=1; endpoint groups=1; citations=265; citation rank=479; relevance rank within scan=not in scan
- Presynaptic nicotinic modulation of dopamine release in the three ascending pathways studied by in vivo microdialysis: comparison of naive and chronic nicotine-treated rats.
  `doi:10.1046/j.1471-4159.1997.68041511.x`; published=1997-04-01; title mentions=1; abstract mentions=10; model groups=3; endpoint groups=2; citations=218; citation rank=667; relevance rank within scan=not in scan
- Complex interactions between nicotine and nonpharmacological stimuli reveal multiple roles for nicotine in reinforcement.
  `doi:10.1007/s00213-005-0178-1`; published=2005-10-21; title mentions=2; abstract mentions=10; model groups=2; endpoint groups=1; citations=216; citation rank=676; relevance rank within scan=not in scan
- Nicotine-induced conditioned place preference in adolescent and adult rats.
  `doi:10.1016/s0031-9384(02)00818-1`; published=2002-09-01; title mentions=1; abstract mentions=10; model groups=2; endpoint groups=1; citations=204; citation rank=766; relevance rank within scan=not in scan
- Nicotine as a modulator of behavior: beyond the inverted U.
  `doi:10.1016/s0165-6147(03)00230-x`; published=2003-09-01; title mentions=1; abstract mentions=5; model groups=1; endpoint groups=2; citations=203; citation rank=776; relevance rank within scan=not in scan
- Evidence for enhanced neurobehavioral vulnerability to nicotine during periadolescence in rats.
  `doi:10.1523/jneurosci.23-11-04712.2003`; published=2003-06-01; title mentions=1; abstract mentions=6; model groups=1; endpoint groups=1; citations=198; citation rank=811; relevance rank within scan=not in scan

## Interpretation limits

The audit can show that a hard cutoff loses plausible papers. It cannot measure true recall because the retained corpus has not been exhaustively relevance-labeled. A final cutoff decision therefore needs manual review of the below-cutoff probes and a pinned-sentinel exception for known important papers.
