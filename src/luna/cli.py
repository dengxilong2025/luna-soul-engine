from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from luna import __version__
from luna.config import load_config
from luna.context_builder import build_context_bundle, write_bundle
from luna.notion_reader import NotionReader, classify_notion_error
from luna.validator import diagnose


def _read_manifest(reader: NotionReader, entries: list[dict[str, Any]]) -> tuple[list[dict], dict[str, Any]]:
    pages: list[dict] = []
    failures: list[str] = []
    required_failures = 0
    optional_failures = 0
    unexpanded_required = False
    roles: dict[str, str] = {}
    error_types: list[str] = []

    for index, item in enumerate(entries):
        required = item.get("required", True)
        raw_label = item.get("title") or item.get("expected_title") or item.get("role") or item["id"]
        label = str(raw_label)
        lowered_label = label.lower()
        if lowered_label.startswith(("secret_", "ntn_", "sk-", "bearer ")) or "token" in lowered_label:
            label = "<redacted>"
        raw_role_key = item.get("role") or item.get("title") or item.get("expected_title") or item["id"]
        role_key = str(raw_role_key)
        lowered_role = role_key.lower()
        if lowered_role.startswith(("secret_", "ntn_", "sk-", "bearer ")) or "token" in lowered_role:
            role_key = "<redacted>"
        compact_role = role_key.replace("-", "")
        if len(compact_role) >= 16 and all(ch in "0123456789abcdefABCDEF" for ch in compact_role):
            role_key = NotionReader._mask_block_id(role_key)
        page_status = "OK"
        try:
            result = reader.fetch_page(item["id"])
            if isinstance(result, tuple):
                if len(result) == 2:
                    actual_title, content = result
                    meta: dict[str, Any] = {}
                else:
                    actual_title, content, meta = result[0], result[1], result[2] if len(result) > 2 else {}
            else:
                actual_title, content, meta = result["title"], result["content"], result.get("meta", {})
            expected_title = item.get("expected_title")
            if expected_title and str(actual_title).strip() != str(expected_title).strip():
                raise ValueError(
                    f"title mismatch for {label!r}: expected {expected_title!r}, got {actual_title!r}"
                )
            content = content or ""
            meta = meta or {}
            has_unexpanded = bool(meta.get("has_unexpanded")) or "Unexpanded nested content" in content or "contents not expanded" in content
            if has_unexpanded:
                page_status = "DEGRADED"
                if required:
                    unexpanded_required = True
            pages.append({
                "title": item.get("title") or actual_title,
                "content": content,
                "page_id": item["id"],
                "role": item.get("role"),
                "status": page_status,
            })
        except Exception as exc:
            error_type = classify_notion_error(exc)
            error_types.append(error_type)
            page_status = "MISSING" if error_type == "not_found" else "FAILED"
            exc_text = str(exc)
            if any(tok in exc_text.lower() for tok in ("secret_", "ntn_", "token", "sk-", "bearer ")):
                exc_text = "<redacted>"
            message = f"pages[{index}] {label!r}: {error_type}: {type(exc).__name__}: {exc_text}"
            failures.append(message)
            if required:
                required_failures += 1
            else:
                optional_failures += 1
        roles[role_key] = page_status

    # Status rule (LUNA review):
    # - empty config, zero successful reads, or any required failure → FAILED
    # - optional failures with at least one success → DEGRADED
    # - unexpanded on required pages → DEGRADED
    # - otherwise → OK
    if not entries:
        status = "FAILED"
        failures.append("no pages configured in the source manifest")
    elif required_failures or not pages:
        status = "FAILED"
    elif optional_failures or unexpanded_required:
        status = "DEGRADED"
    else:
        status = "OK"
    report = {
        "status": status,
        "configured": len(entries),
        "read": len(pages),
        "required_failures": required_failures,
        "optional_failures": optional_failures,
        "failures": failures,
        "unexpanded_required": unexpanded_required,
        "roles": roles,
        "error_types": error_types,
    }
    return pages, report


def main() -> None:
    parser = argparse.ArgumentParser(prog="luna", description="Luna Soul Engine session-restoration CLI")
    parser.add_argument("command", choices=["status", "diagnose", "bootstrap"])
    parser.add_argument("--config", default="config/sources.yaml", help="Path to YAML source manifest")
    args = parser.parse_args()
    token = os.getenv("NOTION_TOKEN")

    if args.command == "status":
        print(f"Luna Soul Engine v{__version__}")
        print(f"NOTION_TOKEN: {'present' if token else 'missing'}")
        print("Mode: manifest-checked manual context-bundle generation; no automatic ChatGPT injection")
        return

    if args.command == "diagnose":
        problems = diagnose(args.config, token)
        if problems:
            print("Diagnosis: NEEDS ATTENTION")
            for problem in problems:
                print(f"- {problem}")
            sys.exit(1)
        print("Diagnosis: OK (local checks only; Notion access not tested)")
        return

    if not token:
        print("Error: set NOTION_TOKEN before running bootstrap.", file=sys.stderr)
        sys.exit(2)
    try:
        config = load_config(args.config)
        reader = NotionReader(token)
        pages, report = _read_manifest(reader, config["pages"])
        bundle = build_context_bundle(pages, manifest_report=report)
        output_path = write_bundle(bundle)
    except Exception as exc:
        # Deliberately avoid printing request headers or secrets.
        exc_text = str(exc)
        lowered_exc = exc_text.lower()
        if any(tok in lowered_exc for tok in ("secret_", "ntn_", "token", "sk-", "bearer ", "authorization")):
            exc_text = "<redacted>"
        print(f"Bootstrap failed: {type(exc).__name__}: {exc_text}", file=sys.stderr)
        sys.exit(1)

    print(f"Created restoration bundle: {output_path}")
    print(f"Manifest status: {report['status']}")
    print(f"Pages configured/read: {report['configured']}/{report['read']}")
    print(f"Required failures: {report['required_failures']}; optional failures: {report['optional_failures']}")
    if report["failures"]:
        for failure in report["failures"]:
            print(f"- {failure}")
    print("Review the output locally before sharing it.")
    if report["status"] == "FAILED":
        # A bundle is retained for diagnosis, but is not declared usable.
        sys.exit(1)


if __name__ == "__main__":
    main()
