"""Disease burden for the atlas's tracked diseases: global DALYs in 2021 from the WHO Global Health Estimates,
mapped by hand to every disease that has a tracked tile (issue #76).

    .venv/bin/python analyses/model-system-atlas/burden.py

Source: WHO Global Health Estimates 2021, "Global DALYs by cause, 2000-2023", both sexes, all ages, the
workbook daly_global_2026-09-30.xlsx under
https://www.who.int/data/gho/data/themes/mortality-and-global-health-estimates/global-health-estimates-leading-causes-of-dalys
(downloaded 2026-11-05). lists/who_ghe_2021_global_dalys.csv is its "Global 2021" sheet as one row per
cause (code, depth, cause, dalys_2021). WHO publishes the GHE under CC BY-NC-SA 3.0 IGO.

Each atlas disease is mapped to one or more WHO causes with a match grade: `exact` (the cause is the
disease), `broader` (the cause contains the disease and others; the DALYs overstate it), `shared`
(another atlas disease maps to the same cause and holds it for ranking), or `none` (no WHO cause is
specific enough; the disease sits inside an aggregate). The ranking uses exact and broader matches.
Writes lists/burden.csv: one row per tracked disease, with the causes, the grade, the DALYs, the rank
among ranked diseases, and the disease's tracked tiles. Read-only.
"""
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LISTS = os.path.join(HERE, "lists")

# mondo_id -> (match, [WHO cause codes], note)
MAP = {
    "MONDO:0005148": ("broader", [800], "Diabetes mellitus; type 2 is about nine tenths of it"),
    "MONDO:0005147": ("shared", [800], "within Diabetes mellitus, held by type 2 diabetes"),
    "MONDO:0005002": ("exact", [1180], ""),
    "MONDO:0005109": ("exact", [100], ""),
    "MONDO:0005233": ("broader", [680], "Trachea, bronchus, lung cancers; NSCLC is about 85% of lung cancer"),
    "MONDO:0008433": ("shared", [680], "within lung cancers, held by NSCLC"),
    "MONDO:0005277": ("exact", [990], ""),
    "MONDO:0004975": ("broader", [950], "Alzheimer disease and other dementias"),
    "MONDO:0004979": ("exact", [1190], ""),
    "MONDO:0007254": ("exact", [700], ""),
    "MONDO:0005178": ("exact", [1360], ""),
    "MONDO:0005575": ("exact", [650], "Colon and rectum cancers"),
    "MONDO:0005366": ("exact", [1231, 661], "cirrhosis and liver cancer secondary to hepatitis B; acute hepatitis B excluded"),
    "MONDO:0007256": ("broader", [660], "Liver cancer; hepatocellular carcinoma is most of it"),
    "MONDO:0005090": ("exact", [850], ""),
    "MONDO:0001056": ("exact", [640], "Stomach cancer"),
    "MONDO:0005231": ("exact", [200, 1232, 662], "acute hepatitis C, cirrhosis and liver cancer secondary to hepatitis C"),
    "MONDO:0005016": ("exact", [1272], "Chronic kidney disease due to diabetes"),
    "MONDO:0018874": ("broader", [770], "Leukaemia, all types"),
    "MONDO:0009831": ("exact", [670], "Pancreas cancer"),
    "MONDO:0007027": ("broader", [1234], "Other liver cirrhosis, which holds MASH among other causes"),
    "MONDO:0008315": ("exact", [740], ""),
    "MONDO:0018906": ("broader", [762], "Non-Hodgkin lymphoma, all subtypes"),
    "MONDO:0008170": ("exact", [730], "Ovary cancer"),
    "MONDO:0008383": ("exact", [1350], ""),
    "MONDO:0009693": ("exact", [763], "Multiple myeloma"),
    "MONDO:0005105": ("exact", [691], "Malignant skin melanoma"),
    "MONDO:0005011": ("broader", [1244], "Inflammatory bowel disease, with ulcerative colitis"),
    "MONDO:0005101": ("shared", [1244], "within Inflammatory bowel disease, held by Crohn disease"),
    "MONDO:0005338": ("broader", [1030], "Glaucoma, all forms"),
    "MONDO:0005542": ("broader", [1130], "Ischaemic heart disease; acute coronary syndrome is its acute presentation"),
    "MONDO:0005301": ("exact", [980], ""),
    "MONDO:0002974": ("exact", [710], "Cervix uteri cancer"),
    "MONDO:0004952": ("exact", [761], ""),
    "MONDO:0005086": ("broader", [745], "Kidney cancer; renal cell carcinoma is about nine tenths of it"),
    "MONDO:0005150": ("exact", [1060], "Macular degeneration"),
    "MONDO:0005393": ("exact", [1370], ""),
    "MONDO:0003864": ("shared", [770], "within Leukaemia, held by acute myeloid leukemia"),
    "MONDO:0004967": ("shared", [770], "within Leukaemia, held by acute myeloid leukemia"),
    "MONDO:0011996": ("shared", [770], "within Leukaemia, held by acute myeloid leukemia"),
    "MONDO:0015759": ("shared", [762], "within Non-Hodgkin lymphoma, held by follicular lymphoma"),
    "MONDO:0017604": ("shared", [762], "within Non-Hodgkin lymphoma, held by follicular lymphoma"),
    "MONDO:0018876": ("shared", [762], "within Non-Hodgkin lymphoma, held by follicular lymphoma"),
    "MONDO:0018905": ("shared", [762], "within Non-Hodgkin lymphoma, held by follicular lymphoma"),
    "MONDO:0019472": ("shared", [762], "within Non-Hodgkin lymphoma, held by follicular lymphoma"),
    "MONDO:0968974": ("shared", [762], "within Non-Hodgkin lymphoma, held by follicular lymphoma"),
    "MONDO:0100280": ("shared", [762], "within Non-Hodgkin lymphoma, held by follicular lymphoma"),
    # no WHO cause is specific enough
    "MONDO:0011786": ("none", [], "allergic rhinitis has no WHO cause"),
    "MONDO:0005271": ("none", [], "allergic disease has no WHO cause"),
    "MONDO:0005083": ("none", [], "only the Skin diseases aggregate"),
    "MONDO:0004980": ("none", [], "only the Skin diseases aggregate"),
    "MONDO:0005133": ("none", [], "only the Gynecological diseases aggregate"),
    "MONDO:0006964": ("none", [], "a complication of chronic kidney disease, not a WHO cause"),
    "MONDO:0005388": ("none", [], "inside Other liver cirrhosis, not separable"),
    "MONDO:0007186": ("none", [], "only the Other digestive diseases aggregate"),
    "MONDO:0010602": ("none", [], "inside Other endocrine, blood and immune disorders"),
    "MONDO:0010604": ("none", [], "inside Other endocrine, blood and immune disorders"),
    "MONDO:0100244": ("none", [], "inside Other haemoglobinopathies and haemolytic anaemias"),
    "MONDO:0021187": ("none", [], "a risk factor in the WHO estimates, not a cause"),
    "MONDO:0018881": ("none", [], "inside Other malignant neoplasms"),
    "MONDO:0004728": ("none", [], "inside Other vision loss"),
    "MONDO:0006733": ("none", [], "no WHO cause"),
    "MONDO:0013600": ("none", [], "no WHO cause"),
    "MONDO:0009061": ("none", [], "inside Other respiratory diseases"),
    "MONDO:0018301": ("none", [], "inside Other urinary diseases"),
    "MONDO:0007915": ("none", [], "inside Other musculoskeletal disorders"),
    "MONDO:0010030": ("none", [], "inside Other musculoskeletal disorders"),
    "MONDO:0005152": ("none", [], "inside Other endocrine, blood and immune disorders"),
    "MONDO:0006909": ("none", [], "inside Other endocrine, blood and immune disorders"),
    "MONDO:0001586": ("none", [], "inside Other endocrine, blood and immune disorders"),
    "MONDO:0009290": ("none", [], "inside Other endocrine, blood and immune disorders"),
    "MONDO:0009656": ("none", [], "inside Other endocrine, blood and immune disorders"),
    "MONDO:0010526": ("none", [], "inside Other endocrine, blood and immune disorders"),
    "MONDO:0001684": ("none", [], "only the Other digestive diseases aggregate"),
    "MONDO:0100187": ("none", [], "a side effect of opioid treatment, not a WHO cause"),
    "MONDO:0007571": ("none", [], "inside Other neurological conditions"),
    "MONDO:0007739": ("none", [], "inside Other neurological conditions"),
    "MONDO:0010679": ("none", [], "inside Other neurological conditions"),
    "MONDO:0010383": ("none", [], "inside Other chromosomal anomalies"),
    "MONDO:0011719": ("none", [], "inside Other malignant neoplasms"),
    "MONDO:0044903": ("none", [], "inside Other neoplasms"),
    "MONDO:0019200": ("none", [], "inside Other vision loss"),
    "MONDO:0005298": ("none", [], "a risk factor in the WHO estimates (low bone mineral density), not a cause"),
    "MONDO:0009179": ("none", [], "only the Skin diseases aggregate"),
    "MONDO:0015924": ("none", [], "inside Other circulatory diseases"),
}


