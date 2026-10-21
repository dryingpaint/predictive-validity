"""Reference values from BIO, Informa and QLS, Clinical Development Success Rates
2011-2020 (Thomas et al. 2021): phase transition success, likelihood of approval
from Phase I, and LOA by disease area and by modality (percent)."""

TRANSITIONS = {1: 52.0, 2: 28.9, 3: 52.4}
LOA = 7.9
LOA_NOVEL = 6.8
AREA_LOA = {"hematology": 23.9, "metabolic": 15.5, "infectious_disease": 13.2, "other": 13.0,
                "ophthalmology": 11.9, "autoimmune": 10.7, "allergy": 10.3, "gastroenterology": 8.3,
                "psychiatry": 7.3, "respiratory": 7.5, "endocrine": 6.6, "neurology": 5.9,
                "cardiovascular": 4.8, "oncology": 5.3, "urology": 3.6}
MODALITY_LOA = {"car_t": 17.3, "sirna_rnai": 13.5, "monoclonal_antibody": 12.1, "antibody_drug_conjugate": 10.8,
                    "gene_therapy": 10.0, "vaccine": 9.7, "protein": 9.4, "peptide": 8.0, "small_molecule": 7.5,
                    "antisense_oligonucleotide": 5.2}
