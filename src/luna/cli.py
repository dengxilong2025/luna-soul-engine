from __future__ import annotations

import argparse
import os
import sys

from luna import __version__
from luna.config import load_config
from luna.context_builder import build_context_bundle, write_bundle
from luna.notion_reader import NotionReader
from luna.validator import diagnose


def main() -> None:
    parser = argparse.ArgumentParser(prog="luna", description="Luna Soul Engine session-restoration CLI")
    parser.add_argument("command", choices=["status", "diagnose", "bootstrap"])
    parser.add_argument("--config", default="config/sources.yaml", help="Path to YAML source config")
    args = parser.parse_args()
    token = os.getenv("NOTION_TOKEN")

    if args.command == "status":
        print(f"Luna Soul Engine v{__version__}")
        print(f"NOTION_TOKEN: {'present' if token else 'missing'}")
        print("Mode: manual context-bundle generation; no automatic ChatGPT injection")
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
        pages = []
        for item in config["pages"]:
            title, content = reader.fetch_page(item["id"])
            pages.append({"title": item.get("title") or title, "content": content})
        bundle = build_context_bundle(pages)
        output_path = write_bundle(bundle)
    except Exception as exc:
        # Deliberately avoid printing request headers or secrets.
        print(f"Bootstrap failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Created restoration bundle: {output_path}")
    print(f"Pages read: {len(pages)}")
    print("Review the output locally before sharing it.")


if __name__ == "__main__":
    main()
