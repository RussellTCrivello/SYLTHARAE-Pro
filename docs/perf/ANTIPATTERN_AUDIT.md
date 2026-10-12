# Performance anti-pattern audit (automated)

Total findings: **201**

| Severity | Count |
|----------|------:|
| high | 94 |
| medium | 56 |
| low | 51 |

| File | Line | Severity | Problem | Snippet |
|------|-----:|----------|---------|---------|
| `Api\routes\places.py` | 375 | high | N+1 / loop I/O or query | `for name in cleaned_names:` |
| `Api\services\import_service.py` | 413 | high | N+1 / loop I/O or query | `for _tn in delete_order:` |
| `Api\services\search_service.py` | 360 | high | Leading-wildcard ILIKE | `WHEN p.file_name ILIKE '%%' || term || '%%' THEN 2.0` |
| `Api\services\search_service.py` | 368 | high | Leading-wildcard ILIKE | `AND w.word ILIKE '%%' || term || '%%'` |
| `Api\services\search_service.py` | 431 | high | Leading-wildcard ILIKE | `WHEN p.file_name ILIKE '%%' || term || '%%' THEN 2.0` |
| `Api\services\search_service.py` | 439 | high | Leading-wildcard ILIKE | `AND w.word ILIKE '%%' || term || '%%'` |
| `Api\services\search_service.py` | 1060 | high | Leading-wildcard ILIKE | `WHEN p.file_name ILIKE '%%' || term || '%%' THEN 2.0` |
| `Api\services\search_service.py` | 1068 | high | Leading-wildcard ILIKE | `AND w.word ILIKE '%%' || term || '%%'` |
| `Api\utils\utils.py` | 994 | high | Leading-wildcard ILIKE | `WHEN p.file_name ILIKE '%%' || term || '%%' THEN 2.0` |
| `Api\utils\utils.py` | 999 | high | Leading-wildcard ILIKE | `AND w.word ILIKE '%%' || term || '%%'` |
| `database\bootstrap.py` | 126 | high | N+1 / loop I/O or query | `for ext in REQUIRED_EXTENSIONS:` |
| `database\database\repository\contents_repo.py` | 202 | high | N+1 / loop I/O or query | `for seq, chunk in enumerate(chunks):` |
| `database\migrations\m0001_initial_schema.py` | 222 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0002_performance_indexes.py` | 34 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0003_auth_tables.py` | 61 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0007_provenance_hierarchy_status.py` | 132 | high | N+1 / loop I/O or query | `for legacy, target in _BACKFILL.items():` |
| `database\migrations\m0007_provenance_hierarchy_status.py` | 159 | high | N+1 / loop I/O or query | `for statement in statements:` |
| `database\migrations\m0009_analyst_categorization.py` | 93 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0010_content_raw_text.py` | 48 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0011_content_identity.py` | 59 | high | N+1 / loop I/O or query | `for statement in statements:` |
| `database\migrations\m0012_translation_overrides.py` | 29 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0014_alerts_notification_indexes.py` | 46 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0015_geo_mentions.py` | 42 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0016_saved_searches.py` | 84 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0017_content_signals.py` | 117 | high | N+1 / loop I/O or query | `for statement in _STATEMENTS:` |
| `database\migrations\m0018_signal_provenance.py` | 53 | high | N+1 / loop I/O or query | `for statement in _STATEMENTS:` |
| `database\migrations\m0019_gazetteer.py` | 166 | high | N+1 / loop I/O or query | `for statement in _STATEMENTS:` |
| `database\migrations\m0020_monitoring_rules.py` | 163 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0021_scenarios.py` | 195 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0022_report_runs.py` | 151 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0023_report_artifacts.py` | 105 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0024_audit_log_lookup_indexes.py` | 38 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0024_audit_log_lookup_indexes.py` | 44 | high | N+1 / loop I/O or query | `for index_name, _ in INDEXES:` |
| `database\migrations\m0025_signal_run_history_index.py` | 30 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0025_signal_run_history_index.py` | 36 | high | N+1 / loop I/O or query | `for index_name, _ in INDEXES:` |
| `database\migrations\m0026_report_run_analyses.py` | 79 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0027_report_baselines.py` | 58 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0028_run_dataset_baseline.py` | 46 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0029_path_revisions.py` | 66 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0030_artifact_language.py` | 44 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0031_job_schedules.py` | 65 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0032_retention_schedule_type.py` | 32 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0033_user_navigation_prefs.py` | 47 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0035_search_inverted_index_cover.py` | 16 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\migrations\m0036_words_hashs_word_hash_index.py` | 16 | high | N+1 / loop I/O or query | `for statement in SQL_STATEMENTS:` |
| `database\services\contents_db_service.py` | 1108 | high | N+1 / loop I/O or query | `for keyword_id in keyword_ids:` |
| `services\navigation_prefs.py` | 92 | high | N+1 / loop I/O or query | `for interface_id, hidden, position in cleaned:` |
| `services\navigation_prefs.py` | 116 | high | N+1 / loop I/O or query | `for interface_id in stale:` |
| `services\reporting\runs.py` | 342 | high | N+1 / loop I/O or query | `for position, an in enumerate(analyses or ()):` |
| `services\reporting\runs.py` | 354 | high | N+1 / loop I/O or query | `for position, ds in enumerate(datasets or ()):` |
| `tests\integration\_seed.py` | 73 | high | N+1 / loop I/O or query | `for word, count in counts.items():` |
| `tests\integration\test_analyst_categorization.py` | 81 | high | N+1 / loop I/O or query | `for name in (_ALPHA, _BETA):` |
| `tests\integration\test_analyst_categorization_audit.py` | 74 | high | N+1 / loop I/O or query | `for name in (_ALPHA, _BETA):` |
| `tests\integration\test_audit_log_viewer.py` | 23 | high | N+1 / loop I/O or query | `for i in range(n):` |
| `tests\integration\test_cell_locations_and_recipients.py` | 132 | high | N+1 / loop I/O or query | `for suffix in ("xlsx", "csv", "eml"):` |
| `tests\integration\test_content_display_search.py` | 91 | high | N+1 / loop I/O or query | `for name, ctx in ((_ALPHA, context_id), (_BETA, beta_context_id)):` |
| `tests\integration\test_content_identity.py` | 114 | high | N+1 / loop I/O or query | `for i in (1, 2):` |
| `tests\integration\test_file_navigation_pages.py` | 133 | high | N+1 / loop I/O or query | `for label, created in _FILES:` |
| `tests\integration\test_migration_upgrade_path.py` | 347 | high | N+1 / loop I/O or query | `for _ in range(2):` |
| `tests\integration\test_notification_accuracy.py` | 86 | high | N+1 / loop I/O or query | `for name in (_DUP_A, _DUP_B):` |
| `tests\integration\test_relations_list.py` | 148 | high | N+1 / loop I/O or query | `for copy in range(copies):` |
| `tests\integration\test_report_catalog_api.py` | 62 | high | N+1 / loop I/O or query | `for wid in (kw_id, common_id, _word_id(f"unk{tag}")):` |
| `tests\integration\test_report_catalog_api.py` | 80 | high | N+1 / loop I/O or query | `for h in hashes:` |
| `tests\integration\test_report_catalog_api.py` | 317 | high | N+1 / loop I/O or query | `for pid in places:` |
| `tests\integration\test_report_registry_pg.py` | 79 | high | N+1 / loop I/O or query | `for wid in member_ids:` |
| `tests\integration\test_report_registry_pg.py` | 98 | high | N+1 / loop I/O or query | `for h in matched_hashes:` |
| `tests\integration\test_report_registry_pg.py` | 126 | high | N+1 / loop I/O or query | `for i, (stype, d_from, d_to, orient, _bucket) in enumerate(_signals):` |
| `tests\integration\test_report_registry_pg.py` | 251 | high | N+1 / loop I/O or query | `for pid in place_ids:` |
| `tests\integration\test_reports_comprehensive_pg.py` | 72 | high | N+1 / loop I/O or query | `for h, count in ((h1, 3), (h3, 1)):` |
| `tests\integration\test_retention_pg.py` | 111 | high | N+1 / loop I/O or query | `for _ in range(n_events):` |
| `tests\integration\test_rule_engine_pg.py` | 38 | high | N+1 / loop I/O or query | `for key in ("a", "b"):` |
| `tests\integration\test_rule_engine_pg.py` | 370 | high | N+1 / loop I/O or query | `for f, t in cases:` |
| `tests\integration\test_scenario_engine_pg.py` | 38 | high | N+1 / loop I/O or query | `for key in ("a", "b", "c", "d"):` |
| `tests\integration\test_search_after_ingest.py` | 7 | high | Leading-wildcard ILIKE | `WHEN p.file_name ILIKE '%' || term || '%' THEN 2.0` |
| `tests\integration\test_search_after_ingest.py` | 13 | high | Leading-wildcard ILIKE | `name ILIKE '%'  || %s || '%'   -> IndexError: tuple index out of range` |
| `tests\integration\test_search_after_ingest.py` | 14 | high | Leading-wildcard ILIKE | `name ILIKE '%%' || %s || '%%'  -> ok` |
| `tests\integration\test_show_more_pagination.py` | 25 | high | N+1 / loop I/O or query | `for i in range(12):` |
| `tests\integration\test_show_more_pagination.py` | 59 | high | N+1 / loop I/O or query | `for i in range(12):` |
| `tests\integration\test_show_more_pagination.py` | 82 | high | N+1 / loop I/O or query | `for i in range(8):` |
| `tests\integration\test_show_more_pagination.py` | 103 | high | N+1 / loop I/O or query | `for i in range(8):` |
| `tests\integration\test_show_more_pagination.py` | 124 | high | N+1 / loop I/O or query | `for i in range(12):` |
| `tests\integration\test_show_more_pagination.py` | 150 | high | N+1 / loop I/O or query | `for i in range(10):` |
| `tests\integration\test_show_more_pagination.py` | 173 | high | N+1 / loop I/O or query | `for i in range(10):` |
| `tests\integration\test_signal_explorer_pg.py` | 48 | high | N+1 / loop I/O or query | `for key in ("a", "b"):` |
| `tests\integration\test_signal_explorer_pg.py` | 258 | high | N+1 / loop I/O or query | `for username in ("testviewer", "testadmin"):` |
| `tests\integration\test_structural_marker_exclusion.py` | 150 | high | N+1 / loop I/O or query | `for suffix in ("xlsx", "pptx", "docx", "eml", "txt"):` |
| `tests\integration\test_structural_marker_exclusion.py` | 178 | high | N+1 / loop I/O or query | `for suffix, path_id in ingested.items():` |
| `tests\integration\test_structured_content_display.py` | 181 | high | N+1 / loop I/O or query | `for suffix in ("xlsx", "pptx", "docx", "md", "log", "csv"):` |
| `tests\integration\test_title_parent_linkage.py` | 90 | high | N+1 / loop I/O or query | `for name in ("container.zip", "child.pdf"):` |
| `tests\unit\test_progressive_tables.py` | 341 | high | N+1 / loop I/O or query | `for hash_id in hash_ids:` |
| `tools\docs\generate_schema.py` | 108 | high | N+1 / loop I/O or query | `for sql in (_COLUMNS, _CONSTRAINTS, _INDEXES, _MIGRATIONS):` |
| `tools\perf\audit_ilike.py` | 19 | high | Leading-wildcard ILIKE | `if "ilike '%" in lower or "ilike \"%\"%" in lower:` |
| `tools\perf\audit_log_perf.py` | 48 | high | N+1 / loop I/O or query | `for sql in getattr(m, "AUDIT_LOG_STATEMENTS", ()):` |
| `tools\verify\runtime_provision.py` | 78 | high | N+1 / loop I/O or query | `for key in DOCUMENTS:` |
| `Api\routes\api.py` | 402 | low | Unbounded loop | `while True:` |
| `Api\routes\api.py` | 688 | low | Unbounded loop | `while True:` |
| `Api\routes\file_analysis.py` | 312 | low | SELECT * | `FROM (SELECT * FROM word_files UNION SELECT * FROM keyword_files) u` |
| `Api\routes\file_analysis.py` | 312 | low | SELECT * | `FROM (SELECT * FROM word_files UNION SELECT * FROM keyword_files) u` |
| `Api\routes\operations_api.py` | 279 | low | Unbounded loop | `while True:` |
| `Api\routes\operations_api.py` | 657 | low | Unbounded loop | `while True:` |
| `Api\routes\operations_api.py` | 1124 | low | Unbounded loop | `while True:` |
| `Api\services\export_service.py` | 470 | low | SELECT * | `cursor.execute(f"SELECT * FROM {table_name} LIMIT 10000")` |
| `Api\services\search_service.py` | 460 | low | SELECT * | `SELECT * FROM ranked_results WHERE rn = 1` |
| `Api\services\search_service.py` | 463 | low | SELECT * | `SELECT *, ROW_NUMBER() OVER (` |
| `Api\utils\utils.py` | 2606 | low | Unbounded loop | `while True:` |
| `apps\cli\main.py` | 995 | low | Unbounded loop | `while True:` |
| `apps\cli\main.py` | 1247 | low | Unbounded loop | `while True:` |
| `core\archive_safety.py` | 306 | low | Unbounded loop | `while True:` |
| `core\archive_safety.py` | 375 | low | Unbounded loop | `while True:` |
| `core\archive_safety.py` | 412 | low | Unbounded loop | `while True:` |
| `core\archive_safety.py` | 925 | low | Unbounded loop | `while True:` |
| `core\hashing.py` | 62 | low | Unbounded loop | `while True:` |
| `core\hashing.py` | 133 | low | Unbounded loop | `while True:` |
| `core\monitoring\notification_service.py` | 495 | low | Unbounded loop | `while True:` |
| `core\security\service.py` | 337 | low | SELECT * | `cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))` |
| `core\security\service.py` | 419 | low | SELECT * | `cur.execute("SELECT * FROM users WHERE username = %s", (username,))` |
| `database\database\queries\path_queries.py` | 40 | low | SELECT * | `return 'SELECT * FROM paths'` |
| `install.py` | 64 | low | Unbounded loop | `while True:` |
| `install.py` | 82 | low | Unbounded loop | `while True:` |
| `pipeline\integrated_reader.py` | 1525 | low | Unbounded loop | `while True:` |
| `pipeline\integrated_reader.py` | 2502 | low | Unbounded loop | `while True:` |
| `reader_file\readers\read_database.py` | 208 | low | SELECT * | `cursor.execute(f"SELECT * FROM {table_name} LIMIT {max_rows_per_table};")` |
| `reader_file\readers\read_remaining.py` | 154 | low | Unbounded loop | `while True:` |
| `reader_file\readers\read_remaining.py` | 161 | low | Unbounded loop | `while True:` |
| `reader_file\readers\read_remaining.py` | 436 | low | Unbounded loop | `while True:` |
| `reader_file\readers\read_remaining.py` | 561 | low | Unbounded loop | `while True:` |
| `services\detection\detection_admin.py` | 231 | low | SELECT * | `" FROM (SELECT * FROM content_signal_runs r" + clause` |
| `services\detection\redetection.py` | 206 | low | SELECT * | `" (SELECT * FROM unnest(%s::text[], %s::text[]))",` |
| `services\detection\redetection.py` | 117 | low | Unbounded loop | `while True:` |
| `services\jobs\manager.py` | 220 | low | Unbounded loop | `while True:` |
| `services\map_packages.py` | 195 | low | Unbounded loop | `while True:` |
| `services\monitoring\scenario_engine.py` | 394 | low | SELECT * | `+ decision.q.sql + " SELECT * FROM out", decision.q.params)` |
| `services\monitoring\scenarios.py` | 375 | low | SELECT * | `+ " FROM (SELECT * FROM scenario_outcomes WHERE " + clause` |
| `services\reporting\runs.py` | 708 | low | SELECT * | `" (SELECT * FROM unnest(%s::text[], %s::int[]))")` |
| `services\reporting\runs.py` | 739 | low | SELECT * | `" (SELECT * FROM unnest(%s::text[], %s::int[]))")` |
| `services\retention\service.py` | 145 | low | Unbounded loop | `while True:` |
| `static\js\modules\rendering\cursor-pagination.js` | 17 | low | SELECT * | `* @param {Array<string>} options.select_columns - Columns to select` |
| `tests\integration\test_audit_log_viewer.py` | 51 | low | Unbounded loop | `while True:` |
| `tests\integration\test_relations_list.py` | 206 | low | Unbounded loop | `while True:` |
| `tests\integration\test_scenario_engine_pg.py` | 135 | low | SELECT * | `cur.execute("SELECT * FROM scenario_outcomes WHERE scenario_id = %s"` |
| `tests\unit\_rar_fixtures.py` | 28 | low | Unbounded loop | `while True:` |
| `tools\perf\audit_antipatterns.py` | 18 | low | SELECT * | `(r"SELECT\s+\*", "SELECT *", "low"),` |
| `tools\perf\audit_antipatterns.py` | 20 | low | Unbounded loop | `(r"while True:", "Unbounded loop", "low"),` |
| `tools\perf\detection_admin_perf.py` | 173 | low | SELECT * | `cur.execute("EXPLAIN (FORMAT JSON) SELECT * FROM content_signal_runs" + clause  # nosec B608 # developer benchmark; filt` |
| `tools\verify\runtime_check_detection.py` | 126 | low | Unbounded loop | `while True:` |
| `Api\blueprints\files.py` | 541 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\repositories\paths.py` | 97 | medium | SQL OFFSET pagination | `clauses.append("ORDER BY date_creation DESC OFFSET %s LIMIT %s")` |
| `Api\routes\api.py` | 804 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\api.py` | 824 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\archives.py` | 723 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\archives.py` | 808 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\archives.py` | 890 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\archives.py` | 943 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\archives.py` | 998 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\archives.py` | 1047 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\archives.py` | 1106 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\archives.py` | 1161 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\archives.py` | 1239 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\archives.py` | 1283 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\archives.py` | 1395 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\archives.py` | 1439 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\archives_api.py` | 1898 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\file_analysis.py` | 953 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\keywords.py` | 709 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\notifications_page.py` | 190 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\places.py` | 256 | medium | SQL OFFSET pagination | `f" ORDER BY {place_sort[sort]} {order.upper()}, p.place_key ASC LIMIT %s OFFSET %s",` |
| `Api\routes\places.py` | 613 | medium | SQL OFFSET pagination | `f" ORDER BY {sort_columns[sort]} {order.upper()}, n.id ASC LIMIT %s OFFSET %s",` |
| `Api\routes\places.py` | 813 | medium | SQL OFFSET pagination | `f" ORDER BY {LOAD_SORT[sort]} {order.upper()}, id DESC LIMIT %s OFFSET %s",` |
| `Api\routes\sides.py` | 65 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\routes\sources.py` | 71 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\services\analyst_categories.py` | 567 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\services\analyst_categories.py` | 696 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\services\search_service.py` | 486 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\services\search_service.py` | 1081 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\services\search_service.py` | 1619 | medium | SQL OFFSET pagination | `limit_clause = "LIMIT %s OFFSET %s"` |
| `Api\utils\utils.py` | 873 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\utils\utils.py` | 1396 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\utils\utils.py` | 1558 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\utils\utils.py` | 1679 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\utils\utils.py` | 1948 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `Api\utils\utils.py` | 2456 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `core\criteria\compiler.py` | 116 | medium | SQL OFFSET pagination | `") matched ORDER BY hash_id ASC LIMIT %s OFFSET %s"` |
| `core\criteria\compiler.py` | 120 | medium | SQL OFFSET pagination | `f"ORDER BY {self.order_sql} LIMIT %s OFFSET %s")` |
| `database\database\queries\category_queries.py` | 81 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `database\database\queries\keyword_queries.py` | 137 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `database\database\queries\path_queries.py` | 104 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `database\database\queries\word_queries.py` | 140 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `database\database\queries\word_queries.py` | 184 | medium | SQL OFFSET pagination | `LIMIT %s OFFSET %s` |
| `database\database\repository\words_repo.py` | 359 | medium | SQL OFFSET pagination | `query = base_query.replace("LIMIT %s OFFSET %s", f"{order_by}\n            LIMIT %s OFFSET %s")` |
| `database\database\repository\words_repo.py` | 359 | medium | SQL OFFSET pagination | `query = base_query.replace("LIMIT %s OFFSET %s", f"{order_by}\n            LIMIT %s OFFSET %s")` |
| `services\detection\detection_admin.py` | 232 | medium | SQL OFFSET pagination | `+ " ORDER BY r.ran_at DESC, r.hash_id DESC, r.detector LIMIT %s OFFSET %s) r"` |
| `services\detection\signal_query.py` | 511 | medium | SQL OFFSET pagination | `f" ORDER BY {EXPLORER_SORTS[sort]}, s.id ASC LIMIT %s OFFSET %s",` |
| `services\detection\signal_query.py` | 636 | medium | SQL OFFSET pagination | `f" ORDER BY {EXPLORER_SORTS[sort]}, s.id ASC LIMIT %s OFFSET %s",` |
| `services\monitoring\rules.py` | 384 | medium | SQL OFFSET pagination | `" WHERE rule_id = %s ORDER BY id DESC LIMIT %s OFFSET %s",` |
| `services\monitoring\scenarios.py` | 302 | medium | SQL OFFSET pagination | `" ORDER BY id DESC LIMIT %s OFFSET %s", params + [limit, offset])` |
| `services\monitoring\scenarios.py` | 376 | medium | SQL OFFSET pagination | `+ " ORDER BY id DESC LIMIT %s OFFSET %s) so" + lateral + " ORDER BY so.id DESC",` |
| `services\reporting\runs.py` | 780 | medium | SQL OFFSET pagination | `+ " ORDER BY requested_at DESC, id DESC LIMIT %s OFFSET %s",` |
| `tests\unit\test_fast_search_sql.py` | 54 | medium | SQL OFFSET pagination | `if "LIMIT %s OFFSET %s" in sql` |
| `tests\unit\test_fast_search_sql.py` | 59 | medium | SQL OFFSET pagination | `if "LIMIT %s OFFSET %s" in sql` |
| `tests\unit\test_notification_volume_guards.py` | 73 | medium | SQL OFFSET pagination | `assert "LIMIT %s OFFSET %s" in source, "pagination must be SQL-side"` |
| `tools\perf\detection_admin_perf.py` | 174 | medium | SQL OFFSET pagination | `+ " ORDER BY ran_at DESC, hash_id DESC, detector LIMIT %s OFFSET %s",` |
