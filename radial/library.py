"""Folder scan for brushes (.ZBP) — the basis of Phase 4.

Usage:
    python -m radial.library "C:\\path\\to\\brushes" "D:\\my brushes"
    python -m radial.library <folders...> --slots   # prints slots ready for the JSON

Writes config/library.json with the name and path of every brush found.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import PROJECT_ROOT

BRUSH_EXTENSIONS = {".zbp"}
LIBRARY_PATH = PROJECT_ROOT / "config" / "library.json"


def scan(folders: list[str | Path]) -> list[dict]:
    """Lists the brushes in the folders (recursive), without duplicate paths."""
    found: dict[str, dict] = {}
    for folder in folders:
        root = Path(folder).expanduser()
        if not root.is_dir():
            print(f"[library] folder not found, skipping: {root}")
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in BRUSH_EXTENSIONS:
                key = str(path.resolve()).lower()
                if key not in found:
                    found[key] = {
                        "name": path.stem,
                        "path": str(path.resolve()),
                        "folder": path.parent.name,
                    }
    return sorted(found.values(), key=lambda b: (b["folder"].lower(), b["name"].lower()))


def search(library: list[dict], query: str) -> list[dict]:
    """Simple search: every word must appear in the name or the folder."""
    words = query.lower().split()
    return [
        b for b in library
        if all(w in f'{b["name"]} {b["folder"]}'.lower() for w in words)
    ]


def as_slot(brush: dict) -> dict:
    return {"label": brush["name"], "action": {"type": "brush_file", "path": brush["path"]}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scans folders for .ZBP brushes")
    parser.add_argument("folders", nargs="+")
    parser.add_argument("--slots", action="store_true",
                        help="prints the brushes in menus.json slot format")
    parser.add_argument("--find", default="", help="filters by name")
    args = parser.parse_args(argv)

    library = scan(args.folders)
    if args.find:
        library = search(library, args.find)
    LIBRARY_PATH.write_text(json.dumps(library, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[library] {len(library)} brushes -> {LIBRARY_PATH}")
    if args.slots:
        print(json.dumps([as_slot(b) for b in library], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
