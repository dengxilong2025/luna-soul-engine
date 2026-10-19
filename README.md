# Luna Soul Engine v0.2.0

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

## Safety and scope

- Never store personal memories, conversation exports, wallet details, credentials, or API tokens in this repository.
- Use a read-only Notion integration. The program only makes page/block retrieval requests.
- The generated bundle can contain sensitive information. Keep it local and inspect it before use.
- Block pagination is supported. If the API says more results exist but omits the next cursor, the reader now fails explicitly instead of silently producing incomplete content.
- Nested child blocks are not recursively expanded in this version; when a block reports `has_children=true`, the recovery bundle includes an explicit unexpanded-nested-content marker (block type + masked block id) instead of silently dropping children.
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
