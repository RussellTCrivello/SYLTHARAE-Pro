# Execution record, research limitations and open questions

## Environment setup and verified run

- Installed the checked-out project in a local `.venv` with the declared base dependencies and PDF, Office, OCR, ebook, audio, media, Waitress and development extras. PST native extra was not installed because it requires platform-specific C dependencies.
- Started an ephemeral PostgreSQL 16.2 instance from the `pgserver` development package. Created a local demo database and applied the authoritative migration chain through `0039` (all 39 migrations).
- Started `run_web.py` with a local development configuration and Flask bound to `0.0.0.0:5000`. Setup installer backend completed successfully; the setup wizard and login pages were captured from actual live routes.
- Captured authenticated pages for all 34 interfaces declared in `docs/INTERFACE_REGISTRY.md`; 34 route responses returned HTTP 200 during the capture pass. Also captured login, setup wizard, file detail, full-content reader, and four mobile viewport screens. Files and route/viewport details appear in `screenshot_manifest.csv` and `interface_screenshots.zip`.
- Uploaded two synthetic text files using the application’s ingestion UI, created/selected a synthetic source and side, ran dry-run preflight (2 discovered, 2 to read, 0 unreadable, 770 B), started the actual ingestion job, observed `COMPLETED` at 100% / 4 of 4 work units, and searched `CASE-DEMO-042` (2 results). Screenshots are authentic captures; only the documents are synthetic.
- Ran `verify_readiness.py`: **31 checks, 0 failed, READY**. This readiness utility includes a representative ingest/search probe and several security/configuration checks; it is not the full project test suite.

## Not verified in this run

- The full pytest unit/integration/security suites, JS test suite, Ruff, and Bandit were not run.
- OCR self-check and OCR accuracy were not run. The OCR Python extras installed, but no Tesseract system binary/language packs were configured or exercised.
- PST native reader, every reader/format, large files, archive attack corpus, translated locale states, all role/permission combinations, and every UI interaction were not exhaustively tested.
- No production deployment, TLS reverse proxy, systemd service, multi-user load, performance benchmark, backup/restore, upgrade/rollback, penetration test, threat model, dependency advisory audit, or compliance review was performed.
- Live captures use a local development server, an ephemeral local PostgreSQL cluster, and a demo administrator. They establish observed behavior in this sandbox only, not production readiness or hardening.
- The interface screenshot pass captured the 34 registered page endpoints at the default desktop viewport; mobile screenshot spot-check covers File Library, Search, Input/Ingestion, and Settings only. Responsive behavior is not exhaustively verified.
- PDF export is still unavailable: neither LibreOffice/soffice nor a compatible presentation renderer is installed in the environment. The PPTX package itself was checked for ZIP integrity and slide/image counts, but visual rendering of the 91-slide deck should be checked in PowerPoint or LibreOffice.
- Local checkout history is shallow at `aa2b865a24c429e242a457a60d2aef84661389b2`; no tags were listed. Full release/issue/PR history was not reviewed.

## Open questions for adoption

1. Which operating systems and PostgreSQL versions are supported in production?
2. What throughput, corpus size, concurrent-user and job-concurrency envelope is supported and measured?
3. Which format versions and extraction-fidelity limits are accepted for target corpora?
4. What is the intended tenant/isolation model and authorization boundary for cross-group collections?
5. What are the retention, legal-hold, data residency, deletion and privacy policies for originals and extracted text?
6. What database plus filesystem backup/restore and recovery-point/recovery-time objectives are supported?
7. What upgrade and rollback playbooks are validated for the supported deployment shape?
8. Has an independent security review, SBOM/dependency scan, or compliance assessment been completed?
9. What is the intended future of in-process jobs if horizontal worker scaling is required?
10. Has counsel reviewed AGPL-3.0-or-later obligations for modified network-service deployments?

## Qualification

This is a repository-grounded technical briefing plus a bounded live demonstration. It is not a full code audit, formal test report, customer reference, security certification or production-readiness assessment. All live UI screenshots are identified as captures from the isolated demo instance; the dataset is synthetic.
