from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from luna import __version__
from luna.config import load_config
from luna.context_builder import build_context_bundle, write_bundle
from luna.notion_reader import NotionReader
from luna.validator import diagnose


def _read_manifest(reader: NotionReader, entries: list[dict[str, Any]]) -> tuple[list[dict], dict[str, Any]]:
    pages: list[dict] = []
    failures: list[str] = []
    required_failures = 0
    optional_failures = 0

    for index, item in enumerate(entries):
        required = item.get("required", True)
        label = item.get("title") or item.get("expected_title") or item["id"]
        try:
            actual_title, content = reader.fetch_page(item["id"])
            expected_title = item.get("expected_title")
            if expected_title and actual_title.strip() != expected_title.strip():
                raise ValueError(
                    f"title mismatch for {label!r}: expected {expected_title!r}, got {actual_title!r}"
                )
            pages.append({
                "title": item.get("title") or actual_title,
                "content": content,
                "page_id": item["id"],
            })
        except Exception as exc:
            message = f"pages[{index}] {label!r}: {type(exc).__name__}: {exc}"
            failures.append(message)
            if required:
                required_failures += 1
            else:
                optional_failures += 1

    # Status rule (LUNA review):
    # - empty config, zero successful reads, or any required failure → FAILED
    # - optional failures with at least one success → DEGRADED
    # - otherwise → OK
    if not entries:
        status = "FAILED"
        failures.append("no pages configured in the source manifest")
    elif required_failures or not pages:
        status = "FAILED"
    elif optional_failures:
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
        print(f"Bootstrap failed: {type(exc).__name__}: {exc}", file=sys.stderr)
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
