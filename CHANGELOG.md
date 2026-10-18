# Changelog

## v0.1.1

- Fail explicitly if Notion reports `has_more=true` without a `next_cursor`.
- Add mock tests for successful reads, cursor pagination, missing cursor, HTTP 403, and network errors.
- Fix sequential numbering for contiguous numbered-list blocks.
- Update bundle/version metadata and document known limitations.
- No real Notion token, personal memory export, or live Notion API call is included.
