"""Source-aware alias classification and conservative literature-search aliases.

Aliases remain raw, source-versioned facts in ``pv_core.entity_alias``.  This
module defines the smaller projection that is safe to use for retrieval.  In
particular, ChEMBL classification labels and generic ``OTHER`` synonyms are
retained but are not silently promoted into search terms.
"""
from __future__ import annotations

import re
from typing import Any, Iterable


CHEMBL_ASSET_ALIAS_KIND = {
    "INN": "inn",
    "INN_SPANISH": "inn",
    "INN_FRENCH": "inn",
    "BAN": "ban",
    "USAN": "usan",
    "FDA": "fda_name",
    "USP": "usp_name",
    "EMA": "ema_name",
    "JAN": "jan_name",
    "DCF": "dcf_name",
    "BNF": "bnf_name",
    "ATC": "atc_name",
    "TRADE_NAME": "trade_name",
    "RESEARCH_CODE": "research_code",
    "MERCK_INDEX": "merck_index_name",
    "OTHER": "other_name",
}

CHEMBL_ALIAS_LANGUAGE = {
    "INN_SPANISH": "es",
    "INN_FRENCH": "fr",
}

# This is deliberately narrower than the aliases we preserve.  Chemical
# descriptions, ontology/class labels and unspecified OTHER names can be useful
# for review but are unsafe automatic retrieval terms.
ASSET_SEARCH_ALIAS_KINDS = (
    "preferred",
    "chembl_preferred_name",
    "pubchem_title",
    "inn",
    "ban",
    "usan",
    "fda_name",
    "usp_name",
    "ema_name",
    "jan_name",
    "dcf_name",
    "bnf_name",
    "atc_name",
    "trade_name",
    "research_code",
)

TARGET_SEARCH_ALIAS_KINDS = (
    "approved_symbol",
    "approved_name",
    "protein_name",
    "chembl_preferred_name",
    "gene_symbol",
)


def classify_chembl_asset_alias(row: dict[str, Any]) -> tuple[str, bool, str]:
    """Return ``(alias_kind, is_ambiguous, language)`` for a ChEMBL synonym."""
    text = str(row.get("molecule_synonym") or "").strip()
    source_kind = str(row.get("syn_type") or "OTHER").upper()
    kind = CHEMBL_ASSET_ALIAS_KIND.get(source_kind, "other_name")
    language = CHEMBL_ALIAS_LANGUAGE.get(source_kind, "en")

    # ChEMBL sometimes puts strings such as "ATC CODE G03 GA GONADOTROPINS"
    # in RESEARCH_CODE.  That is a class annotation, not an alias for one drug.
    classification_label = bool(re.match(r"^ATC\s+CODE\b", text, re.IGNORECASE))
    if classification_label:
        kind = "classification_label"
    ambiguous = classification_label or len(re.sub(r"\W+", "", text)) < 3
    return kind, ambiguous, language


def _unique_casefold(values: Iterable[str | None]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        clean = value.strip()
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            output.append(clean)
    return output


def search_aliases(
    cur: Any,
    entity_id: Any,
    entity_type: str,
    alias_kinds: tuple[str, ...],
    fallbacks: Iterable[str | None] = (),
) -> list[str]:
    """Return non-ambiguous, collision-free aliases in deterministic order.

    Collision detection is entity-type-specific.  If the same normalized term
    belongs to two assets (or two targets), it is preserved in the ledger but
    is not automatically used as a literature query term.
    """
    cur.execute(
        """
        SELECT DISTINCT ea.alias_text,ea.alias_normalized,ea.alias_kind
        FROM pv_core.entity_alias ea
        WHERE ea.entity_id=%s
          AND ea.entity_type=%s
          AND ea.alias_kind=ANY(%s)
          AND ea.is_ambiguous=false
          AND NOT EXISTS (
            SELECT 1
            FROM pv_core.entity_alias collision
            WHERE collision.entity_type=ea.entity_type
              AND collision.alias_normalized=ea.alias_normalized
              AND collision.entity_id<>ea.entity_id
              AND collision.alias_kind=ANY(%s)
              AND collision.is_ambiguous=false
          )
        ORDER BY ea.alias_kind,ea.alias_text
        """,
        (entity_id, entity_type, list(alias_kinds), list(alias_kinds)),
    )
    return _unique_casefold([row[0] for row in cur.fetchall()] + list(fallbacks))


def asset_search_aliases(
    cur: Any, entity_id: Any, fallbacks: Iterable[str | None] = ()
) -> list[str]:
    aliases = search_aliases(
        cur, entity_id, "asset", ASSET_SEARCH_ALIAS_KINDS, fallbacks
    )
    # Pharmacopeial impurity/reference-standard labels are preserved as source
    # aliases, but searching them as if they were therapeutic names introduces
    # unrelated chemistry and clinical papers (for example, edaravone's
    # "Antipyrine related compound A").
    return [
        alias for alias in aliases
        if not re.search(r"\brelated[\s-]+compound\b", alias, re.IGNORECASE)
    ]


def target_search_aliases(
    cur: Any, entity_id: Any, fallbacks: Iterable[str | None] = ()
) -> list[str]:
    return search_aliases(cur, entity_id, "target", TARGET_SEARCH_ALIAS_KINDS, fallbacks)
