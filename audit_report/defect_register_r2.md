# Defect register — round 2

Suite of record: `4326` tests, **114 failures, 12 errors, 134 skipped**
(`/tmp/full7.log`, `/tmp/junit_full7.xml`, per-test list `/tmp/fails7.txt`).
Baseline before this round was 121 failures / 12 errors (`/tmp/full5.log`).

Status vocabulary: **FIXED + VERIFIED** (repaired and proven green),
**OPEN** (real, not yet repaired), **NEEDS-DECISION** (cannot be repaired
without a choice from the user), **ENV-LIMIT** (cannot pass on this host),
**COLLATERAL** (fails only because another test damaged the shared database),
**TEST DEFECT** (the expectation is wrong, the product is right),
**DOC DRIFT** (generated artefact not committed).

## A. Fixed and verified this round

| ID | Defect | Fix | Proof |
|---|---|---|---|
| R2-01 | Job events `WARNING`/`FAILED` cannot be stored (`job_events_event_type_check`) | `stored_event()` translation at the repository boundary; original name kept in `payload.event_kind` | `tests/unit/test_job_event_storage_vocabulary.py` (5 tests, green) |
| R2-02 | `cancel()` writes status `CANCELLING`, absent from `ck_jobs_status`; recovery queried it | cancellation is a flag on a RUNNING job; status vocabulary untouched | `test_job_service.py::TestIngestionJobs` green |
| R2-03 | Reports dashboard has no unified-table engine | template rebuilt on `record_table` + new `reports-dashboard-page.js` + `UnifiedTable.init` | `test_one_load_more.py` all green |
| R2-04 | No reports query surface | `services/reporting/processing.py` + 5 routes + templates | `test_reports_pg.py` 7 passed |
| R2-05 | `Notification(file_name=…)` TypeError | test dropped stale kwargs (dataclass carries name/path in `metadata`) | `test_notification_accuracy.py` green except the protected index test |
| R2-06 | Recovery test asserted event name `FAILED` | asserts `JOB_FAILED`, the stored vocabulary | `test_crash_recovery_then_retry_no_duplicate_work` green |

## B. Remaining, by class

Counts: COLLATERAL 7, DOC DRIFT 24, ENV-LIMIT 29, NEEDS-DECISION 34, OPEN 29,
TEST DEFECT 3 = 126 findings (114 failures + 12 errors).

### COLLATERAL (7)

| Test | Reason |
|---|---|
| `tests.integration.test_lexis_cosmos_api::test_search_returns_the_files_of_a_scope_with_their_matches` | Only fails after test_startup_upgrade_path dropped analyst_* tables; passes in isolation |
| `tests.integration.test_structural_marker_exclusion::test_email_header_values_are_searchable` | Only fails after test_startup_upgrade_path dropped analyst_* tables; passes in isolation |
| `tests.integration.test_structural_marker_exclusion::test_labelled_text_value_is_searchable_without_label` | Only fails after test_startup_upgrade_path dropped analyst_* tables; passes in isolation |
| `tests.integration.test_structural_marker_exclusion::test_line_matches_exclude_structural_marker_lines` | Only fails after test_startup_upgrade_path dropped analyst_* tables; passes in isolation |
| `tests.integration.test_structural_marker_exclusion::test_real_content_is_searchable` | Only fails after test_startup_upgrade_path dropped analyst_* tables; passes in isolation |
| `tests.integration.test_structural_marker_exclusion::test_spreadsheet_cell_values_are_searchable` | Only fails after test_startup_upgrade_path dropped analyst_* tables; passes in isolation |
| `tests.integration.test_svg_status_reason::test_svg_text_is_indexed_and_searchable` | Only fails after test_startup_upgrade_path dropped analyst_* tables; passes in isolation |

### DOC DRIFT (24)

