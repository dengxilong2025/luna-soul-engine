# Luna Soul Engine v0.3.0

A small, auditable Python CLI for checking configuration and generating a manual session-restoration bundle from selected Notion pages.

**This is a runnable prototype, not an automatic ChatGPT memory injector.** It reads configured Notion pages when you run `luna bootstrap`, then writes a Markdown bundle locally for review and manual handoff.

## Requirements

- Python 3.11+
- A Notion integration token with read access to configured pages
- The configured pages must be shared with the Notion integration

## Install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install -e ".[dev]"
```

## Configure

1. Set `NOTION_TOKEN` in your shell environment. Never commit the token.
2. Edit `config/sources.yaml` and add the Notion page IDs to read.
3. Share each selected page with your Notion integration and grant read-only access.

```bash
export NOTION_TOKEN="secret_your_token"  # macOS/Linux
# PowerShell: $env:NOTION_TOKEN="secret_your_token"
```

## Commands

```bash
luna status
luna diagnose
luna bootstrap
```

- `status`: prints the CLI version and whether a token is present.
- `diagnose`: checks Python version, token presence, and configuration. It does not call Notion.
- `bootstrap`: reads configured pages via the Notion API and writes `output/luna-context-YYYYMMDD-HHMMSS.md`.

The generated `output/` folder is ignored by Git because it may contain personal context. Inspect the file before sharing it.

## Manifest roles

Page entries may include an optional `role` string (for example `bootstrap_protocol` or `continuity_index`). Roles are reported by name, never by raw Notion IDs, in bundle/status diagnostics.

## Status rules

- `FAILED`: empty config, zero successful reads, or any required-page failure (missing, unreadable, title mismatch, critical pagination error).
- `DEGRADED`: not failed, but optional failures exist or a required page has unexpanded nested content.
- `OK`: all configured pages read successfully, titles match, no unexpanded nested content on required pages, integrity digest computed.

## Integrity digest

Each bundle header contains `Integrity-SHA256`, a SHA-256 hex digest of a canonical serialization of status, configured/read counts, and page contents sorted by masked id. Partial or failed bundles still receive a digest of whatever was read.

## Live Notion tests

Live tests are opt-in and skipped by default:

```bash
LUNA_NOTION_LIVE=1 NOTION_TOKEN=secret_... .venv/bin/pytest -q -m notion_live
```

## Safety and scope

- Never store personal memories, conversation exports, wallet details, credentials, or API tokens in this repository.
- Use a read-only Notion integration. The program only makes page/block retrieval requests.
- The generated bundle can contain sensitive information. Keep it local and inspect it before use.
- Block pagination is supported. If the API says more results exist but omits the next cursor, the reader now fails explicitly instead of silently producing incomplete content.
- Missing or non-list `results` fields are treated as incomplete responses.
- Nested child blocks are not recursively expanded in this version; when a block reports `has_children=true`, the recovery bundle includes an explicit unexpanded-nested-content marker (block type + masked block id) instead of silently dropping children. A required page with such a marker yields `DEGRADED`.
- Numbered list items are numbered sequentially within contiguous runs.
- This project does not upload itself to GitHub or automatically inject context into a new ChatGPT session.
- GitHub Actions runs mock/unit tests only; it does not require secrets or contact Notion.

## Tests

```bash
python -m pytest -q
```

## Known limitations

- Only ordinary text/rich-text block content is extracted; unsupported block types receive a short placeholder.
- Nested blocks (for example, toggle contents) are not recursively read yet, but they are explicitly flagged in the recovery bundle so nothing is silently dropped.
- Real Notion permissions, API availability, and page structure must be verified in the environment where this runs.
