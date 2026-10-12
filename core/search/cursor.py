"""Keyset (cursor) pagination tokens for stable deep pages."""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, Optional, Tuple  # noqa: F401 — Any used in relevance_cursor payload


def encode_cursor(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token or not str(token).strip():
        return None
    pad = "=" * (-len(token) % 4)
    try:
        raw = base64.urlsafe_b64decode(str(token).strip() + pad)
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except (ValueError, json.JSONDecodeError):
        return None


def relevance_cursor(
    score: float,
    path_id: int,
    sort_order: str = "desc",
    *,
    query_signature: Optional[str] = None,
) -> str:
    payload: Dict[str, Any] = {
        "v": 2,
        "sort": "relevance",
        "order": sort_order,
        "score": score,
        "id": path_id,
    }
    if query_signature:
        payload["sig"] = query_signature
    return encode_cursor(payload)


def parse_relevance_cursor(
    token: Optional[str],
    *,
    expected_signature: Optional[str] = None,
) -> Optional[Tuple[float, int, str]]:
    data = decode_cursor(token)
    if not data or data.get("sort") != "relevance":
        return None
    if expected_signature:
        sig = data.get("sig")
        if not sig or sig != expected_signature:
            return None
    try:
        return float(data["score"]), int(data["id"]), str(data.get("order", "desc"))
    except (KeyError, TypeError, ValueError):
        return None