| Test | Reason |
|---|---|
| `tests.integration.test_interface_coverage.TestTheEvidenceReport::test_the_evidence_report_matches_the_application` | Generated documentation file not committed |
| `tests.unit.test_action_lifecycle_components.TestTheyAreDeclaredComponents::test_the_documentation_is_regenerated_from_the_library[confirm_dialog]` | Generated documentation file not committed |
| `tests.unit.test_action_lifecycle_components.TestTheyAreDeclaredComponents::test_the_documentation_is_regenerated_from_the_library[toast]` | Generated documentation file not committed |
| `tests.unit.test_action_surface_audit.TestTheDocumentIsGenerated::test_the_document_explains_itself_without_a_count_in_prose` | Generated documentation file not committed |
| `tests.unit.test_action_surface_audit.TestTheDocumentIsGenerated::test_the_document_is_what_the_product_now_says` | Generated documentation file not committed |
| `tests.unit.test_architecture_diagrams::test_architecture_has_mermaid_diagrams` | Generated documentation file not committed |
| `tests.unit.test_architecture_diagrams::test_job_state_diagram_matches_transitions` | Generated documentation file not committed |
| `tests.unit.test_component_library.TestTheDocumentCannotDrift::test_the_document_states_the_rules` | Generated documentation file not committed |
| `tests.unit.test_component_library.TestTheDocumentCannotDrift::test_the_generated_section_matches_the_components` | Generated documentation file not committed |
| `tests.unit.test_component_library.TestTheStateVocabularyIsComplete::test_the_document_calls_them_not_yet_rather_than_implying_coverage` | Generated documentation file not committed |
| `tests.unit.test_experience_contract.TestTheDocumentCannotDrift::test_the_document_has_no_hand_typed_counts` | Generated documentation file not committed |
| `tests.unit.test_experience_contract.TestTheDocumentCannotDrift::test_the_generated_block_matches` | Generated documentation file not committed |
| `tests.unit.test_interface_docs.TestEndpointInventory::test_every_record_carries_the_fields_the_directive_asks_for` | Generated documentation file not committed |
| `tests.unit.test_interface_docs.TestEndpointInventory::test_every_record_names_an_owner_or_an_exception` | Generated documentation file not committed |
| `tests.unit.test_interface_docs.TestEndpointInventory::test_the_inventory_is_sorted_so_a_new_page_shows_up_as_a_diff` | Generated documentation file not committed |
| `tests.unit.test_interface_docs.TestOtherDocuments::test_the_productization_map_points_at_the_registry` | Generated documentation file not committed |
| `tests.unit.test_interface_lifecycle.TestAllFiveConsumersAgree::test_the_generated_documentation_states_the_policy` | Generated documentation file not committed |
| `tests.unit.test_interface_lifecycle.TestTheRegistryIsFrozen::test_the_freeze_is_written_down` | Generated documentation file not committed |
| `tests.unit.test_licensing::test_every_vendored_file_is_in_the_notices` | Generated documentation file not committed |
| `tests.unit.test_ocr_provenance_docs::test_every_documented_ocr_field_is_stored` | Generated documentation file not committed |
| `tests.unit.test_ocr_provenance_docs::test_every_stored_ocr_field_is_documented` | Generated documentation file not committed |
| `tests.unit.test_screen_inspector.TestTheEvidenceIsMeasuredNotWritten::test_the_document_explains_itself_without_a_count_in_prose` | Generated documentation file not committed |
| `tests.unit.test_screen_inspector.TestTheEvidenceIsMeasuredNotWritten::test_the_document_is_what_the_product_now_says` | Generated documentation file not committed |
| `tests.unit.test_windows_offline_kit.TestDependencyInventory::test_the_committed_inventory_matches_the_generator` | Generated documentation file not committed |

### ENV-LIMIT (29)

