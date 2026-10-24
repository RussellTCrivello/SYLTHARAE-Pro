"""Translation memory: a local SQLite file, outside PostgreSQL, by design.

Why not a table
===============

The schema is frozen, and for a good reason: most of what the system needs can
be derived from the rows it already stores. Translation memory is the exception
- a corrected translation is *not* derivable from anything - so it lives in its
own file, under ``APP_DATA_DIR``, the way ``map_data/registry.db`` holds the
offline map registry. Nothing in PostgreSQL changes, nothing in
``database/migrations`` changes, and a translation memory can be copied between
installations (or deleted) with one file operation.

What a row records
==================

``origin`` is ``engine`` (a machine translation) or ``user`` (an analyst's
correction). Every row also records the engine id and version that produced it,
so a translation can always be attributed, and a correction keeps
``actor`` - the username that made it.

The rules this module enforces
==============================

1. an exact match is reused, and counts its uses;
2. a user correction is final: :meth:`TranslationMemory.remember` will not
   overwrite a ``user`` row with an ``engine`` one, however many times the
   engine is asked again;
3. fuzzy matches are a *suggestion* (:meth:`suggest`), never a translation: a
   near-identical sentence is offered to the analyst, and
   :meth:`TranslationMemory.lookup` never returns one.
"""

from __future__ import annotations

import difflib
import hashlib
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

__all__ = ["TranslationMemory", "default_memory_path"]

