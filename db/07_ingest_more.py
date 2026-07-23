"""Third-pass ingest: single-cell expression, GO annotations, remaining tables.

Adds:
- sc_tau_specificity — single-cell tissue Tau (Tabula-Sapiens style; HPA)
- sc_max_cell_type — cell type with highest expression
- sc_max_cell_value — expression value in max cell type
- sc_n_cell_types_expressed — number of cell types with expression > 0
- n_go_bp / n_go_mf / n_go_cc — GO term counts per target
- go_terms — text array of GO terms (for full-text search)
"""

import os
import time
import psycopg2
from psycopg2.extras import execute_values

DB_URL = os.environ["DATABASE_URL"]

NEW_DIMS = [
    ("sc_tau_specificity", "B_mechanistic", "target", "numeric_float",
     "Tau specificity across HPA single-cell (Tabula Sapiens style)"),
    ("sc_max_cell_type", "B_mechanistic", "target", "text",
     "Cell type with highest expression"),
    ("sc_max_cell_value", "B_mechanistic", "target", "numeric_float",
     "Expression value in max cell type"),
    ("sc_n_cell_types_expressed", "B_mechanistic", "target", "count",
     "Number of HPA cell types with expression > 0"),
    ("n_go_biological_process", "B_mechanistic", "target", "count",
     "Number of GO BP terms annotated"),
    ("n_go_molecular_function", "B_mechanistic", "target", "count",
     "Number of GO MF terms annotated"),
    ("n_go_cellular_component", "B_mechanistic", "target", "count",
     "Number of GO CC terms annotated"),
]


def compute_tau(values):
    """Yanai Tau specificity from a list of expression values."""
    if not values:
        return None
    vals = [v for v in values if v is not None and v > 0]
    if len(vals) < 2:
        return None
    m = max(vals)
    if m == 0:
        return None
    return sum(1 - (v / m) for v in vals) / (len(vals) - 1)


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    print("Registering dimensions...")
    for dim, cat, subj, dtype, desc in NEW_DIMS:
        cur.execute("""
            INSERT INTO preclin.evidence_dimension (dimension, category, subject_type, data_type, description)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (dimension) DO UPDATE SET description = EXCLUDED.description
        """, (dim, cat, subj, dtype, desc))
    conn.commit()

    # 1. Single-cell expression Tau + max cell
    print("Computing single-cell Tau (this reads 3M rows)...", flush=True)
    cur.execute("""
        SELECT target_id, cell_type, value
        FROM public.single_cell_expression
        WHERE value IS NOT NULL AND source = 'hpa'
    """)
    by_target = {}
    for tid, ct, v in cur.fetchall():
        by_target.setdefault(tid, []).append((ct, v))

    rows_tau, rows_max, rows_maxval, rows_n = [], [], [], []
    for tid, entries in by_target.items():
        vals = [v for _, v in entries]
        tau = compute_tau(vals)
        if tau is not None:
            rows_tau.append(("target", tid, None, "sc_tau_specificity", "B_mechanistic",
                             float(tau), None, None,
                             "hpa_single_cell", "2026", None, None, "script:07_ingest_more"))
        max_ct, max_v = max(entries, key=lambda x: (x[1] or 0))
        rows_max.append(("target", tid, None, "sc_max_cell_type", "B_mechanistic",
                         None, max_ct[:200], None,
                         "hpa_single_cell", "2026", None, None, "script:07_ingest_more"))
        rows_maxval.append(("target", tid, None, "sc_max_cell_value", "B_mechanistic",
                            float(max_v or 0), None, None,
                            "hpa_single_cell", "2026", None, None, "script:07_ingest_more"))
        n_expr = sum(1 for _, v in entries if v and v > 0)
        rows_n.append(("target", tid, None, "sc_n_cell_types_expressed", "B_mechanistic",
                       float(n_expr), None, None,
                       "hpa_single_cell", "2026", None, None, "script:07_ingest_more"))

    def flush(rows, label):
        if not rows:
            return
        execute_values(cur, """
            INSERT INTO preclin.evidence_score
              (subject_type, subject_id, subject_id2, dimension, category,
               value_numeric, value_text, value_boolean, source, source_version,
               confidence, citation_pmids, extracted_by)
            VALUES %s
            ON CONFLICT (subject_type, subject_id, subject_id2, dimension, source, source_version)
            DO UPDATE SET
              value_numeric = EXCLUDED.value_numeric,
              value_text = EXCLUDED.value_text,
              extracted_at = now()
        """, rows, page_size=2000)
        conn.commit()
        print(f"  {label}: {len(rows)}")

    flush(rows_tau, "sc_tau_specificity")
    flush(rows_max, "sc_max_cell_type")
    flush(rows_maxval, "sc_max_cell_value")
    flush(rows_n, "sc_n_cell_types_expressed")

    # 2. GO term counts per category
    print("Ingesting GO annotations...", flush=True)
    for namespace, dim in [("biological_process", "n_go_biological_process"),
                          ("molecular_function", "n_go_molecular_function"),
                          ("cellular_component", "n_go_cellular_component")]:
        cur.execute("""
            SELECT gg.target_id, count(DISTINCT gt.go_id)
            FROM public.gene_go gg
            JOIN public.go_terms gt ON gt.go_id = gg.go_id
            WHERE gt.namespace = %s
            GROUP BY gg.target_id
        """, (namespace,))
        data = cur.fetchall()
        rows = [("target", tid, None, dim, "B_mechanistic",
                 float(n), None, None,
                 "gene_ontology", "2026", None, None, "script:07_ingest_more")
                for tid, n in data]
        flush(rows, dim)

    # Log
    cur.execute("""
        INSERT INTO preclin.ingest_log (source_file, target_table, rows_inserted, finished_at, status)
        VALUES ('public.single_cell_expression + gene_go', 'preclin.evidence_score', %s, now(), 'ok')
    """, (len(rows_tau) + len(rows_max) + len(rows_maxval) + len(rows_n),))
    conn.commit()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