| Test | Reason |
|---|---|
| `tests.unit.test_date_and_orientation::test_pdf_page_rotated_image_text_extraction[180]` | No OCR engine binary in this sandbox |
| `tests.unit.test_date_and_orientation::test_pdf_page_rotated_image_text_extraction[270]` | No OCR engine binary in this sandbox |
| `tests.unit.test_date_and_orientation::test_pdf_page_rotated_image_text_extraction[90]` | No OCR engine binary in this sandbox |
| `tests.unit.test_date_and_orientation::test_standalone_rotated_image_text_extraction[180]` | No OCR engine binary in this sandbox |
| `tests.unit.test_date_and_orientation::test_standalone_rotated_image_text_extraction[270]` | No OCR engine binary in this sandbox |
| `tests.unit.test_date_and_orientation::test_standalone_rotated_image_text_extraction[90]` | No OCR engine binary in this sandbox |
| `tests.unit.test_embedded_images::test_docx_embedded_image_carries_ocr_provenance` | No OCR engine binary in this sandbox |
| `tests.unit.test_embedded_images::test_docx_embedded_image_is_extracted` | No OCR engine binary in this sandbox |
| `tests.unit.test_embedded_images::test_docx_embedded_image_keeps_its_part_name` | No OCR engine binary in this sandbox |
| `tests.unit.test_embedded_images::test_docx_embedded_image_text_was_ocrd` | No OCR engine binary in this sandbox |
| `tests.unit.test_embedded_images::test_pptx_embedded_image_is_extracted` | No OCR engine binary in this sandbox |
| `tests.unit.test_embedded_images::test_pptx_publishes_extraction_path_without_a_result_dict` | No OCR engine binary in this sandbox |
| `tests.unit.test_embedded_images::test_reader_publishes_extraction_path_so_the_router_can_recurse` | No OCR engine binary in this sandbox |
| `tests.unit.test_embedded_images::test_xlsx_embedded_image_is_extracted` | No OCR engine binary in this sandbox |
| `tests.unit.test_ocr_engines.TestImageReaderOcr::test_blank_image_yields_no_text_and_no_hallucination` | No OCR engine binary in this sandbox |
| `tests.unit.test_ocr_engines.TestImageReaderOcr::test_blocks_carry_confidence_and_bbox` | No OCR engine binary in this sandbox |
| `tests.unit.test_ocr_engines.TestImageReaderOcr::test_printed_text_is_extracted_with_provenance` | No OCR engine binary in this sandbox |
| `tests.unit.test_ocr_matrix.TestMixedPdf::test_both_layers_survive` | No OCR engine binary in this sandbox |
| `tests.unit.test_ocr_matrix.TestMultiPagePdf::test_every_page_is_ocrd_in_order` | No OCR engine binary in this sandbox |
| `tests.unit.test_ocr_matrix.TestNoText::test_blank_image_yields_nothing` | No OCR engine binary in this sandbox |
| `tests.unit.test_ocr_matrix.TestOrdinaryText::test_extracted_with_full_provenance` | No OCR engine binary in this sandbox |
| `tests.unit.test_ocr_matrix.TestResolution::test_high_resolution` | No OCR engine binary in this sandbox |
| `tests.unit.test_ocr_matrix.TestResolution::test_very_large_image_is_not_refused` | No OCR engine binary in this sandbox |
| `tests.unit.test_ocr_selfcheck.TestRequire::test_the_fallback_engine_passes_when_it_is_the_one_required` | No OCR engine binary in this sandbox |
| `tests.unit.test_ocr_selfcheck::test_the_host_engine_reads_every_sample` | No OCR engine binary in this sandbox |
| `tests.unit.test_pdf_text_layer.TestScannedPdfUsesFallbackEngine::test_blank_scanned_page_falls_back_without_hallucinating` | No OCR engine binary in this sandbox |
| `tests.unit.test_pdf_text_layer.TestScannedPdfUsesFallbackEngine::test_document_is_not_flagged_as_no_engine` | No OCR engine binary in this sandbox |
| `tests.unit.test_pdf_text_layer.TestScannedPdfUsesFallbackEngine::test_engine_exists_so_ocr_is_not_skipped` | No OCR engine binary in this sandbox |
| `tests.unit.test_pdf_text_layer.TestScannedPdfUsesFallbackEngine::test_scanned_page_yields_recognised_text_with_provenance` | No OCR engine binary in this sandbox |