def main() -> None:
    who = pd.read_csv(os.path.join(LISTS, "who_ghe_2021_global_dalys.csv")).set_index("code")
    tiles = pd.read_csv(os.path.join(LISTS, "named_contexts.csv"))
    diseases = tiles.groupby(["area", "mondo_id", "label"]).size().reset_index(name="tiles")
    missing = set(diseases.mondo_id) - set(MAP)
    if missing:
        raise SystemExit(f"unmapped tracked diseases: {sorted(missing)}")
    rows = []
    for d in diseases.itertuples():
        match, codes, note = MAP[d.mondo_id]
        rows.append({"area": d.area, "mondo_id": d.mondo_id, "disease": d.label, "tiles": d.tiles, "match": match,
                     "who_codes": ";".join(map(str, codes)), "who_causes": "; ".join(who.cause[c] for c in codes),
                     "dalys_2021": sum(who.dalys_2021[c] for c in codes) if codes else None, "note": note})
    out = pd.DataFrame(rows)
    ranked = out[out.match.isin(["exact", "broader"])].sort_values("dalys_2021", ascending=False)
    out["rank"] = out.mondo_id.map({m: i + 1 for i, m in enumerate(ranked.mondo_id)})
    out = out.sort_values(["rank", "area", "disease"], na_position="last")
    out["rank"] = out["rank"].astype("Int64")
    out.to_csv(os.path.join(LISTS, "burden.csv"), index=False)
    n = out.match.value_counts()
    print(f"{len(out)} tracked diseases: {n.get('exact', 0)} exact, {n.get('broader', 0)} broader, {n.get('shared', 0)} shared, {n.get('none', 0)} without a WHO cause")
    print(out[out["rank"].notna()][["rank", "disease", "tiles", "match", "dalys_2021"]].assign(dalys_2021=lambda x: (x.dalys_2021 / 1e6).round(1)).to_string(index=False))
    top = ranked.head(15)
    print(f"\ntop 15 by DALYs: {int(top.tiles.sum())} tiles; top 10: {int(ranked.head(10).tiles.sum())} tiles")


if __name__ == "__main__":
    main()
