"""How closely an evidence disease matches a program's disease, on MONDO.

Information content is intrinsic (Seco et al. 2004): IC(t) = 1 - log(1 + d(t)) / log(N),
with d(t) the number of descendants and N the number of terms. The Lin
similarity of two terms is 2 * IC(MICA) / (IC(a) + IC(b)), where MICA is their
most informative common ancestor (a term counts as its own ancestor).
Minikel et al. 2024 count genetic support when trait-indication similarity is
at least 0.8; that is the default threshold here.
"""
from __future__ import annotations

import math
from collections import defaultdict

from report import frame

SIMILARITY_THRESHOLD = 0.8


class Mondo:
    def __init__(self):
        anc = frame.query("SELECT term_id, ancestor_id FROM preclin.ontology_ancestor WHERE ontology = 'MONDO'")
        self.ancestors = defaultdict(set)
        for t, a in anc.itertuples(index=False):
            self.ancestors[t].add(a)
        terms = frame.query("SELECT term_id FROM preclin.ontology_term WHERE ontology = 'MONDO' AND NOT is_obsolete")
        n_desc = defaultdict(int)
        for t, ancs in self.ancestors.items():
            for a in ancs:
                n_desc[a] += 1
        n = len(terms)
        self.ic = {t: 1 - math.log(1 + n_desc.get(t, 0)) / math.log(n) for t in terms.term_id}

    def lin(self, a: str, b: str) -> float:
        if a == b:
            return 1.0
        common = (self.ancestors[a] | {a}) & (self.ancestors[b] | {b})
        if not common:
            return 0.0
        mica = max(self.ic.get(c, 0.0) for c in common)
        denom = self.ic.get(a, 0.0) + self.ic.get(b, 0.0)
        return 2 * mica / denom if denom else 0.0

    def relation(self, evidence: str, program: str) -> str:
        """same, narrower (evidence is a subtype of the program disease), broader, or other."""
        if evidence == program:
            return "same"
        if program in self.ancestors[evidence]:
            return "narrower"
        if evidence in self.ancestors[program]:
            return "broader"
        return "other"

    def matches(self, evidence: str, program: str, threshold: float = SIMILARITY_THRESHOLD) -> bool:
        rel = self.relation(evidence, program)
        return rel in ("same", "narrower") or self.lin(evidence, program) >= threshold