### NEEDS-DECISION (34)

| Test | Reason |
|---|---|
| `tests.integration.test_notification_accuracy::test_alert_indexes_exist` | Asserts a constraint/index/migration name the frozen schema does not use (D-2) |
| `tests.integration.test_places_crud_pg::test_admin_curates_place_names_with_fingerprint_revision_and_audit` | Places/gazetteer design is deferred (D-4) |
| `tests.integration.test_places_crud_pg::test_place_names_and_immutable_load_history_are_browsable` | Places/gazetteer design is deferred (D-4) |
| `tests.integration.test_places_crud_pg::test_place_search_sort_pagination_and_mutation_authorization` | Places/gazetteer design is deferred (D-4) |
| `tests.integration.test_places_pg::test_migration_created_gazetteer_tables` | Places/gazetteer design is deferred (D-4) |
| `tests.integration.test_places_pg::test_sync_seed_loads_gazetteer` | Places/gazetteer design is deferred (D-4) |
| `tests.integration.test_saved_searches_pg::test_constraints_reject_invalid_rows[overrides0-ck_saved_searches_name_nonempty]` | Asserts a constraint/index/migration name the frozen schema does not use (D-2) |
| `tests.integration.test_saved_searches_pg::test_constraints_reject_invalid_rows[overrides1-ck_saved_searches_fingerprint_hex]` | Asserts a constraint/index/migration name the frozen schema does not use (D-2) |
| `tests.integration.test_saved_searches_pg::test_constraints_reject_invalid_rows[overrides2-ck_saved_searches_legacy_pair]` | Asserts a constraint/index/migration name the frozen schema does not use (D-2) |
| `tests.integration.test_scenario_engine_pg::test_an_owner_who_lost_the_privilege_disables_the_scenario` | Helper selects alerts.rule_id/rule_evaluation_id; SQL-vs-Python priority mismatch (D-1) |
| `tests.integration.test_scenario_engine_pg::test_baseline_then_notification_with_provenance` | Helper selects alerts.rule_id/rule_evaluation_id; SQL-vs-Python priority mismatch (D-1) |
| `tests.integration.test_scenario_engine_pg::test_notifications_are_capped_with_an_explicit_overflow_summary` | Helper selects alerts.rule_id/rule_evaluation_id; SQL-vs-Python priority mismatch (D-1) |
| `tests.integration.test_scenario_engine_pg::test_notify_existing_dry_run_counts_the_notifications` | Helper selects alerts.rule_id/rule_evaluation_id; SQL-vs-Python priority mismatch (D-1) |
| `tests.integration.test_scenario_engine_pg::test_sql_priority_agrees_with_the_python_rule` | Helper selects alerts.rule_id/rule_evaluation_id; SQL-vs-Python priority mismatch (D-1) |
| `tests.integration.test_signal_explorer_pg::test_explorer_filters_and_paginates_deterministically` | Protected test (do-not-edit list) |
| `tests.integration.test_signal_explorer_pg::test_signal_detail_carries_run_versions_and_occurrences` | Protected test (do-not-edit list) |
| `tests.integration.test_signal_ingestion::test_signal_constraints[over0-ck_content_signals_resolved_has_range]` | Asserts a constraint/index/migration name the frozen schema does not use (D-2) |
| `tests.integration.test_signal_ingestion::test_signal_constraints[over1-ck_content_signals_resolved_has_range]` | Asserts a constraint/index/migration name the frozen schema does not use (D-2) |
| `tests.integration.test_signal_ingestion::test_signal_constraints[over2-ck_content_signals_range_pair]` | Asserts a constraint/index/migration name the frozen schema does not use (D-2) |
| `tests.integration.test_signal_ingestion::test_signal_constraints[over3-ck_content_signals_range_order]` | Asserts a constraint/index/migration name the frozen schema does not use (D-2) |
| `tests.integration.test_signal_ingestion::test_signal_constraints[over4-ck_content_signals_relative_anchor]` | Asserts a constraint/index/migration name the frozen schema does not use (D-2) |
| `tests.integration.test_signal_ingestion::test_signal_constraints[over5-ck_content_signals_offsets]` | Asserts a constraint/index/migration name the frozen schema does not use (D-2) |
| `tests.integration.test_signal_ingestion::test_signal_constraints[over6-ck_content_signals_dedup_hex]` | Asserts a constraint/index/migration name the frozen schema does not use (D-2) |
| `tests.integration.test_signal_ingestion::test_signal_constraints[over7-ck_content_signals_type]` | Asserts a constraint/index/migration name the frozen schema does not use (D-2) |
| `tests.integration.test_structured_content_display::test_migration_m0010_created_contents_raw` | Asserts a constraint/index/migration name the frozen schema does not use (D-2) |
| `tests.integration.test_title_parent_linkage::test_foreign_key_still_enforced` | Protected test (do-not-edit list): TypeError/KeyError inside the test helper |
| `tests.integration.test_title_parent_linkage::test_linkage_is_retrievable_from_the_child` | Protected test (do-not-edit list): TypeError/KeyError inside the test helper |
| `tests.integration.test_title_parent_linkage::test_omitting_a_parent_still_works` | Protected test (do-not-edit list): TypeError/KeyError inside the test helper |
| `tests.integration.test_title_parent_linkage::test_parent_linkage_is_persisted` | Protected test (do-not-edit list): TypeError/KeyError inside the test helper |
| `tests.unit.test_gazetteer_packaging::test_seed_inputs_exist` | Places/gazetteer design is deferred (D-4) |
| `tests.unit.test_identifiers_intel::test_detects_email_phone_ipv4_and_links_to_sentence` | Protected test (do-not-edit list): TypeError/KeyError inside the test helper |
| `tests.unit.test_identifiers_intel::test_email_not_double_counted_as_ipv4_fragment` | Protected test (do-not-edit list): TypeError/KeyError inside the test helper |
| `tests.unit.test_interface_docs.TestGeneratedBlock::test_the_block_matches_the_registry` | Asserts a constraint/index/migration name the frozen schema does not use (D-2) |
| `tests.unit.test_notification_volume_guards::test_alert_index_migration_has_a_unique_version` | Asserts a constraint/index/migration name the frozen schema does not use (D-2) |

