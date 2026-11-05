"""How closely an evidence disease matches a program's disease, on MONDO.

Information content is intrinsic (Seco et al. 2004): IC(t) = 1 - log(1 + d(t)) / log(N),
with d(t) the number of descendants and N the number of terms. The Lin
similarity of two terms is 2 * IC(MICA) / (IC(a) + IC(b)), where MICA is their
most informative common ancestor (a term counts as its own ancestor).
Minikel et al. 2024 count genetic support when trait-indication similarity is
at least 0.8; that is the threshold here.
"""
from __future__ import annotations

import math
from collections import defaultdict
from functools import cache

from report import frame

SIMILARITY_THRESHOLD = 0.8


@cache  # loaded once per build; every Mondo shares the tables, which callers only read
def mondo_tables() -> tuple[dict, dict]:
    anc = frame.query("SELECT term_id, ancestor_id FROM preclin.ontology_ancestor WHERE ontology = 'MONDO'")
    ancestors = defaultdict(set)
    for t, a in anc.itertuples(index=False):
        ancestors[t].add(a)
    terms = frame.query("SELECT term_id FROM preclin.ontology_term WHERE ontology = 'MONDO' AND NOT is_obsolete")
    n_desc = defaultdict(int)
    for t, ancs in ancestors.items():
        for a in ancs:
            n_desc[a] += 1
    n = len(terms)
    ic = {t: 1 - math.log(1 + n_desc.get(t, 0)) / math.log(n) for t in terms.term_id}
    return ancestors, ic


class Mondo:
    _lin: dict = {}  # (a, b) -> Lin similarity; every Mondo shares mondo_tables, so one memo serves them all

    def __init__(self):
        self.ancestors, self.ic = mondo_tables()

    def lin(self, a: str, b: str) -> float:
        if a == b:
            return 1.0
        key = (a, b) if a < b else (b, a)
        if key not in Mondo._lin:
            Mondo._lin[key] = self._lin_uncached(a, b)
        return Mondo._lin[key]

    def _lin_uncached(self, a: str, b: str) -> float:
        common = (self.ancestors[a] | {a}) & (self.ancestors[b] | {b})
        if not common:
            return 0.0
        mica = max(self.ic.get(c, 0.0) for c in common)
        denom = self.ic.get(a, 0.0) + self.ic.get(b, 0.0)
        return 2 * mica / denom if denom else 0.0

    def matches(self, evidence: str, program: str) -> tuple[bool, bool]:
        """(match, close): close is Lin similarity >= SIMILARITY_THRESHOLD; a match
        is also the same term or a subtype of the program disease."""
        close = self.lin(evidence, program) >= SIMILARITY_THRESHOLD
        return close or program in self.ancestors[evidence], close