_DB_NAME = "translation_memory.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tm_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_lang TEXT NOT NULL,
    target_lang TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    source_text TEXT NOT NULL,
    target_text TEXT NOT NULL,
    origin TEXT NOT NULL CHECK (origin IN ('engine', 'user', 'imported')),
    engine TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    actor TEXT,
    uses INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (source_lang, target_lang, source_hash)
);
CREATE INDEX IF NOT EXISTS idx_tm_entries_pair ON tm_entries (source_lang, target_lang);
CREATE TABLE IF NOT EXISTS tm_glossary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_lang TEXT NOT NULL,
    target_lang TEXT NOT NULL,
    term TEXT NOT NULL,
    translation TEXT NOT NULL,
    actor TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (source_lang, target_lang, term)
);
"""


def default_memory_path() -> Path:
    """``APP_DATA_DIR/translation/translation_memory.db`` (created on demand)."""
    from core.app_paths import get_data_root

    return Path(get_data_root()) / "translation" / _DB_NAME


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(text: str) -> str:
    return hashlib.sha256(" ".join((text or "").split()).encode("utf-8")).hexdigest()


class TranslationMemory:
    """The translation memory file. Cheap to construct; it opens per call."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path is not None else default_memory_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    # -- plumbing ----------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    # -- translations ------------------------------------------------------
    def remember(self, *, source_lang: str, target_lang: str, source_text: str,
                 target_text: str, origin: str, engine: str, engine_version: str,
                 actor: Optional[str] = None) -> Dict:
        """Store (or refresh) one translation.

        An ``engine`` write never replaces a ``user`` row - the analyst's
        correction is the more authoritative record.
        """
        source_hash = _hash(source_text)
        now = _now()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT origin FROM tm_entries WHERE source_lang = ? AND"
                " target_lang = ? AND source_hash = ?",
                (source_lang, target_lang, source_hash)).fetchone()
            if existing is not None:
                stored_origin = existing["origin"]
                if stored_origin == "user" and origin != "user":
                    return self._row(conn, source_lang, target_lang, source_hash)
                conn.execute(
                    "UPDATE tm_entries SET target_text = ?, origin = ?, engine = ?,"
                    " engine_version = ?, actor = ?, updated_at = ?"
                    " WHERE source_lang = ? AND target_lang = ? AND source_hash = ?",
                    (target_text, origin, engine, engine_version,
                     actor if origin == "user" else None, now,
                     source_lang, target_lang, source_hash))
            else:
                conn.execute(
                    "INSERT INTO tm_entries (source_lang, target_lang, source_hash,"
                    " source_text, target_text, origin, engine, engine_version,"
                    " actor, uses, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                    (source_lang, target_lang, source_hash,
                     " ".join(source_text.split()), target_text, origin, engine,
                     engine_version, actor if origin == "user" else None, now, now))
            conn.commit()
            return self._row(conn, source_lang, target_lang, source_hash)

    def correct(self, *, source_lang: str, target_lang: str, source_text: str,
                target_text: str, actor: Optional[str] = None) -> Dict:
        """Record an analyst's correction - always ``origin = 'user'``."""
        return self.remember(source_lang=source_lang, target_lang=target_lang,
                             source_text=source_text, target_text=target_text,
                             origin="user", engine="user", engine_version="user",
                             actor=actor)

    def lookup(self, *, source_lang: str, target_lang: str,
               source_text: str) -> Optional[Dict]:
        """The stored translation for this exact sentence, or ``None``."""
        source_hash = _hash(source_text)
        with self._connect() as conn:
            row = self._row(conn, source_lang, target_lang, source_hash)
            if row is None:
                return None
            conn.execute(
                "UPDATE tm_entries SET uses = uses + 1 WHERE id = ?", (row["id"],))
            conn.commit()
            row["uses"] += 1
            return row

    def suggest(self, *, source_lang: str, target_lang: str, source_text: str,
                limit: int = 5, threshold: float = 0.6) -> List[Dict]:
        """Fuzzy matches for *source_text* - suggestions, never translations."""
        wanted = " ".join((source_text or "").split())
        if not wanted:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tm_entries WHERE source_lang = ? AND target_lang = ?",
                (source_lang, target_lang)).fetchall()
        scored = []
        for row in rows:
            score = difflib.SequenceMatcher(
                None, wanted, row["source_text"]).ratio()
            if score >= threshold and row["source_text"] != wanted:
                entry = dict(row)
                entry["score"] = round(score, 4)
                scored.append(entry)
        scored.sort(key=lambda entry: entry["score"], reverse=True)
        return scored[:limit]

    def _row(self, conn, source_lang: str, target_lang: str,
             source_hash: str) -> Optional[Dict]:
        row = conn.execute(
            "SELECT * FROM tm_entries WHERE source_lang = ? AND target_lang = ?"
            " AND source_hash = ?", (source_lang, target_lang, source_hash)).fetchone()
        return dict(row) if row is not None else None

    # -- glossary ----------------------------------------------------------
    def set_glossary_term(self, *, source_lang: str, target_lang: str, term: str,
                          translation: str, actor: Optional[str] = None) -> Dict:
        now = _now()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO tm_glossary (source_lang, target_lang, term,"
                " translation, actor, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT (source_lang, target_lang, term) DO UPDATE SET"
                " translation = excluded.translation, actor = excluded.actor,"
                " updated_at = excluded.updated_at",
                (source_lang, target_lang, term, translation, actor, now, now))
            conn.commit()
        return {"term": term, "translation": translation}

    def glossary(self, *, source_lang: str, target_lang: str) -> Dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT term, translation FROM tm_glossary WHERE source_lang = ?"
                " AND target_lang = ? ORDER BY term",
                (source_lang, target_lang)).fetchall()
        return {row["term"]: row["translation"] for row in rows}

    def apply_glossary_terms(self, text: str, glossary: Dict[str, str]) -> List[str]:
        """Terms of *glossary* that occur in *text* (case-insensitive words)."""
        found = []
        for term in glossary:
            if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, flags=re.IGNORECASE):
                found.append(term)
        return found

    def apply_glossary(self, text: str, glossary: Dict[str, str]) -> str:
        """Replace every glossary term in *text* with its agreed translation.

        Applied to the *translation*, never to the source: the original is what
        the analyst selected and must come back unchanged.
        """
        result = text
        for term, translation in glossary.items():
            result = re.sub(rf"(?<!\w){re.escape(term)}(?!\w)", translation, result,
                            flags=re.IGNORECASE)
        return result

    # -- reporting ---------------------------------------------------------
    def stats(self) -> Dict:
        with self._connect() as conn:
            total = conn.execute("SELECT count(*) AS n FROM tm_entries").fetchone()["n"]
            user = conn.execute(
                "SELECT count(*) AS n FROM tm_entries WHERE origin = 'user'"
            ).fetchone()["n"]
            glossary = conn.execute(
                "SELECT count(*) AS n FROM tm_glossary").fetchone()["n"]
        return {"entries": total, "corrections": user, "glossary_terms": glossary,
                "path": str(self.path)}
