# Changelog

## v0.2.0

- Add backwards-compatible manifest fields: `required` (default true) and `expected_title`.
- Detect duplicate page IDs and invalid field types before network access.
- Report manifest status as OK / DEGRADED / FAILED; write the report into the recovery bundle.
- Required-page failures exit with code 1; optional-page failures keep successful pages.
- Avoid overwriting a bundle generated within the same second.
- Add mock-only tests for manifest validation and reader integrity. No new dependencies.

## v0.1.1

- Fail explicitly if Notion reports `has_more=true` without a `next_cursor`.
- Add mock tests for successful reads, cursor pagination, missing cursor, HTTP 403, and network errors.
- Fix sequential numbering for contiguous numbered-list blocks.
- Update bundle/version metadata and document known limitations.
- No real Notion token, personal memory export, or live Notion API call is included.
