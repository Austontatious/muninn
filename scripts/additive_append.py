#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append a section to a file only if a marker is missing."
    )
    parser.add_argument("--file", required=True, help="Target file path.")
    parser.add_argument(
        "--marker",
        required=True,
        help="Marker string to detect existing content and prevent duplicates.",
    )
    parser.add_argument("--content", help="Section text to write/append.")
    parser.add_argument("--content-file", help="Read section text from a file path.")
    return parser.parse_args()


def load_content(args: argparse.Namespace) -> str:
    if args.content is not None:
        return args.content
    if args.content_file is not None:
        return Path(args.content_file).read_text(encoding="utf-8")
    return sys.stdin.read()


def main() -> int:
    args = parse_args()
    target = Path(args.file)
    marker = args.marker
    content = load_content(args)

    if not content:
        print("SKIP: empty content")
        return 0
    if not content.endswith("\n"):
        content = f"{content}\n"

    if target.exists():
        current = target.read_text(encoding="utf-8")
        if marker in current:
            print(f"SKIP: marker already present in {target}")
            return 0

        with target.open("a", encoding="utf-8") as handle:
            if current and not current.endswith("\n"):
                handle.write("\n")
            handle.write(f"\n<!-- ADDITIVE_APPEND START: {marker} -->\n")
            handle.write(content)
            handle.write(f"<!-- ADDITIVE_APPEND END: {marker} -->\n")
        print(f"APPEND: {target}")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    print(f"CREATE: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
