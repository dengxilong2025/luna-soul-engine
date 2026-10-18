# Luna Soul Engine v0.1

A small, auditable Python CLI for checking configuration and generating a manual session-restoration bundle from selected Notion pages.

**This is a first runnable prototype, not an automatic ChatGPT memory injector.** It reads configured Notion pages when you run `luna bootstrap`, then writes a Markdown bundle locally for you to review and paste into a new ChatGPT conversation.

## Requirements

- Python 3.11+
- A Notion integration token with read access to the pages you configure
- The configured pages must be shared with that Notion integration

## Install

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1

python -m pip install -e ".[dev]"
```

## Configure

1. Copy `.env.example` to `.env` if you use a local dotenv loader, or set the environment variable directly. This prototype intentionally does not load `.env` automatically.
2. Set `NOTION_TOKEN` in your shell environment. Never commit the token.
3. Edit `config/sources.yaml` and add the Notion page IDs you want to read.
4. In Notion, share each selected page with your integration and grant read-only access.

Example environment setup:

```bash
# macOS/Linux
export NOTION_TOKEN="secret_your_token"
# Windows PowerShell
$env:NOTION_TOKEN="secret_your_token"
```

## Commands

```bash
luna status
luna diagnose
luna bootstrap
```

- `status`: prints the CLI version and whether the token is present.
- `diagnose`: checks Python version, token presence, and configuration validity. It does not call Notion.
- `bootstrap`: reads configured pages via the Notion API, validates the response, and writes `output/luna-context-YYYYMMDD-HHMMSS.md`.

The generated `output/` folder is ignored by Git because it may contain personal context. Review the file before sharing or pasting it anywhere.

## Safety and scope

- Do not store personal memories, conversation exports, wallet details, credentials, or API tokens in this public code repository.
- Use a read-only Notion integration. The program only makes page/block retrieval requests.
- The generated bundle can contain sensitive information. Keep it local and inspect it before use.
- Notion API block pagination is supported for page content. Nested child blocks are not expanded in this prototype.
- This project does not execute code inside ChatGPT, upload itself to GitHub, or automatically inject context into a new session.
- The GitHub Actions workflow runs unit tests only; it does not need secrets or contact Notion.

## Tests

```bash
python -m pytest
```

## Known limitations

- Only ordinary text/rich-text block content is extracted; unsupported block types are represented by a short placeholder.
- Nested blocks (for example, toggle contents) are not recursively read yet.
- Notion permissions, API availability, and page structure must be verified in the environment where this runs.
