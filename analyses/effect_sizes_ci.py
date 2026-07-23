"""Compute bootstrap 95% CIs for effect sizes, write to preclin.effect_size_snapshot.

SQL gives us the 2x2 counts and point OR (in v_effect_sizes_2x2). Bootstrap CIs
need repeated sampling, so we do that in Python and store back to a snapshot table.

Rerun after every ingest.
"""

import os
import random
import psycopg2
from collections import Counter
from psycopg2.extras import execute_values

random.seed(42)

DDL = """
CREATE TABLE IF NOT EXISTS preclin.effect_size_snapshot (
  snapshot_id      BIGSERIAL PRIMARY KEY,
  cohort           TEXT NOT NULL,       -- 'tight' | 'broad'
  dimension        TEXT NOT NULL,
  n_covered        INTEGER,
  high_approved    INTEGER,
  high_failed      INTEGER,
  low_approved     INTEGER,
  low_failed       INTEGER,
  odds_ratio       DOUBLE PRECISION,
  ci_lo            DOUBLE PRECISION,
  ci_hi            DOUBLE PRECISION,
  computed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (cohort, dimension, computed_at)
);
"""


def or_boot(ey, en, uy, un, n=500):
    def of(a, b, c, d):
        if a == 0 or b == 0 or c == 0 or d == 0:
            a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
        return (a * d) / (b * c)
    pt = of(ey, en, uy, un)
    total = ey + en + uy + un
    if total == 0:
        return pt, None, None
    cases = ([("e", 1)] * ey + [("e", 0)] * en +
             [("u", 1)] * uy + [("u", 0)] * un)
    ors = []
    for _ in range(n):
        s = [cases[random.randrange(len(cases))] for _ in range(len(cases))]
        c = Counter(s)
        ors.append(of(c[("e", 1)], c[("e", 0)], c[("u", 1)], c[("u", 0)]))
    ors.sort()
    return pt, ors[int(n * 0.025)], ors[int(n * 0.975)]


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute(DDL)
    conn.commit()

    cur.execute("""
        SELECT cohort, dimension, high_approved, high_failed, low_approved, low_failed
        FROM preclin.v_effect_sizes_2x2
        ORDER BY cohort, dimension
    """)
    rows = cur.fetchall()

    snap = []
    for cohort, dim, ha, hf, la_, lf in rows:
        n = (ha or 0) + (hf or 0) + (la_ or 0) + (lf or 0)
        if n < 20:
            snap.append((cohort, dim, n, ha, hf, la_, lf, None, None, None))
            continue
        pt, lo, hi = or_boot(ha or 0, hf or 0, la_ or 0, lf or 0)
        snap.append((cohort, dim, n, ha, hf, la_, lf, pt, lo, hi))
        print(f"  {cohort:6} {dim:38} OR={pt:.2f} [{lo:.2f}, {hi:.2f}]  n={n}")

    execute_values(cur, """
        INSERT INTO preclin.effect_size_snapshot
          (cohort, dimension, n_covered, high_approved, high_failed,
           low_approved, low_failed, odds_ratio, ci_lo, ci_hi)
        VALUES %s
    """, snap)
    conn.commit()
    print(f"\nWrote {len(snap)} rows to preclin.effect_size_snapshot")


if __name__ == "__main__":
    main()