### OPEN (29)

| Test | Reason |
|---|---|
| `tests.e2e.test_frontend_workflow.TestFrontendIngestionWorkflow::test_upload_ingest_monitor_search` | See the test |
| `tests.integration.test_db_integrity_audit::test_no_duplicate_index_shape_remains` | Duplicate index shapes in the baseline; needs a register or a migration (D-8) |
| `tests.integration.test_interface_coverage.TestTheEvidenceReport::test_the_endpoint_inventory_matches_the_application` | See the test |
| `tests.integration.test_keyword_search_bounded::test_a_database_error_in_api_search_is_an_error_response` | See the test |
| `tests.integration.test_signal_ingestion::test_failed_run_requires_error_and_deleting_content_cascades` | Cascade/event expectation on signal ingestion |
| `tests.integration.test_translation_coverage::test_no_catalog_entry_is_empty_or_fuzzy[ar]` | Pre-existing catalogue translation gap (ar/he/fa/hr) |
| `tests.integration.test_translation_coverage::test_no_catalog_entry_is_empty_or_fuzzy[fa]` | Pre-existing catalogue translation gap (ar/he/fa/hr) |
| `tests.integration.test_translation_coverage::test_no_catalog_entry_is_empty_or_fuzzy[he]` | Pre-existing catalogue translation gap (ar/he/fa/hr) |
| `tests.integration.test_translation_coverage::test_no_catalog_entry_is_empty_or_fuzzy[hr]` | Pre-existing catalogue translation gap (ar/he/fa/hr) |
| `tests.unit.test_analytics_measures::test_keyness_sql_level_is_the_threshold` | Imports core.reporting, which does not exist in the tree |
| `tests.unit.test_bandit_triage_fixes::test_anchored_validators_match_the_whole_value[core.reporting.model-_HELP_TOPIC-reports/keyword]` | Imports core.reporting, which does not exist in the tree |
| `tests.unit.test_bandit_triage_fixes::test_anchored_validators_match_the_whole_value[core.reporting.model-_ID-keyword.summary]` | Imports core.reporting, which does not exist in the tree |
| `tests.unit.test_component_library.TestAdoption::test_the_audit_counts_the_hand_written_markup` | Adoption audit counts 12 hand-written blocks vs 9 expected |
| `tests.unit.test_interface_docs.TestCountsAreGenerated::test_the_document_states_no_endpoint_count_of_its_own` | See the test |
| `tests.unit.test_interface_docs.TestEndpointInventory::test_the_inventory_is_committed_and_parses` | See the test |
| `tests.unit.test_interface_docs.TestGeneratedBlock::test_regeneration_is_idempotent` | See the test |
| `tests.unit.test_interface_docs.TestGeneratedBlock::test_splicing_preserves_the_prose` | See the test |
| `tests.unit.test_interface_docs.TestGeneratedBlock::test_the_document_embeds_a_generated_block` | See the test |
| `tests.unit.test_interface_docs.TestOtherDocuments::test_the_domain_model_exists` | See the test |
| `tests.unit.test_interface_docs.TestRegistryEvidence::test_every_required_evidence_item_is_present` | See the test |
| `tests.unit.test_interface_docs.TestRegistryEvidence::test_regeneration_is_idempotent` | See the test |
| `tests.unit.test_interface_docs.TestRegistryEvidence::test_the_coverage_claim_is_stated_as_zero_unmanaged` | See the test |
| `tests.unit.test_interface_docs.TestRegistryEvidence::test_the_document_embeds_both_generated_blocks` | See the test |
| `tests.unit.test_interface_docs.TestRegistryEvidence::test_the_document_reports_what_remains_legacy` | See the test |
| `tests.unit.test_interface_docs.TestRegistryEvidence::test_the_registry_half_matches_the_registry` | See the test |
| `tests.unit.test_licensing::test_checker_cli_exits_zero_on_this_environment` | Packaging/licence statement gap (D-6) |
| `tests.unit.test_licensing::test_installed_dependencies_are_agpl_compatible` | Packaging/licence statement gap (D-6) |
| `tests.unit.test_licensing::test_pyproject_declares_the_licence` | Packaging/licence statement gap (D-6) |
| `tests.unit.test_licensing::test_readme_and_docs_state_the_licence` | Packaging/licence statement gap (D-6) |

### TEST DEFECT (3)

| Test | Reason |
|---|---|
| `tests.integration.test_db_integrity_audit::test_an_out_of_vocabulary_value_is_reported_and_fails_the_gate` | Imports a migration module that is not in the frozen chain |
| `tests.integration.test_startup_upgrade_path::test_startup_applies_pending_migrations_to_existing_install` | Assumes migrations m0009/m0021; drops shared tables it cannot restore (poisons the DB for later tests) |
| `tests.integration.test_startup_upgrade_path::test_startup_without_marker_or_config_upgrades_an_installed_database` | Assumes migrations m0009/m0021; drops shared tables it cannot restore (poisons the DB for later tests) |

COUNTS {'COLLATERAL': 7, 'DOC DRIFT': 24, 'ENV-LIMIT': 29, 'NEEDS-DECISION': 34, 'OPEN': 29, 'TEST DEFECT': 3}
