## Industry failure modes

Of development programs that entered Phase 1 in 2015–2025 and were developed in the US, {{section1.us_site.loa|pct}} reached FDA approval for their disease (95% CI {{section1.us_site.loa_lo|pct}}–{{section1.us_site.loa_hi|pct}}), against BIO's {{bio.loa}} for 2011–2020 ({{bio.loa_novel}} for novel drugs). Across all industry programs registered on ClinicalTrials.gov, including those run only outside the US, the figure is {{section1.overall.loa|pct}}. Most programs stop without a stated reason: of {{section1.failure_modes.n_suspended|int}} programs that stopped, {{section1.failure_modes.family_share.all.unexplained|pct0}} left no stated reason and no posted or published result, and {{section1.failure_modes.family_share.all.biology|pct0}} record an efficacy, safety or pharmacokinetic reason.

### How programs are counted

* **Trial:** a registered interventional study listing Early Phase 1 to Phase 3. A Phase 1/2 trial counts as Phase 2 and a Phase 2/3 trial as Phase 3. Withdrawn trials never enrolled and are left out.
* **Molecular entity:** the active substance, whatever its brand, sponsor code, dose or salt, resolved to its FDA UNII substance where one exists. Biosimilars fold into their reference entity.
* **Disease:** the MONDO term for the condition the trial treats, without line, stage, biomarker or age qualifiers.
* **Program:** one entity developed for one disease. An entity belongs to a program only in trials where it is the investigational agent, not a comparator or background therapy. Each industry trial's purpose is classified first: bioequivalence, formulation, food-effect, interaction and other product-support studies ({{section1.purpose.product_support|int}} trials) belong to no program; a first-in-human study or a basket across several diseases counts as Phase 1 only for the program the sponsor pursued next.
* **Phase entry and outcome:** a program enters a phase with its first industry-sponsored trial of that phase. It *advanced* when a later-phase trial in its disease started (any sponsor) or the FDA approved the entity for the disease; it is *suspended* when none of its trials has been active within {{section1.lag_months}} months of the snapshot ({{section1.snapshot}}); otherwise it is still running and *censored*. Programs whose entity was already approved for the disease are lifecycle programs and are left out. As in BIO's report, each phase's success rate is advanced ÷ (advanced + suspended), and LOA is their product.
* **Approval:** FDA approval of the entity for the program's disease, a subtype or population of it, or a broader approved class that includes it, judged from the dated approval letters, original-approval dates and labels of every application of the entity (CDER and CBER).

{{section1.scale.cohort_programs|int}} programs of {{section1.scale.cohort_entities|int}} entities entered at least one phase in 2015–2025.

### Phase transitions

{{TRANSITIONS_TABLE}}

{{SECTION1_TRANSITIONS}}

{{SENSITIVITY_TABLE}}

### Why programs stop

Each suspended program takes one reason from the industry trials of the phase it stopped in, in this order: an efficacy reason stated by the sponsor, a primary endpoint missed in posted or published results, a safety signal, a pharmacokinetic or formulation problem, an explicit business or strategic reason, a bare "sponsor decision", an enrollment, operational or regulatory reason, a positive primary readout without advancement, and finally no reason at all.

{{FAILURE_TABLE}}

![Why suspended programs stopped, by phase](report/output/figures/failure_modes_by_phase.png)

{{SECTION1_FAILURES}}

### By disease area and modality

{{AREA_TABLE}}

{{MODALITY_TABLE}}

![Likelihood of approval by disease area](report/output/figures/loa_by_area.png)

![Likelihood of approval by modality](report/output/figures/loa_by_modality.png)

{{SECTION1_STRATA}}
