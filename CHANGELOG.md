# Changelog

## v0.3.0

- Live `notion_live` pytest performs real read-only calls when opted in; failures are not skipped.
- Unexpanded detection prefers structured meta; bare prose phrases do not degrade.
- Pagination guards: repeated `next_cursor` and `MAX_BLOCK_PAGES` cap → explicit error.
- Reject duplicate non-empty manifest roles without exposing page IDs.
Gap-fill (missing tests + small polish):
- live pytest real calls
- sources.yaml gitignored
- unexpanded meta-primary
- pagination loop/cap
- duplicate roles
- digest fingerprint wording

Closing fix round (LUNA-approved):
- Rewrite live Notion pytest with opt-in skipif and masked summary only.
- Gitignore `config/sources.yaml`; keep example placeholders.
- Unexpanded false positive fixed: bracketed markers only; structured unexpanded metadata drives bundle section.
- Pagination loop guard: repeated cursor and 50-page cap raise `NotionPaginationError`.
- Role collision validation raises `ValueError` with deterministic message.
- Integrity digest documented as content fingerprint, not signature/authenticity/completeness proof.
- Network isolation coverage for pure unit paths.

- Count unsupported/nested block placeholders toward unexpanded completeness (required pages → DEGRADED).
- Scrub bootstrap top-level exceptions; diagnose catches YAML errors without crashing.
- Distinguish pagination_error (missing cursor) from incomplete_response (bad results).
- Add optional manifest `role` field with non-empty validation.
- Enrich `fetch_page` to return `(title, content, meta)` with unexpanded block metadata, block counts, fetch counts, and `has_unexpanded`.
- Classify Notion errors into stable categories (`rate_limit`, `auth_failure`, etc.).
- Treat missing/non-list `results` as incomplete Notion responses.
- Deduplicate unexpanded markers by masked id / synthetic key.
- Update nested-content marker text to `children not read in v0.3.0`.
- Add integrity SHA-256 digest to context bundle (canonical text includes roles and failure lines).
- Rewrite bundle with startup instructions disclaimer, required page read status, key page contents, missing items, unexpanded, limits and notes.
- Status rules: unexpanded required pages yield `DEGRADED`; track `unexpanded_required`, `roles`, and `error_types`.
- Add opt-in `notion_live` pytest marker and scaffold live test.
- Add secret-injection tests and document roles, status rules, integrity digest, live test env vars, known limits.

## v0.2.0

- Add backwards-compatible manifest fields: `required` (default true) and `expected_title`.
- Detect duplicate page IDs and invalid field types before network access.
- Report manifest status as OK / DEGRADED / FAILED; write the report into the recovery bundle.
- Required-page failures exit with code 1; optional-page failures keep successful pages.
- Avoid overwriting a bundle generated within the same second.
- Add mock-only tests for manifest validation and reader integrity. No new dependencies.
- Flag Notion blocks with `has_children=true` in the recovery bundle (block type + masked block id); nested child content is still not recursively read.

## v0.1.1

- Fail explicitly if Notion reports `has_more=true` without a `next_cursor`.
- Add mock tests for successful reads, cursor pagination, missing cursor, HTTP 403, and network errors.
- Fix sequential numbering for contiguous numbered-list blocks.
- Update bundle/version metadata and document known limitations.
- No real Notion token, personal memory export, or live Notion API call is included.
