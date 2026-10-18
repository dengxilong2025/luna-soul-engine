# Upload instructions for GrokBot

1. Extract this archive.
2. In `dengxilong2025/luna-soul-engine`, replace the matching project files with these files and add `CHANGELOG.md` plus this instruction file if desired.
3. Do not upload `.env`, real Notion tokens, personal memory exports, or generated `output/` files.
4. Commit with a message such as `v0.1.1: harden Notion pagination and add reader tests`.
5. Wait for GitHub Actions to finish. Confirm the run includes `python -m pytest -q` and that it succeeds.
6. Report the new commit SHA, Actions run URL, test count, and any errors. Do not claim live Notion API access was tested: these tests use mocks.

This archive is a code update, not proof that it has already been uploaded or run by GitHub Actions.
