#!/usr/bin/env python3
"""Make the category workbook the source of truth for the classification data.

One command reconciles the database with ``classification/domain_data.xlsx``:
additions, edits and deletions in the file all propagate, and running it twice
changes nothing the second time.

    python -m tools.i18n.sync_taxonomy --check       # validate the file only
    python -m tools.i18n.sync_taxonomy --dry-run     # show what would change
    python -m tools.i18n.sync_taxonomy --apply       # write the difference
    python -m tools.i18n.sync_taxonomy --watch       # apply on every save

What "the workbook is authoritative" means, precisely
----------------------------------------------------
* a worksheet is a category, named by the worksheet (rule R1 in
  :mod:`apps.importing.validators.workbook_rules`);
* column ``Term`` holds single words, column ``Keyword`` holds two or more - the
  split the database already makes between ``words_categorys`` (a term in a
  category) and ``keywords`` (a phrase owned by a category);
* a term removed from a sheet is unlinked from that category;
* a keyword removed from a sheet is deleted;
* a word row is **never** deleted implicitly: ``keywords.keyword`` stores word
  ids, so deleting a word would silently change another category's phrase.
  Orphans are reported, and ``--prune-words`` removes only those no phrase
  refers to;
* a worksheet that disappears removes its category only with
  ``--prune-categories`` - otherwise it is reported, because "I deleted a sheet"
  and "I renamed a sheet" look identical from here. ``--rename OLD=NEW`` says
  which one it was.

Exit status: 0 when the file is valid and the run succeeded, 1 on a rule
violation (``--check``), 2 when the database refused the change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.importing.validators import workbook_rules as rules  # noqa: E402

DEFAULT_XLSX = str(ROOT / "classification" / "domain_data.xlsx")


# ---------------------------------------------------------------------------
# database
# ---------------------------------------------------------------------------
def connect():
    import psycopg2

    return psycopg2.connect(
        host=os.environ.get("DB_HOST") or "localhost",
        port=int(os.environ.get("DB_PORT") or 5432),
        user=os.environ.get("DB_USER") or "postgres",
        password=os.environ.get("DB_PASSWORD") or "",
        dbname=os.environ.get("DB_NAME") or "postgres",
    )


def _query(conn, sql: str, params=None) -> List[Tuple]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def _scalar(conn, sql: str, params=None):
    rows = _query(conn, sql, params)
    return rows[0][0] if rows else None


def snapshot(conn) -> Dict[str, int]:
    out = {}
    for table in ("words", "categorys", "words_categorys", "keywords"):
        out[table] = _scalar(conn, f"SELECT count(*) FROM {table}")  # nosec B608
    return out


# ---------------------------------------------------------------------------
# the plan
# ---------------------------------------------------------------------------
@dataclass
class Plan:
    """The difference between the workbook and the database.

    ``delete_categories`` holds only what will actually be deleted (it needs
    ``--prune-categories``); a worksheet that vanished without that flag shows up
    in ``missing_categories`` instead, because a deleted sheet and a renamed one
    look identical from here.
    """

    create_categories: List[str] = field(default_factory=list)
    rename_categories: List[Tuple[str, str]] = field(default_factory=list)
    missing_categories: List[str] = field(default_factory=list)
    delete_categories: List[str] = field(default_factory=list)
    create_words: List[str] = field(default_factory=list)
    link_terms: List[Tuple[str, str]] = field(default_factory=list)
    unlink_terms: List[Tuple[str, str]] = field(default_factory=list)
    create_keywords: List[Tuple[str, str]] = field(default_factory=list)
    delete_keywords: List[Dict[str, Any]] = field(default_factory=list)
    keep_keywords: List[Tuple[str, str]] = field(default_factory=list)
    not_stored: List[Dict[str, str]] = field(default_factory=list)
    stale_keywords: List[Dict[str, str]] = field(default_factory=list)
    orphan_words: List[str] = field(default_factory=list)
    unchanged: Dict[str, int] = field(default_factory=dict)

    @property
    def changes(self) -> int:
        return sum(len(getattr(self, name)) for name in (
            "create_categories", "rename_categories", "delete_categories",
            "create_words", "link_terms", "unlink_terms",
            "create_keywords", "delete_keywords"))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "changes": self.changes,
            "create_categories": self.create_categories,
            "rename_categories": [f"{old} -> {new}" for old, new in self.rename_categories],
            "missing_categories": self.missing_categories,
            "delete_categories": self.delete_categories,
            "create_words": len(self.create_words),
            "link_terms": len(self.link_terms),
            "unlink_terms": len(self.unlink_terms),
            "create_keywords": len(self.create_keywords),
            "delete_keywords": len(self.delete_keywords),
            "keep_keywords": len(self.keep_keywords),
            "not_stored_shared": self.not_stored,
            "stale_keywords": self.stale_keywords,
            "orphan_words": len(self.orphan_words),
            "unchanged": self.unchanged,
        }


def _decode_keyword(conn, blob) -> str:
    """Turn a stored keyword blob back into its phrase (word ids -> texts)."""
    from core.serialization import unpack_int_list

    ids = [int(i) for i in unpack_int_list(blob)]
    if not ids:
        return ""
    rows = dict(_query(conn, "SELECT id, word FROM words WHERE id = ANY(%s)", (ids,)))
    return " ".join(str(rows.get(i, "")) for i in ids).strip()


def _stored_categories(conn) -> Dict[str, Tuple[str, int]]:
    """``word.casefold() -> (word, category id)``, read-only."""
    return {row[0].casefold(): (row[0], int(row[1])) for row in _query(
        conn,
        "SELECT w.word, c.id FROM categorys c JOIN words w ON w.id = c.word_id")}


def build_plan(conn, workbook: rules.Workbook, *,
               prune_categories: bool = False, prune_words: bool = False,
               renames: Optional[Dict[str, str]] = None) -> Plan:
    """Compute the difference. Reads only, so it is safe against production."""
    state = rules.desired_state(workbook)
    renames = {rules.normalise(old).casefold(): rules.normalise(new)
               for old, new in (renames or {}).items()}
    plan = Plan()
    stored = _stored_categories(conn)

    # A category's effective name is its stored name, or the new name when the
    # operator says the worksheet was renamed.
    effective = {key: renames.get(key, name) for key, (name, _id) in stored.items()}
    effective_by_id = {cid: effective[key] for key, (_n, cid) in stored.items()}

    workbook_names = {name.casefold(): name for name in state.categories}

    # -- categories ------------------------------------------------------
    # A worksheet matching a stored name is unchanged; one matching a rename
    # target is a rename; anything else is new. ``renames`` maps a casefolded
    # old name to the new text, so the comparison is on casefolded keys.
    renamed_targets = {
        new_text.casefold(): old_key
        for old_key, new_text in renames.items()
        if old_key in stored and new_text.casefold() in workbook_names
    }
    for key, name in workbook_names.items():
        if key in stored:
            plan.unchanged["categories"] = plan.unchanged.get("categories", 0) + 1
        elif key in renamed_targets:
            plan.rename_categories.append((stored[renamed_targets[key]][0], name))
        else:
            plan.create_categories.append(name)

    workbook_effective = set(workbook_names.values())
    for key, (name, _cid) in stored.items():
        if effective[key] in workbook_effective:
            continue
        plan.missing_categories.append(name)
        if prune_categories:
            plan.delete_categories.append(name)

    # -- terms -----------------------------------------------------------
    known = {row[0].casefold() for row in _query(conn, "SELECT word FROM words")}
    links: Dict[str, Dict[str, str]] = {}
    for category_word, term in _query(
            conn,
            "SELECT cw.word, tw.word FROM words_categorys wc"
            " JOIN categorys c ON c.id = wc.category_id"
            " JOIN words cw ON cw.id = c.word_id"
            " JOIN words tw ON tw.id = wc.word_id"):
        # keyed by the category's *effective* name, so a renamed worksheet's
        # existing links are compared against the new name, not re-created
        name = effective.get(category_word.casefold(), category_word)
        links.setdefault(name.casefold(), {})[term.casefold()] = term

    for name, (terms, _keywords) in state.categories.items():
        present = links.get(name.casefold(), {})
        for term in terms:
            key = term.casefold()
            if key not in known and term not in plan.create_words:
                plan.create_words.append(term)
            if key in present:
                plan.unchanged["terms"] = plan.unchanged.get("terms", 0) + 1
            else:
                plan.link_terms.append((name, term))
        wanted = {term.casefold() for term in terms}
        for key, text in present.items():
            if key not in wanted:
                plan.unlink_terms.append((name, text))

    # -- keywords --------------------------------------------------------
    # The schema stores a phrase once, so each phrase is compared against the
    # category the workbook says owns it.
    stored_keywords: Dict[str, Dict[str, List[int]]] = {}
    for keyword_id, category_id, blob in _query(
            conn, "SELECT id, category_id, keyword FROM keywords ORDER BY id"):
        name = effective_by_id.get(int(category_id))
        if name is None:
            continue
        text = _decode_keyword(conn, blob)
        stored_keywords.setdefault(name.casefold(), {}).setdefault(
            text.casefold(), []).append((int(keyword_id), text))

    for key, owner in state.keyword_owner.items():
        if owner.casefold() not in workbook_names:
            continue
        text = state.keyword_text(key, owner)
        if key in stored_keywords.get(owner.casefold(), {}):
            plan.keep_keywords.append((owner, text))
        else:
            plan.create_keywords.append((owner, text))

    for name_key, phrases in stored_keywords.items():
        name = workbook_names.get(name_key)
        wanted = {key for key, owner in state.keyword_owner.items()
                  if owner.casefold() == name_key}
        for key in phrases:
            if key in wanted:
                continue
            if name is None:
                owner = next((effective_by_id[cid] for cid in effective_by_id
                              if effective_by_id[cid].casefold() == name_key), name_key)
                plan.stale_keywords.append({"category": owner, "phrase": key})
                continue
            keyword_ids = phrases[key]
            plan.delete_keywords.append({
                "category": name,
                "phrase": keyword_ids[0][1],       # the stored spelling
                "keyword_id": keyword_ids[0][0],   # delete by identity
            })

    for key, listed_in in state.shared.items():
        owner = state.keyword_owner.get(key, "")
        for name in listed_in:
            if name.casefold() != owner.casefold():
                plan.not_stored.append({
                    "sheet": name, "phrase": key, "owner": owner,
                    "reason": "keywords.keyword is UNIQUE (one category per phrase)",
                })

    # -- orphan words ----------------------------------------------------
    # A word used only inside a keyword phrase is *not* an orphan: the phrase is
    # stored as word ids, so deleting it would silently rewrite another
    # category's keyword. Only words nothing at all refers to are orphans.
    from core.serialization import unpack_int_list

    referenced = set()
    for (blob,) in _query(conn, "SELECT keyword FROM keywords"):
        referenced.update(int(i) for i in unpack_int_list(blob))
    plan.orphan_words = [word for (word,) in _query(
        conn,
        "SELECT w.word FROM words w"
        " WHERE NOT EXISTS (SELECT 1 FROM words_categorys wc WHERE wc.word_id = w.id)"
        "   AND NOT EXISTS (SELECT 1 FROM categorys c WHERE c.word_id = w.id)")
        if int(_scalar(conn, "SELECT id FROM words WHERE word = %s", (word,)) or 0)
        not in referenced]
    return plan


def apply_plan(conn, workbook: rules.Workbook, plan: Plan,
               *, prune_words: bool = False) -> Dict[str, int]:
    """Write exactly the plan, in one transaction.

    ``apply`` never recomputes the difference, so what ``--dry-run`` printed is
    what this writes.
    """
    from core.serialization import pack_int_list

    written = {"categories_created": 0, "categories_deleted": 0, "categories_renamed": 0,
               "words_created": 0, "terms_linked": 0, "terms_unlinked": 0,
               "keywords_created": 0, "keywords_deleted": 0, "words_pruned": 0}
    state = rules.desired_state(workbook)

    def word_id(text: str) -> int:
        # ``words.word`` is UNIQUE case-sensitively, while the planner compares
        # words case-insensitively. Matching the same way here keeps the two
        # halves of the tool consistent: a row written by a lowercasing writer
        # is reused, not duplicated. An exact match wins when both exist.
        found = _scalar(
            conn,
            "SELECT id FROM words WHERE lower(word) = lower(%s)"
            " ORDER BY (word = %s) DESC, id LIMIT 1", (text, text))
        if found:
            return int(found)
        row = _query(conn, "INSERT INTO words (word) VALUES (%s) RETURNING id", (text,))
        written["words_created"] += 1
        return int(row[0][0])

    def category_id(name: str, *, create: bool) -> Optional[int]:
        found = _scalar(
            conn,
            "SELECT c.id FROM categorys c JOIN words w ON w.id = c.word_id"
            " WHERE lower(w.word) = lower(%s) ORDER BY (w.word = %s) DESC, c.id LIMIT 1",
            (name, name))
        if found:
            return int(found)
        if not create:
            return None
        row = _query(conn, "INSERT INTO categorys (word_id) VALUES (%s) RETURNING id",
                     (word_id(name),))
        written["categories_created"] += 1
        return int(row[0][0])

    with conn:  # one transaction: a failure leaves the database unchanged
        for old, new in plan.rename_categories:
            if _scalar(conn, "SELECT 1 FROM words WHERE word = %s", (new,)):
                raise RuntimeError(
                    f"cannot rename {old!r} to {new!r}: that word already exists")
            with conn.cursor() as cur:
                cur.execute("UPDATE words SET word = %s WHERE word = %s", (new, old))
                written["categories_renamed"] += cur.rowcount

        for name, (terms, _keywords) in state.categories.items():
            cid = category_id(name, create=True)
            for term in terms:
                tid = word_id(term)
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO words_categorys (word_id, category_id)"
                                " VALUES (%s, %s) ON CONFLICT DO NOTHING", (tid, cid))
                    written["terms_linked"] += cur.rowcount

        for name, term in plan.unlink_terms:
            cid = category_id(name, create=False)
            tid = _scalar(conn, "SELECT id FROM words WHERE word = %s", (term,))
            if cid and tid:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM words_categorys WHERE word_id = %s"
                                " AND category_id = %s", (tid, cid))
                    written["terms_unlinked"] += cur.rowcount

        for name, phrase in plan.create_keywords:
            cid = category_id(name, create=True)
            ids = [word_id(word) for word in phrase.split()]
            blob = pack_int_list(ids)
            try:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO keywords (keyword, category_id)"
                                " VALUES (%s, %s) ON CONFLICT DO NOTHING", (blob, cid))
                    written["keywords_created"] += cur.rowcount
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    f"the phrase {phrase!r} could not be stored for {name!r}: {exc}") from exc

        for item in plan.delete_keywords:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM keywords WHERE id = %s", (item["keyword_id"],))
                written["keywords_deleted"] += cur.rowcount

        for name in plan.delete_categories:
            cid = category_id(name, create=False)
            if cid:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM categorys WHERE id = %s", (cid,))
                    written["categories_deleted"] += cur.rowcount

        if prune_words and plan.orphan_words:
            referenced = set()
            for (blob,) in _query(conn, "SELECT keyword FROM keywords"):
                from core.serialization import unpack_int_list
                referenced.update(int(i) for i in unpack_int_list(blob))
            for word in plan.orphan_words:
                wid = _scalar(conn, "SELECT id FROM words WHERE word = %s", (word,))
                if wid is None or int(wid) in referenced:
                    continue
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM words WHERE word = %s", (word,))
                    written["words_pruned"] += cur.rowcount

    return written


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------
def report_workbook(workbook: rules.Workbook) -> None:
    info = workbook.as_dict()
    print(f"workbook : {workbook.path}")
    print(f"layout   : {workbook.layout}")
    print(f"sheets   : {info['categories']} categories, "
          f"{info['terms']} terms ({info['distinct_terms']} distinct), "
          f"{info['keywords']} keywords ({info['distinct_keywords']} distinct)")
    if workbook.errors:
        print(f"errors   : {len(workbook.errors)}")
        for violation in workbook.errors[:25]:
            print("   ", violation)
        if len(workbook.errors) > 25:
            print(f"    ... {len(workbook.errors) - 25} more")
    else:
        print("errors   : 0")
    if workbook.decisions:
        print(f"decisions: {len(workbook.decisions)} shared keyword(s) the schema "
              f"stores once - see {rules.OWNERS_SHEET}")
        for violation in workbook.decisions[:3]:
            print("   ", violation)
        if len(workbook.decisions) > 3:
            print(f"    ... {len(workbook.decisions) - 3} more (not printed)")


def _file_hash(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_renames(values: Sequence[str]) -> Dict[str, str]:
    out = {}
    for value in values or ():
        if "=" not in value:
            raise SystemExit(f"--rename expects OLD=NEW, got {value!r}")
        old, new = value.split("=", 1)
        out[old.strip()] = new.strip()
    return out


def run(path: str, *, check_only: bool = False, apply: bool = False,
        prune_categories: bool = False, prune_words: bool = False,
        renames: Optional[Dict[str, str]] = None, quiet: bool = False,
        report_path: Optional[str] = None) -> int:
    workbook = rules.read(path, renames=renames)
    if not quiet:
        report_workbook(workbook)
    if not workbook.ok:
        print("\nrefusing to touch the database: fix the errors above first",
              file=sys.stderr)
        return 1
    if check_only:
        return 0

    conn = connect()
    try:
        before = snapshot(conn)
        plan = build_plan(conn, workbook, prune_categories=prune_categories,
                          prune_words=prune_words, renames=renames)
        result: Dict[str, Any] = {
            "path": path,
            "file_sha256": _file_hash(path),
            "workbook": workbook.as_dict(),
            "plan": plan.as_dict(),
            "before": before,
            "applied": False,
        }
        if not quiet:
            print("\nplan")
            print(f"  categories: {len(plan.create_categories)} to create, "
                  f"{len(plan.rename_categories)} to rename, "
                  f"{len(plan.missing_categories)} in the database only")
            for name in plan.create_categories[:10]:
                print(f"     + {name}")
            for old, new in plan.rename_categories[:10]:
                print(f"     ~ {old} -> {new}")
            for name in plan.missing_categories[:10]:
                flag = "delete" if prune_categories else "kept (needs --prune-categories)"
                print(f"     - {name}  [{flag}]")
            print(f"  words     : {len(plan.create_words)} new")
            print(f"  terms     : {len(plan.link_terms)} to link, "
                  f"{len(plan.unlink_terms)} to unlink")
            print(f"  keywords  : {len(plan.create_keywords)} to create, "
                  f"{len(plan.delete_keywords)} to delete, "
                  f"{len(plan.keep_keywords)} unchanged")
            if plan.not_stored:
                print(f"  shared    : {len(plan.not_stored)} phrase memberships "
                      f"cannot be stored (one category per phrase) - reported, "
                      f"not dropped silently")
            if plan.orphan_words:
                print(f"  orphans   : {len(plan.orphan_words)} word(s) with no "
                      f"membership (kept unless --prune-words)")

        if apply and plan.changes:
            written = apply_plan(conn, workbook, plan, prune_words=prune_words)
            result["applied"] = True
            result["written"] = written
            if not quiet:
                print("\nwritten:", json.dumps(written))
        elif not apply and plan.changes and not quiet:
            print("\nno database change written (use --apply)")

        result["after"] = snapshot(conn)
        if report_path:
            Path(report_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
            if not quiet:
                print(f"report   : {report_path}")
        return 0
    except Exception as exc:  # noqa: BLE001 - the CLI must explain, not traceback
        conn.rollback()
        print(f"\ndatabase refused the change, rolled back: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()


def watch(path: str, interval: float, **options) -> int:
    """Apply the workbook whenever the file changes on disk."""
    last = _file_hash(path)
    print(f"watching {path} every {interval:g}s (Ctrl-C to stop)")
    try:
        while True:
            time.sleep(interval)
            current = _file_hash(path)
            if current == last:
                continue
            last = current
            print(f"\n[{time.strftime('%H:%M:%S')}] file changed, syncing")
            run(path, apply=True, **options)
    except KeyboardInterrupt:
        print("\nstopped")
        return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile the database with the category workbook.")
    parser.add_argument("--xlsx", default=DEFAULT_XLSX)
    parser.add_argument("--check", action="store_true",
                        help="validate the workbook and exit (default action)")
    parser.add_argument("--dry-run", action="store_true",
                        help="show the difference, write nothing")
    parser.add_argument("--apply", action="store_true", help="write the difference")
    parser.add_argument("--watch", action="store_true",
                        help="apply whenever the file changes")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--rename", action="append", default=[], metavar="OLD=NEW",
                        help="a worksheet was renamed; migrate the category")
    parser.add_argument("--prune-categories", action="store_true",
                        help="delete categories whose worksheet is gone")
    parser.add_argument("--prune-words", action="store_true",
                        help="delete word rows nothing refers to")
    parser.add_argument("--report", default=None, help="write a JSON report here")
    parser.add_argument("--write-workbook", action="store_true",
                        help="rewrite the file in the two-column layout and exit")
    args = parser.parse_args(argv)

    if args.write_workbook:
        workbook = rules.read(args.xlsx, validate=False)
        counts = rules.write(args.xlsx, workbook)
        print(f"rewrote {args.xlsx}: {json.dumps(counts)}")
        return 0

    renames = _parse_renames(args.rename)
    if args.watch:
        return watch(args.xlsx, args.interval, prune_categories=args.prune_categories,
                     prune_words=args.prune_words, renames=renames,
                     report_path=args.report)
    if args.apply:
        return run(args.xlsx, apply=True, prune_categories=args.prune_categories,
                   prune_words=args.prune_words, renames=renames,
                   report_path=args.report)
    if args.dry_run:
        return run(args.xlsx, apply=False, prune_categories=args.prune_categories,
                   prune_words=args.prune_words, renames=renames,
                   report_path=args.report)
    return run(args.xlsx, check_only=True, renames=renames)


if __name__ == "__main__":
    sys.exit(main())
