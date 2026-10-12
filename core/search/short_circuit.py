"""Indexed-vocabulary short-circuit for provably empty plain/boolean AND queries."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.criteria.sql import parse_boolean_expression
from core.search.words import normalize_search_token, resolve_word_ids_for_terms

_REGEX_LIKE = re.compile(
    r"[\[\]\(\)\|\?\*\+\{\\]|\\b|\(\?[a-zA-Z]",
)


def looks_like_regex_pattern(query: str) -> bool:
    """Heuristic: do not treat regex/PCRE-style queries as indexed vocabulary."""
    text = str(query or "").strip()
    if not text:
        return False
    return bool(_REGEX_LIKE.search(text))


def collect_expression_terms(expression: Tuple) -> List[str]:
    kind = expression[0]
    if kind == "term":
        return [str(expression[1])]
    if kind in ("and", "or"):
        return collect_expression_terms(expression[1]) + collect_expression_terms(expression[2])
    if kind == "not":
        return collect_expression_terms(expression[1])
    return []


def indexed_expression_provably_empty(expression: Tuple, id_map: Dict[str, int]) -> bool:
    """True when the boolean tree cannot match indexed vocabulary (AND/OR rules)."""
    kind = expression[0]
    if kind == "term":
        return normalize_search_token(expression[1]) not in id_map
    if kind == "and":
        return indexed_expression_provably_empty(expression[1], id_map) or indexed_expression_provably_empty(
            expression[2], id_map
        )
    if kind == "or":
        return indexed_expression_provably_empty(expression[1], id_map) and indexed_expression_provably_empty(
            expression[2], id_map
        )
    if kind == "not":
        return False
    return False


def unresolved_mandatory_term_count(terms: Sequence[str], id_map: Dict[str, int]) -> int:
    count = 0
    for term in terms:
        key = normalize_search_token(term)
        if key and key not in id_map:
            count += 1
    return count


def assess_indexed_vocabulary_short_circuit(
    *,
    query: str,
    intent: Dict[str, Any],
    case_sensitive: bool,
    whole_word: bool,
    expansion_terms: Sequence[str],
    cursor: Any,
) -> Optional[Dict[str, Any]]:
    """
    Return telemetry dict when the query is provably empty on indexed vocabulary.

    Plain space-separated terms use AND semantics. Boolean OR only short-circuits
    when every branch is provably empty.
    """
    if case_sensitive or whole_word or expansion_terms:
        return None
    if intent.get("has_quotes"):
        return None
    if looks_like_regex_pattern(query):
        return None

    text = str(query or "").strip()
    if len(text) < 2:
        return None

    if intent.get("has_operators") or "(" in text or ")" in text:
        expression = parse_boolean_expression(text)
        if expression is None:
            return None
        terms = collect_expression_terms(expression)
        if not terms:
            return None
        id_map = resolve_word_ids_for_terms(terms, cursor=cursor)
        if not indexed_expression_provably_empty(expression, id_map):
            return None
        missing = unresolved_mandatory_term_count(terms, id_map)
        return {
            "short_circuit": True,
            "short_circuit_reason": "mandatory_term_unresolved",
            "unresolved_term_count": missing,
        }

    if intent.get("has_operators"):
        return None

    search_terms = [t.strip() for t in text.split() if t.strip()]
    if not search_terms:
        return None
    id_map = resolve_word_ids_for_terms(search_terms, cursor=cursor)
    missing = unresolved_mandatory_term_count(search_terms, id_map)
    if missing <= 0:
        return None
    return {
        "short_circuit": True,
        "short_circuit_reason": "mandatory_term_unresolved",
        "unresolved_term_count": missing,
    }
