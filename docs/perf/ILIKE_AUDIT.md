# ILIKE / LIKE audit

| Class | Count |
|-------|------:|
| other | 928 |
| metadata_filename | 36 |
| leading_wildcard | 12 |
| expensive_word_scan | 4 |
| content_or_path | 2 |

| File | Line | Class | Snippet |
|------|-----:|-------|---------|
| `install.py` | 83 | other | `raw = input(f"  {label} [{hint}]: ").strip().lower()` |
| `install.py` | 109 | other | `return (True, "") if value.upper() in valid else (False, f"Must be one of: {', '.join(sorted(valid))}")` |
| `install.py` | 169 | other | `required[name.lower()] = line` |
| `run_web.py` | 144 | other | `debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')` |
| `verify_readiness.py` | 680 | other | `print(f"\n=== {current_section.upper()} ===")` |
| `Api\cursor_pagination.py` | 249 | other | `if op not in ('=', '!=', '>', '<', '>=', '<=', 'LIKE', 'ILIKE', 'IN', 'BETWEEN'):` |
| `Api\cursor_pagination.py` | 253 | other | `if op in ('=', '!=', '>', '<', '>=', '<=', 'LIKE', 'ILIKE'):` |
| `Api\cursor_pagination.py` | 285 | other | `any(func in col.upper() for func in ['COUNT(', 'SUM(', 'AVG(', 'MAX(', 'MIN('])` |
| `Api\cursor_pagination.py` | 297 | other | `col_upper = col.upper().strip()` |
| `Api\cursor_pagination.py` | 325 | other | `if column_part.lower() in bytea_columns:` |
| `Api\cursor_pagination.py` | 329 | other | `# If it's from a joined table (like w.word), we need to include it` |
| `Api\cursor_pagination.py` | 339 | other | `if ' AS ' in col_name.upper() or re.search(r'\s+[Aa][Ss]\s+', col_name, re.IGNORECASE):` |
| `Api\cursor_pagination.py` | 350 | other | `# If sort_column is like "s.importance", check if it matches alias_or_table` |
| `Api\cursor_pagination.py` | 371 | other | `if clean_col and ' AS ' not in clean_col.upper():` |
| `Api\cursor_pagination.py` | 390 | other | `col_upper = col.upper()` |
| `Api\cursor_pagination.py` | 395 | other | `alias_name = parts[1].strip().upper()` |
| `Api\cursor_pagination.py` | 397 | other | `if alias_name == sort_col_name.upper() or alias_name == sort_column.upper().replace('.', '_'):` |
| `Api\cursor_pagination.py` | 403 | other | `if sort_col_name.upper() in col_upper:` |
| `Api\cursor_pagination.py` | 464 | other | `# This handles cases where joins reference an alias like "s.id"` |
| `Api\cursor_pagination.py` | 468 | other | `# Look for pattern like "ON alias.column" or "ON alias.column ="` |
| `Api\cursor_pagination.py` | 495 | other | `if op in ('=', '!=', '>', '<', '>=', '<=', 'LIKE', 'ILIKE'):` |
| `Api\blueprints\analytics.py` | 32 | other | `"""Check if a path is likely an archive file based on extension"""` |
| `Api\blueprints\analytics.py` | 36 | other | `path_lower = path_name.lower()` |
| `Api\blueprints\analytics.py` | 44 | other | `Normalizes path separators and creates appropriate LIKE patterns for matching.` |
| `Api\blueprints\analytics.py` | 67 | other | `(REPLACE(REPLACE(p.file_path, '\\', '/'), '::', '::') LIKE %s` |
| `Api\blueprints\analytics.py` | 68 | other | `OR REPLACE(p.file_path, '\\', '/') LIKE %s)` |
| `Api\blueprints\analytics.py` | 79 | other | `where_clause = "REPLACE(p.file_path, '\\', '/') LIKE %s"` |
| `Api\blueprints\analytics.py` | 85 | other | `(REPLACE(p.file_path, '\\', '/') LIKE %s` |
| `Api\blueprints\analytics.py` | 94 | other | `(REPLACE(p.file_path, '\\', '/') LIKE %s` |
| `Api\blueprints\analytics.py` | 399 | other | `WHERE file_path LIKE '%::%'` |
| `Api\blueprints\analytics.py` | 675 | other | `BOOL_OR(p.file_path LIKE '%::%') as is_archive` |
| `Api\blueprints\analytics.py` | 741 | metadata_filename | `where_conditions.append("(p.file_name ILIKE %s OR p.file_path ILIKE %s)")` |
| `Api\blueprints\analytics.py` | 1800 | other | `UPPER(COALESCE(` |
| `Api\blueprints\analytics.py` | 1813 | other | `UPPER(COALESCE(` |
| `Api\blueprints\files.py` | 468 | other | `#: same allowlist, so a sorted export is ordered exactly like the view.` |
| `Api\blueprints\files.py` | 512 | other | `f"{LIST_SORT_COLUMNS[sort_key]} {sort_order.upper()} NULLS LAST, "` |
| `Api\blueprints\files.py` | 549 | other | `highlight_lower = highlight_term.lower()` |
| `Api\blueprints\files.py` | 553 | other | `if highlight_lower and highlight_lower in (name or '').lower():` |
| `Api\blueprints\files.py` | 817 | other | `normalized = str(value or 'Unknown').strip().lstrip('.').lower()` |
| `Api\blueprints\files.py` | 829 | other | `return names.get(normalized, normalized.upper() if normalized else 'Unknown format')` |
| `Api\blueprints\files.py` | 990 | other | `case_sensitive = request.args.get('case_sensitive', 'false').lower() == 'true'` |
| `Api\blueprints\files.py` | 991 | other | `whole_word = request.args.get('whole_word', 'false').lower() == 'true'` |
| `Api\blueprints\files.py` | 1294 | other | `if force_extension and not result.lower().endswith(f'.{ext.lower()}'):` |
| `Api\blueprints\files.py` | 1310 | other | `if not result.lower().endswith(f'.{ext.lower()}'):` |
| `Api\blueprints\files.py` | 1412 | other | `if not base.lower().endswith(suffix):` |
| `Api\blueprints\files.py` | 1431 | other | `export_format = str(payload.get('format') or 'csv').lower()` |
| `Api\blueprints\files.py` | 1436 | other | `scope = str(payload.get('scope') or '').lower()` |
| `Api\blueprints\files.py` | 1461 | metadata_filename | `ORDER BY LOWER(COALESCE(p.file_name, '')), p.id` |
| `Api\blueprints\files.py` | 1495 | other | `'selected' if scope == 'selected' else _file_type_label(file_type).lower().replace(' ', '_'))` |
| `Api\blueprints\files.py` | 1575 | other | `export_format = str(payload.get('format') or 'csv').lower()` |
| `Api\blueprints\files.py` | 1606 | other | `scope = str(payload.get('scope') or 'selected').lower()` |
| `Api\blueprints\files.py` | 1626 | metadata_filename | `ORDER BY LOWER(COALESCE(p.file_name, '')), p.id` |
| `Api\blueprints\files.py` | 1733 | other | `export_format = str(payload.get('format') or 'txt').lower()` |
| `Api\blueprints\files.py` | 1736 | other | `export_format = str(request.form.get('format') or 'txt').lower()` |
| `Api\blueprints\files.py` | 1861 | other | `kind = str(payload.get('kind') or 'selection').strip().lower()` |
| `Api\blueprints\files.py` | 1865 | other | `export_format = str(payload.get('format') or 'txt').lower()` |
| `Api\blueprints\files.py` | 1972 | other | `export_format = str(payload.get('format') or 'csv').lower()` |
| `Api\blueprints\files.py` | 1976 | other | `export_format = str(request.form.get('format') or 'csv').lower()` |
| `Api\blueprints\files.py` | 1981 | other | `dedupe = str(dedupe_raw).strip().lower() in {'1', 'true', 'yes', 'on'} if dedupe_raw is not None else False` |
| `Api\blueprints\files.py` | 2335 | other | `case_sensitive = request.args.get('case_sensitive', 'false').lower() == 'true'` |
| `Api\blueprints\files.py` | 2336 | other | `whole_word = request.args.get('whole_word', 'false').lower() == 'true'` |
| `Api\blueprints\files.py` | 2478 | other | `case_sensitive = request.args.get('case_sensitive', 'false').lower() == 'true'` |
| `Api\blueprints\files.py` | 2479 | other | `whole_word = request.args.get('whole_word', 'false').lower() == 'true'` |
| `Api\blueprints\files.py` | 2527 | other | `# Convert file_info dict to tuple-like structure for template compatibility` |
| `Api\blueprints\files.py` | 2528 | other | `# get_file() returns a dict, but template expects tuple-like access (file[0], file[1], etc.)` |
| `Api\blueprints\files.py` | 2660 | other | `if path_obj.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg']:` |
| `Api\blueprints\files.py` | 2713 | other | `if path_obj.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg']:` |
| `Api\repositories\paths.py` | 10 | other | `if "RETURNING" not in query.upper():` |
| `Api\routes\analysis.py` | 212 | other | `# unavailable - never with invented values that look like a reading.` |
| `Api\routes\analysis.py` | 305 | other | `if 'not found' in error_message.lower():` |
| `Api\routes\analysis.py` | 307 | other | `elif 'permission' in error_message.lower():` |
| `Api\routes\analysis.py` | 309 | other | `elif 'corrupted' in error_message.lower() or 'invalid' in error_message.lower():` |
| `Api\routes\analyst_categories.py` | 165 | other | `status = 404 if "not found" in error.lower() else 400` |
| `Api\routes\analyst_categories.py` | 174 | other | `status = 404 if "not found" in error.lower() else 400` |
| `Api\routes\analyst_categories.py` | 211 | other | `create_category=str(data.get("create_category", "false")).lower() == "true",` |
| `Api\routes\api.py` | 599 | other | `# SID-01: like SRC-01, the deletion call had been lost - the` |
| `Api\routes\api.py` | 801 | other | `WHERE w.word ILIKE %s {exclude_clause}` |
| `Api\routes\api.py` | 806 | other | `# Use exact match without wildcards - ILIKE without % is case-insensitive exact match` |
| `Api\routes\api.py` | 810 | expensive_word_scan | `count_query = f"SELECT COUNT(*) FROM words w WHERE w.word ILIKE %s {exclude_clause}"` |
| `Api\routes\api.py` | 1488 | other | `if 'invalid load key' not in str(e).lower():` |
| `Api\routes\archives.py` | 32 | other | `column = _ARCHIVES_FILE_SORT_COLUMNS.get((sort_by or '').strip().lower(), 'p.file_date')` |
| `Api\routes\archives.py` | 33 | other | `direction = 'ASC' if str(sort_dir or '').strip().lower() == 'asc' else 'DESC'` |
| `Api\routes\archives.py` | 39 | other | `return f"""LOWER(REPLACE(` |
| `Api\routes\archives.py` | 43 | other | `OR UPPER({alias}.file_type) = 'FILE'` |
| `Api\routes\archives.py` | 54 | other | `keeps the historical exact or LIKE behaviour.` |
| `Api\routes\archives.py` | 64 | other | `str(part).strip().lstrip('.').lower()` |
| `Api\routes\archives.py` | 78 | other | `clauses.append(f"{type_expr} LIKE %s")` |
| `Api\routes\archives.py` | 85 | other | `likes = ' OR '.join([f"{type_expr} LIKE %s"] * len(normalized))` |
| `Api\routes\archives.py` | 86 | other | `clauses.append(f"({likes})")` |
| `Api\routes\archives.py` | 92 | metadata_filename | `"(p.file_name ILIKE %s OR COALESCE(p.file_path, '') ILIKE %s)"` |
| `Api\routes\archives.py` | 433 | other | `WHERE w.word ILIKE %s` |
| `Api\routes\archives.py` | 483 | other | `if search_query and search_query.lower() not in keyword_text.lower():` |
| `Api\routes\archives.py` | 506 | other | `if title_text and (not search_query or search_query.lower() in title_text.lower()):` |
| `Api\routes\archives.py` | 523 | other | `WHERE s.name ILIKE %s OR s.job ILIKE %s OR s.country ILIKE %s` |
| `Api\routes\archives.py` | 560 | other | `WHERE si.name ILIKE %s` |
| `Api\routes\archives.py` | 643 | other | `type_key = (file_type or raw_id).strip().lstrip('.').lower()` |
| `Api\routes\archives_api.py` | 183 | other | `filters['w.word'] = {'ILIKE': f'%{search}%'}` |
| `Api\routes\archives_api.py` | 192 | other | `sort_direction = SortDirection.DESC if sort_dir.lower() == 'desc' else SortDirection.ASC` |
| `Api\routes\archives_api.py` | 321 | other | `categories.sort(key=lambda x: x.get('file_count', 0), reverse=(sort_dir.lower() == 'desc'))` |
| `Api\routes\archives_api.py` | 323 | other | `categories.sort(key=lambda x: (x.get('name') or '').lower(), reverse=(sort_dir.lower() == 'desc'))` |
| `Api\routes\archives_api.py` | 371 | other | `count_query += " AND w.word ILIKE %s"` |
| `Api\routes\archives_api.py` | 441 | other | `sort_direction = SortDirection.DESC if sort_dir.lower() == 'desc' else SortDirection.ASC` |
| `Api\routes\archives_api.py` | 506 | other | `if search and search.lower() not in keyword_text.lower():` |
| `Api\routes\archives_api.py` | 518 | other | `keywords.sort(key=lambda x: (x.get('name') or '').lower(), reverse=(sort_dir.lower() == 'desc'))` |
| `Api\routes\archives_api.py` | 520 | other | `keywords.sort(key=lambda x: x.get('file_count', 0), reverse=(sort_dir.lower() == 'desc'))` |
| `Api\routes\archives_api.py` | 599 | other | `sort_order = request.args.get('sort_order', 'desc').lower()` |
| `Api\routes\archives_api.py` | 724 | other | `if search and search.lower() not in title_text.lower():` |
| `Api\routes\archives_api.py` | 741 | other | `titles.sort(key=lambda x: (x.get('name') or '').lower(), reverse=(sort_order == 'desc'))` |
| `Api\routes\archives_api.py` | 804 | other | `sort_order = request.args.get('sort_order', 'asc').lower()` |
| `Api\routes\archives_api.py` | 985 | other | `filters['s.name'] = {'ILIKE': f'%{search}%'}` |
| `Api\routes\archives_api.py` | 994 | other | `sort_direction = SortDirection.DESC if sort_dir.lower() == 'desc' else SortDirection.ASC` |
| `Api\routes\archives_api.py` | 1068 | other | `sources.sort(key=lambda x: x.get('file_count', 0), reverse=(sort_dir.lower() == 'desc'))` |
| `Api\routes\archives_api.py` | 1070 | other | `sources.sort(key=lambda x: (x.get('name') or '').lower(), reverse=(sort_dir.lower() == 'desc'))` |
| `Api\routes\archives_api.py` | 1118 | other | `count_query += " AND s.name ILIKE %s"` |
| `Api\routes\archives_api.py` | 1177 | other | `filters['si.name'] = {'ILIKE': f'%{search}%'}` |
| `Api\routes\archives_api.py` | 1186 | other | `sort_direction = SortDirection.DESC if sort_dir.lower() == 'desc' else SortDirection.ASC` |
| `Api\routes\archives_api.py` | 1258 | other | `sides.sort(key=lambda x: x.get('file_count', 0), reverse=(sort_dir.lower() == 'desc'))` |
| `Api\routes\archives_api.py` | 1260 | other | `sides.sort(key=lambda x: (x.get('name') or '').lower(), reverse=(sort_dir.lower() == 'desc'))` |
| `Api\routes\archives_api.py` | 1308 | other | `count_query += " AND si.name ILIKE %s"` |
| `Api\routes\archives_api.py` | 1446 | other | `sort_dir = str(request.args.get('sort_dir', 'desc')).lower()` |
| `Api\routes\archives_api.py` | 1560 | other | `filters['w.word'] = {'ILIKE': f'%{search}%'}` |
| `Api\routes\archives_api.py` | 1581 | other | `row.get('name') or  # 'w.word as name' alias (most likely)` |
| `Api\routes\archives_api.py` | 1627 | other | `sort_dir = 'asc' if str(request.args.get('sort_dir', 'desc')).strip().lower() == 'asc' else 'desc'` |
| `Api\routes\archives_api.py` | 1652 | metadata_filename | `filters['p.file_name'] = {'ILIKE': f'%{search}%'}` |
| `Api\routes\archives_api.py` | 1663 | other | `sort_direction = SortDirection.DESC if sort_dir.lower() == 'desc' else SortDirection.ASC` |
| `Api\routes\archives_api.py` | 1675 | metadata_filename | `where_conditions.append("p.file_name ILIKE %s")` |
| `Api\routes\archives_api.py` | 1686 | other | `order_clause = f"ORDER BY {sort_column} {sort_dir.upper()}"` |
| `Api\routes\archives_api.py` | 1804 | metadata_filename | `count_query += " AND p.file_name ILIKE %s"` |
| `Api\routes\archives_api.py` | 1842 | other | `sort_by = (request.args.get('sort_by', 'file_count') or 'file_count').strip().lower()` |
| `Api\routes\archives_api.py` | 1843 | other | `sort_dir = 'asc' if str(request.args.get('sort_dir', 'desc')).strip().lower() == 'asc' else 'desc'` |
| `Api\routes\archives_api.py` | 1846 | other | `LOWER(REPLACE(` |
| `Api\routes\archives_api.py` | 1850 | other | `OR UPPER(p.file_type) = 'FILE'` |
| `Api\routes\archives_api.py` | 1859 | other | `where_extra = f" AND {type_expr} ILIKE %s"` |
| `Api\routes\archives_api.py` | 1860 | other | `params.append(f"%{search.lower()}%")` |
| `Api\routes\archives_api.py` | 1863 | other | `'name': f'type_key {sort_dir.upper()}',` |
| `Api\routes\archives_api.py` | 1864 | other | `'id': f'type_key {sort_dir.upper()}',` |
| `Api\routes\archives_api.py` | 1865 | other | `'file_count': f'file_count {sort_dir.upper()}, type_key ASC',` |
| `Api\routes\archives_api.py` | 1866 | other | `'size': f'total_size {sort_dir.upper()}, type_key ASC',` |
| `Api\routes\archives_api.py` | 1908 | other | `type_key = (row[0] or 'unknown').lower()` |
| `Api\routes\categories.py` | 168 | other | `WHERE LOWER(w.word) = LOWER(%s)` |
| `Api\routes\categories.py` | 201 | other | `WHERE LOWER(w.word) = LOWER(%s)` |
| `Api\routes\categories.py` | 235 | other | `if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():` |
| `Api\routes\categories.py` | 354 | other | `if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():` |
| `Api\routes\categories.py` | 389 | other | `LOWER(w.word) as name_lower,` |
| `Api\routes\categories.py` | 395 | other | `GROUP BY LOWER(w.word)` |
| `Api\routes\categories.py` | 397 | other | `ORDER BY COUNT(*) DESC, LOWER(w.word)` |
| `Api\routes\categories.py` | 453 | other | `LOWER(w.word) as name_lower,` |
| `Api\routes\categories.py` | 457 | other | `GROUP BY LOWER(w.word)` |
| `Api\routes\common.py` | 274 | other | `# Cross-cutting features (page tips and the like) are state, so a` |
| `Api\routes\cursor_api.py` | 45 | other | `sort_direction_str = request.args.get('sort_direction', 'ASC').upper()` |
| `Api\routes\experience_api.py` | 130 | other | `wanted = declared.lower() in ("1", "true", "yes")` |
| `Api\routes\exports.py` | 209 | other | `sort_dir = 'asc' if str(request.args.get('sort_dir', 'desc')).strip().lower() == 'asc' else 'desc'` |
| `Api\routes\exports.py` | 228 | metadata_filename | `where_conditions.append("p.file_name ILIKE %s")` |
| `Api\routes\exports.py` | 255 | other | `ORDER BY {sort_column} {sort_dir.upper()} NULLS LAST, p.id DESC` |
| `Api\routes\exports.py` | 355 | other | `order_by = f"{LIST_SORT_COLUMNS[sort_key]} {sort_order.upper()} NULLS LAST, p.id DESC"` |
| `Api\routes\exports.py` | 467 | other | `clauses.append("s.name ILIKE %s")` |
| `Api\routes\exports.py` | 481 | other | `order_by = f"{columns[sort_by]} {sort_order.upper()} NULLS LAST, s.id DESC"` |
| `Api\routes\exports.py` | 535 | other | `clauses.append("si.name ILIKE %s")` |
| `Api\routes\exports.py` | 549 | other | `order_by = f"{columns[sort_by]} {sort_order.upper()} NULLS LAST, si.id DESC"` |
| `Api\routes\exports.py` | 838 | other | `export_format = (request.args.get('format') or 'csv').lower()` |
| `Api\routes\file_analysis.py` | 12 | content_or_path | `-> ``*_hashs`` -> ``hash_contexts`` -> ``paths``, exactly like the legacy` |
| `Api\routes\file_analysis.py` | 276 | other | `where = "WHERE w.word ILIKE %s" if search else ""` |
| `Api\routes\file_analysis.py` | 335 | other | `items.sort(key=lambda x: (-x['file_count'], x['name'].lower()))` |
| `Api\routes\file_analysis.py` | 460 | other | `page_items = [k for k in page_items if search.lower() in k['name'].lower()]` |
| `Api\routes\file_analysis.py` | 480 | other | `where = "WHERE w.word ILIKE %s" if search else ""` |
| `Api\routes\file_analysis.py` | 540 | other | `if search and search.lower() not in text.lower():` |
| `Api\routes\file_analysis.py` | 551 | other | `items.sort(key=lambda x: (-x['file_count'], x['name'].lower()))` |
| `Api\routes\file_analysis.py` | 570 | other | `where = "WHERE s.name ILIKE %s" if search else ""` |
| `Api\routes\file_analysis.py` | 597 | other | `where = "WHERE si.name ILIKE %s" if search else ""` |
| `Api\routes\file_analysis.py` | 836 | other | `force = request.args.get('force', 'false').lower() in ('1', 'true', 'yes')` |
| `Api\routes\file_operations.py` | 117 | other | `if source.suffix and not new_disk_name.lower().endswith(source.suffix.lower()):` |
| `Api\routes\import_export.py` | 140 | other | `include_data = request.args.get('include_data', 'true').lower() == 'true'` |
| `Api\routes\import_export.py` | 190 | other | `restore_data = request.args.get('restore_data', 'false').lower() == 'true'` |
| `Api\routes\interfaces_api.py` | 45 | other | `wanted = domain.upper()` |
| `Api\routes\keywords.py` | 82 | other | `is_duplicate = keyword_text.lower().strip() in keyword_texts` |
| `Api\routes\keywords.py` | 84 | other | `keyword_texts[keyword_text.lower().strip()] = True` |
| `Api\routes\keywords.py` | 161 | other | `word_id = get_word_id(keyword_text.lower())` |
| `Api\routes\keywords.py` | 180 | other | `word_id = get_word_id(word.lower())` |
| `Api\routes\keywords.py` | 230 | other | `if any(pattern in text.lower() for pattern in dangerous_patterns):` |
| `Api\routes\keywords.py` | 472 | other | `domain_mode = (request.args.get('domain_mode') or 'exact').strip().lower()` |
| `Api\routes\keywords.py` | 647 | other | `if query.lower() not in keyword_text.lower():` |
| `Api\routes\keywords.py` | 668 | other | `all_formatted_keywords.sort(key=lambda x: (x.get('text') or '').lower(), reverse=(sort_order == 'desc'))` |
| `Api\routes\keywords.py` | 699 | other | `order_clause = f"ORDER BY {sort_column} {sort_order.upper()}"` |
| `Api\routes\keywords.py` | 795 | other | `formatted_keywords.sort(key=lambda x: (x.get('text') or '').lower(), reverse=reverse_order)` |
| `Api\routes\keywords.py` | 1292 | other | `if any(pattern in keyword_text.lower() for pattern in dangerous_patterns):` |
| `Api\routes\keywords.py` | 1304 | other | `word_id = get_word_id(word.lower())` |
| `Api\routes\keywords.py` | 1424 | other | `normalized_text = keyword_text.lower().strip()` |
| `Api\routes\keywords.py` | 1571 | other | `domain_mode = (request.args.get('domain_mode') or 'exact').strip().lower()` |
| `Api\routes\map_api.py` | 202 | other | `name = (upload.filename or "").lower()` |
| `Api\routes\notifications.py` | 105 | other | `unread_only = request.args.get('unread_only', 'false').lower() == 'true'` |
| `Api\routes\notifications_page.py` | 32 | other | `'title': "LOWER(a.title)",` |
| `Api\routes\notifications_page.py` | 79 | other | `show_read = request.args.get('show_read', 'false').lower() == 'true'` |
| `Api\routes\notifications_page.py` | 82 | other | `read_status = (raw_read_status or 'all').strip().lower()` |
| `Api\routes\notifications_page.py` | 112 | other | `# Case-insensitive substring search (escaped LIKE wildcards)` |
| `Api\routes\notifications_page.py` | 121 | other | `"(a.title ILIKE %s ESCAPE '\\' OR "` |
| `Api\routes\notifications_page.py` | 122 | other | `"a.message ILIKE %s ESCAPE '\\' OR "` |
| `Api\routes\notifications_page.py` | 123 | metadata_filename | `"COALESCE(a.file_name, '') ILIKE %s ESCAPE '\\')"` |
| `Api\routes\operations_api.py` | 469 | other | `# staging directory, which a job then ingests like any other path. Session` |
| `Api\routes\operations_api.py` | 536 | other | `declared_hash = str(data.get("sha256") or "").strip().lower()` |
| `Api\routes\operations_api.py` | 583 | other | `declared = (request.form.get("sha256") or "").strip().lower()` |
| `Api\routes\operations_api.py` | 722 | other | `return str(value).strip().lower() in ("1", "true", "yes", "on")` |
| `Api\routes\performance.py` | 39 | other | `include_index_analysis = request.args.get('include_index_analysis', 'true').lower() == 'true'` |
| `Api\routes\performance.py` | 151 | other | `if request.args.get('include_entries', 'false').lower() == 'true':` |
| `Api\routes\places.py` | 117 | other | `language = str(data.get("language") or "en").strip().lower()` |
| `Api\routes\places.py` | 120 | other | `name_type = str(data.get("name_type") or "variant").strip().lower()` |
| `Api\routes\places.py` | 187 | other | `country = (request.args.get("country") or "").upper() or None` |
| `Api\routes\places.py` | 194 | other | `order = request.args.get("order", "asc").lower()` |
| `Api\routes\places.py` | 195 | other | `place_sort = {"label": "lower(p.label)", "place_key": "p.place_key",` |
| `Api\routes\places.py` | 224 | other | `like = match_key(q).lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")` |
| `Api\routes\places.py` | 227 | other | `"(p.label ILIKE %s OR p.place_key ILIKE %s OR EXISTS "` |
| `Api\routes\places.py` | 229 | other | `"AND lower(n.match_key) LIKE %s AND n.language = %s))"` |
| `Api\routes\places.py` | 231 | other | `params.extend([f"%{q}%", f"%{q}%", like + "%", language])` |
| `Api\routes\places.py` | 234 | other | `"(p.label ILIKE %s OR p.place_key ILIKE %s OR EXISTS "` |
| `Api\routes\places.py` | 236 | other | `"AND lower(n.match_key) LIKE %s))"` |
| `Api\routes\places.py` | 238 | other | `params.extend([f"%{q}%", f"%{q}%", like + "%"])` |
| `Api\routes\places.py` | 256 | other | `f" ORDER BY {place_sort[sort]} {order.upper()}, p.place_key ASC LIMIT %s OFFSET %s",` |
| `Api\routes\places.py` | 305 | other | `feature_type = str(data.get("feature_type") or "").strip().lower()` |
| `Api\routes\places.py` | 315 | other | `code = str(raw_code).strip().upper()` |
| `Api\routes\places.py` | 338 | other | `slug = "".join(c if c.isalnum() else "_" for c in label.lower()).strip("_")[:40]` |
| `Api\routes\places.py` | 442 | other | `value = str(data["feature_type"] or "").strip().lower()` |
| `Api\routes\places.py` | 451 | other | `code = str(raw).strip().upper()` |
| `Api\routes\places.py` | 560 | other | `order = request.args.get("order", "asc").lower()` |
| `Api\routes\places.py` | 561 | other | `sort_columns = {"name": "lower(n.name)", "language": "n.language",` |
| `Api\routes\places.py` | 562 | other | `"name_type": "n.name_type", "place_label": "lower(p.label)",` |
| `Api\routes\places.py` | 598 | other | `where.append("(n.name ILIKE %s OR p.label ILIKE %s OR p.place_key ILIKE %s"` |
| `Api\routes\places.py` | 599 | other | `" OR lower(n.match_key) LIKE %s)")` |
| `Api\routes\places.py` | 600 | other | `normalized_like = (match_key(q).lower().replace("\\", "\\\\")` |
| `Api\routes\places.py` | 613 | other | `f" ORDER BY {sort_columns[sort]} {order.upper()}, n.id ASC LIMIT %s OFFSET %s",` |
| `Api\routes\places.py` | 798 | other | `order = request.args.get("order", "desc").lower()` |
| `Api\routes\places.py` | 805 | other | `where = "(seed_version ILIKE %s OR loaded_by ILIKE %s OR content_sha256 ILIKE %s OR fingerprint ILIKE %s)"` |
| `Api\routes\places.py` | 806 | other | `like = f"%{q}%"` |
| `Api\routes\places.py` | 807 | other | `params = [like, like, like, like]` |
| `Api\routes\places.py` | 813 | other | `f" ORDER BY {LOAD_SORT[sort]} {order.upper()}, id DESC LIMIT %s OFFSET %s",` |
| `Api\routes\preview.py` | 96 | other | `mimetype=match.group(1).lower(),` |
| `Api\routes\schedules.py` | 25 | other | `(administrators only, like the manual triggers).` |
| `Api\routes\search.py` | 49 | other | `return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}` |
| `Api\routes\search.py` | 59 | other | `if len(values) == 1 and values[0].lower() == 'none':` |
| `Api\routes\search.py` | 192 | other | `"""Enhanced Search with Content Filtering - Uses Google-like search algorithm"""` |
| `Api\routes\search.py` | 215 | other | `# Use Google-like search: supports multiple words, partial words, numbers` |
| `Api\routes\search.py` | 257 | other | `"""Advanced Search with Multiple Filters - Uses Google-like search algorithm"""` |
| `Api\routes\search.py` | 288 | other | `# Use Google-like search: supports multiple words, partial words, numbers` |
| `Api\routes\search.py` | 495 | other | `sort_by = str(data.get('sort_by', 'relevance')).strip().lower()` |
| `Api\routes\search.py` | 496 | other | `sort_order = str(data.get('sort_order', 'desc')).strip().lower()` |
| `Api\routes\search.py` | 528 | other | `).strip().lower()` |
| `Api\routes\sides.py` | 45 | other | `order_by = f"{SORT_COLUMNS[sort_by]} {sort_order.upper()} NULLS LAST, si.id DESC"` |
| `Api\routes\sides.py` | 52 | other | `where = "WHERE si.name ILIKE %s" if search else ""` |
| `Api\routes\signals.py` | 319 | other | `# list must not look like "there are no other sources".` |
| `Api\routes\sources.py` | 47 | other | `order_by = f"{SORT_COLUMNS[sort_by]} {sort_order.upper()} NULLS LAST, s.id DESC"` |
| `Api\routes\sources.py` | 56 | other | `where = "WHERE s.name ILIKE %s" if search else ""` |
| `Api\routes\translations.py` | 139 | other | `# interactive read like the theme: under the 600/hour default the catalog was` |
| `Api\services\analysis_stats.py` | 132 | other | `"""How long the waiting queue is likely to take, given a measured average.` |
| `Api\services\analyst_categories.py` | 49 | other | `# One LIKE-escaping implementation for the whole product (core/criteria/sql.py).` |
| `Api\services\analyst_categories.py` | 109 | other | `ORDER BY LOWER(ac.name)` |
| `Api\services\analyst_categories.py` | 119 | other | `ORDER BY LOWER(ac.name)` |
| `Api\services\analyst_categories.py` | 189 | other | `"SELECT id FROM analyst_categories WHERE LOWER(name) = LOWER(%s)",` |
| `Api\services\analyst_categories.py` | 226 | other | `if "unique" in str(e).lower() or "duplicate" in str(e).lower():` |
| `Api\services\analyst_categories.py` | 273 | other | `if "unique" in str(e).lower() or "duplicate" in str(e).lower():` |
| `Api\services\analyst_categories.py` | 352 | other | `"SELECT id FROM analyst_categories WHERE LOWER(name) = LOWER(%s)",` |
| `Api\services\analyst_categories.py` | 660 | other | `conditions.append("afc.source_query ILIKE %s")` |
| `Api\services\analyst_categories.py` | 663 | metadata_filename | `conditions.append("(p.file_name ILIKE %s OR p.file_path ILIKE %s)")` |
| `Api\services\analyst_categories.py` | 783 | other | `ORDER BY LOWER(ac.name)` |
| `Api\services\document_analysis.py` | 168 | other | `category_terms.sort(key=lambda t: (-t['count'], t['term'].lower()))` |
| `Api\services\document_analysis.py` | 205 | other | `key = (name.lower(),) + extras` |
| `Api\services\document_analysis.py` | 213 | other | `out.sort(key=lambda row: (-row['count'], str(row.get(name_key) or '').lower()))` |
| `Api\services\document_analysis.py` | 287 | other | `key = v.lower()` |
| `Api\services\document_intelligence.py` | 101 | other | `extension = Path(name).suffix.lower()` |
| `Api\services\document_intelligence.py` | 251 | other | `source = _text_value(text).lower()` |
| `Api\services\file_navigation.py` | 188 | metadata_filename | `parts.append("p.file_name ILIKE %s")` |
| `Api\services\file_navigation.py` | 217 | other | `# empty segment is dropped, and a set filters with ANY, not LIKE.` |
| `Api\services\file_preview.py` | 138 | metadata_filename | `file_ext = Path(file_name).suffix.lower() if file_name else ''` |
| `Api\services\import_service.py` | 310 | other | `backup_type = str(backup_col['type']).upper()` |
| `Api\services\import_service.py` | 311 | other | `current_type = current_col['type'].upper()` |
| `Api\services\original_file.py` | 46 | other | `#: Text-like files shown as source text (always served as text/plain).` |
| `Api\services\original_file.py` | 147 | other | `extension = Path(name).suffix.lower() or Path(stored_path).suffix.lower()` |
| `Api\services\original_file.py` | 235 | other | `suffix = path_obj.suffix.lower()` |
| `Api\services\original_file.py` | 236 | other | `if suffix and not cleaned.lower().endswith(suffix):` |
| `Api\services\original_file.py` | 239 | other | `extension = Path(name).suffix.lower() or path_obj.suffix.lower()` |
| `Api\services\search_algorithms.py` | 3 | other | `Implements Google-like and social media search algorithms including:` |
| `Api\services\search_algorithms.py` | 130 | other | `words = [w.lower() for w in words if len(w) > 1 or w.isalnum()]` |
| `Api\services\search_algorithms.py` | 170 | other | `terms = query.lower().split()` |
| `Api\services\search_algorithms.py` | 211 | other | `return difflib.SequenceMatcher(None, seq1.lower(), seq2.lower()).ratio()` |
| `Api\services\search_algorithms.py` | 250 | other | `return difflib.get_close_matches(query.lower(), [c.lower() for c in candidates], n=n, cutoff=cutoff)` |
| `Api\services\search_algorithms.py` | 345 | metadata_filename | `file_name = document.get('file_name', '').lower()` |
| `Api\services\search_algorithms.py` | 346 | other | `query_lower = query.lower()` |
| `Api\services\search_algorithms.py` | 361 | metadata_filename | `file_name = document.get('file_name', '').lower()` |
| `Api\services\search_algorithms.py` | 362 | other | `query_lower = query.lower()` |
| `Api\services\search_algorithms.py` | 369 | other | `content = document.get('content', '').lower()` |
| `Api\services\search_algorithms.py` | 384 | other | `Detect search intent from query - Google-like parsing.` |
| `Api\services\search_algorithms.py` | 393 | other | `query_lower = query.lower()` |
| `Api\services\search_algorithms.py` | 420 | other | `if part.upper() in ['AND', 'OR', 'NOT']:` |
| `Api\services\search_algorithms.py` | 421 | other | `current_operator = part.upper()` |
| `Api\services\search_algorithms.py` | 489 | other | `if ft in query.lower():` |
| `Api\services\search_algorithms.py` | 586 | other | `text_lower = text.lower()` |
| `Api\services\search_algorithms.py` | 587 | other | `query_lower = query.lower()` |
| `Api\services\search_export.py` | 292 | other | `text = str(item).strip().lower() if item is not None else ""` |
| `Api\services\search_export.py` | 312 | other | `return str(value).strip().lower() in ("1", "true", "yes", "on")` |
| `Api\services\search_export.py` | 344 | other | `scope = str(payload.get("export_scope") or "filtered").strip().lower()` |
| `Api\services\search_export.py` | 350 | other | `export_format = str(payload.get("format") or "csv").strip().lower()` |
| `Api\services\search_export.py` | 364 | other | `sort_by = str(payload.get("sort_by") or "relevance").strip().lower()` |
| `Api\services\search_export.py` | 365 | other | `sort_order = str(payload.get("sort_order") or "desc").strip().lower()` |
| `Api\services\search_export.py` | 390 | other | `analyst_scope = str(analyst_scope).strip().lower()` |
| `Api\services\search_history.py` | 50 | other | `# Add new search entry. `len(history) + 1` looks like a` |
| `Api\services\search_service.py` | 4 | other | `Now includes Google-like search algorithms: BM25, query expansion, fuzzy matching, autocomplete` |
| `Api\services\search_service.py` | 125 | other | `- Google-like BM25 ranking algorithm` |
| `Api\services\search_service.py` | 232 | other | `# Google-like search: supports partial words, multiple words, numbers, and partial text` |
| `Api\services\search_service.py` | 239 | other | `# Build search conditions using ILIKE for partial matching (Google-like)` |
| `Api\services\search_service.py` | 252 | other | `# Escape special characters for ILIKE` |
| `Api\services\search_service.py` | 256 | metadata_filename | `search_conditions.append(f"p.file_name ILIKE %s")` |
| `Api\services\search_service.py` | 268 | other | `AND w.word ILIKE %s` |
| `Api\services\search_service.py` | 273 | other | `# Combine all conditions with OR (Google-like: at least one term matches)` |
| `Api\services\search_service.py` | 350 | other | `order = 'DESC' if sort_order.lower() == 'desc' else 'ASC'` |
| `Api\services\search_service.py` | 360 | leading_wildcard | `WHEN p.file_name ILIKE '%%' || term || '%%' THEN 2.0` |
| `Api\services\search_service.py` | 368 | leading_wildcard | `AND w.word ILIKE '%%' || term || '%%'` |
| `Api\services\search_service.py` | 422 | other | `-- Google-like relevance: count matching search terms` |
| `Api\services\search_service.py` | 431 | leading_wildcard | `WHEN p.file_name ILIKE '%%' || term || '%%' THEN 2.0` |
| `Api\services\search_service.py` | 439 | leading_wildcard | `AND w.word ILIKE '%%' || term || '%%'` |
| `Api\services\search_service.py` | 641 | other | `# tabular files (CSV-like): slide/word tables would otherwise` |
| `Api\services\search_service.py` | 752 | other | `idx = line.lower().find(needle.lower())` |
| `Api\services\search_service.py` | 949 | other | `order = 'DESC' if sort_order.lower() == 'desc' else 'ASC'` |
| `Api\services\search_service.py` | 972 | other | `Simple search using ILIKE for backward compatibility.` |
| `Api\services\search_service.py` | 999 | other | `# Google-like search: build conditions for each term with OR logic` |
| `Api\services\search_service.py` | 1004 | other | `# Escape ILIKE wildcards only (see _escape_like).` |
| `Api\services\search_service.py` | 1008 | metadata_filename | `search_conditions.append("p.file_name ILIKE %s")` |
| `Api\services\search_service.py` | 1020 | other | `AND w.word ILIKE %s` |
| `Api\services\search_service.py` | 1055 | other | `-- Google-like relevance score` |
| `Api\services\search_service.py` | 1060 | leading_wildcard | `WHEN p.file_name ILIKE '%%' || term || '%%' THEN 2.0` |
| `Api\services\search_service.py` | 1068 | leading_wildcard | `AND w.word ILIKE '%%' || term || '%%'` |
| `Api\services\search_service.py` | 1146 | other | `Advanced search using Google-like algorithms (BM25, query expansion, fuzzy matching).` |
| `Api\services\search_service.py` | 1326 | other | `original_lower = {t.lower() for t in search_query.split()}` |
| `Api\services\search_service.py` | 1329 | other | `if t and t.lower() not in original_lower` |
| `Api\services\search_service.py` | 1356 | metadata_filename | `"p.file_name ILIKE %s" for _ in search_terms` |
| `Api\services\search_service.py` | 1378 | metadata_filename | `OR p.file_name ILIKE %s` |
| `Api\services\search_service.py` | 1388 | other | `OR w.word ILIKE %s` |
| `Api\services\search_service.py` | 1393 | other | `like_pattern = f'%{_escape_like(search_terms[0])}%'` |
| `Api\services\search_service.py` | 1394 | other | `core_params = [tsquery_terms, like_pattern, tsquery_terms, like_pattern]` |
| `Api\services\search_service.py` | 1400 | other | `# Also create ILIKE patterns for each term (fallback for better multi-word matching)` |
| `Api\services\search_service.py` | 1401 | other | `like_patterns = [f'%{_escape_like(term)}%' for term in search_terms]` |
| `Api\services\search_service.py` | 1408 | metadata_filename | `OR (p.file_name ILIKE ALL(ARRAY[%s]))` |
| `Api\services\search_service.py` | 1419 | other | `OR w.word ILIKE ANY(ARRAY[%s])` |
| `Api\services\search_service.py` | 1424 | other | `core_params = [tsquery_terms, like_patterns, tsquery_terms, like_patterns]` |
| `Api\services\search_service.py` | 1448 | metadata_filename | `p.file_name ILIKE ANY(ARRAY[{exp_placeholders}])` |
| `Api\services\search_service.py` | 1456 | other | `AND w.word ILIKE ANY(ARRAY[{exp_placeholders}])` |
| `Api\services\search_service.py` | 1512 | other | `# idx_afc_path_id so scoped searches perform like unscoped ones` |
| `Api\services\search_service.py` | 1563 | other | `sort_direction = 'ASC' if sort_order.lower() == 'asc' else 'DESC'` |
| `Api\services\search_service.py` | 1594 | other | `and sort_order.lower() == "desc"` |
| `Api\services\search_service.py` | 1788 | other | `reverse=(sort_order.lower() == 'desc'))` |
| `Api\services\search_service.py` | 1792 | other | `reverse=(sort_order.lower() == 'desc'))` |
| `Api\services\search_service.py` | 1795 | metadata_filename | `key=lambda x: x.get('file_name', '').lower(),` |
| `Api\services\search_service.py` | 1796 | other | `reverse=(sort_order.lower() == 'desc'))` |
| `Api\services\search_service.py` | 1799 | metadata_filename | `key=lambda x: (x.get('file_type', ''), x.get('file_name', '').lower()),` |
| `Api\services\search_service.py` | 1800 | other | `reverse=(sort_order.lower() == 'desc'))` |
| `Api\services\search_service.py` | 1804 | other | `reverse=(sort_order.lower() == 'desc'))` |
| `Api\services\search_service.py` | 1888 | other | `query_lower = query.strip().lower()` |
| `Api\services\search_service.py` | 1895 | metadata_filename | `WHERE LOWER(file_name) LIKE %s` |
| `Api\services\search_service.py` | 1909 | other | `WHERE LOWER(w.word) LIKE %s` |
| `Api\services\search_service.py` | 1924 | other | `if name and name.lower() not in seen:` |
| `Api\services\search_service.py` | 1930 | other | `seen.add(name.lower())` |
| `Api\services\search_service.py` | 1934 | other | `if word and word.lower() not in seen and len(word) >= 3:` |
| `Api\services\search_service.py` | 1940 | other | `seen.add(word.lower())` |
| `Api\services\search_service.py` | 1964 | other | `if match.lower() not in seen:` |
| `Api\services\search_service.py` | 1970 | other | `seen.add(match.lower())` |
| `Api\services\search_service.py` | 1974 | other | `0 if x['text'].lower().startswith(query_lower) else 1,` |
| `Api\services\search_service.py` | 1976 | other | `x['text'].lower()` |
| `Api\services\structured_folder_export.py` | 83 | other | `ext = (row.get("file_type") or "").strip().lower()` |
| `Api\services\structured_folder_export.py` | 162 | other | `scope = (scope or "selection").strip().lower()` |
| `Api\services\translation_management.py` | 139 | other | `if path.lower().startswith((` |
| `Api\services\translation_management.py` | 147 | other | `lowered = path.lower()` |
| `Api\services\translation_management.py` | 164 | other | `if len(parts) == 2 and stem.lower() == "base":` |
| `Api\utils\title.py` | 28 | other | `return sorted(titles, key=lambda x: str(x.get(sort_by, '')).lower(),` |
| `Api\utils\title.py` | 49 | other | `search_lower = search.lower()` |
| `Api\utils\title.py` | 52 | other | `if search_lower in title.get('name', '').lower()` |
| `Api\utils\title_similarity.py` | 25 | other | `text1_norm = text1.lower().strip()` |
| `Api\utils\title_similarity.py` | 26 | other | `text2_norm = text2.lower().strip()` |
| `Api\utils\utils.py` | 237 | other | `# Drop final part if it looks like a file (has extension)` |
| `Api\utils\utils.py` | 910 | other | `# Google-like search: supports partial words, multiple words, numbers, and partial text` |
| `Api\utils\utils.py` | 919 | other | `# Escape special characters for ILIKE` |
| `Api\utils\utils.py` | 924 | metadata_filename | `search_conditions.append("p.file_name ILIKE %s")` |
| `Api\utils\utils.py` | 933 | other | `AND w.word ILIKE %s` |
| `Api\utils\utils.py` | 938 | other | `# Combine all conditions with OR (Google-like: at least one term matches)` |
| `Api\utils\utils.py` | 994 | leading_wildcard | `WHEN p.file_name ILIKE '%%' || term || '%%' THEN 2.0` |
| `Api\utils\utils.py` | 999 | leading_wildcard | `AND w.word ILIKE '%%' || term || '%%'` |
| `Api\utils\utils.py` | 1365 | other | `where_sql = "WHERE w.word ILIKE %s"` |
| `Api\utils\utils.py` | 1531 | other | `where_parts.append("w.word ILIKE %s")` |
| `Api\utils\utils.py` | 1650 | other | `where_clauses.append("w.word ILIKE %s")` |
| `Api\utils\utils.py` | 1663 | other | `status_tiebreak = ', COUNT(DISTINCT p.id) {dir}, w.word'.format(dir=sort_order.upper()) if sort_by == 'status' else ', w.word'` |
| `Api\utils\utils.py` | 1678 | other | `ORDER BY {order_column} {sort_order.upper()}{status_tiebreak}` |
| `Api\utils\utils.py` | 1920 | other | `sort_direction = 'ASC' if str(sort_order).lower() == 'asc' else 'DESC'` |
| `Api\utils\utils.py` | 1966 | other | `search_lower = search_term.lower()` |
| `Api\utils\utils.py` | 1993 | other | `if search_term and search_lower not in keyword_text.lower():` |
| `Api\utils\utils.py` | 2001 | other | `key=lambda item: ((item[1] or '').lower(), item[0][0]),` |
| `Api\utils\utils.py` | 2139 | other | `where = "WHERE h.hash ILIKE %s"` |
| `Api\utils\utils.py` | 2262 | other | `SELECT LOWER(REPLACE(` |
| `Api\utils\utils.py` | 2266 | other | `OR UPPER(p.file_type) = 'FILE'` |
| `Api\utils\utils.py` | 2358 | other | `Search files by word(s) - Google-like search supporting multiple words and partial matching` |
| `Api\utils\utils.py` | 2383 | other | `# Google-like search: build conditions for each term with OR logic` |
| `Api\utils\utils.py` | 2389 | other | `# Escape special characters for ILIKE` |
| `Api\utils\utils.py` | 2394 | metadata_filename | `search_conditions.append("p.file_name ILIKE %s")` |
| `Api\utils\utils.py` | 2403 | other | `AND w.word ILIKE %s` |
| `Api\utils\utils.py` | 2436 | metadata_filename | `relevance_parts.append("CASE WHEN p.file_name ILIKE %s THEN 2.0 ELSE 0.0 END")` |
| `Api\utils\utils.py` | 2437 | expensive_word_scan | `relevance_parts.append("CASE WHEN EXISTS (SELECT 1 FROM words_hashs wp JOIN words w ON wp.word_id = w.id WHERE wp.hash_id = (SELECT c2.hash_` |
