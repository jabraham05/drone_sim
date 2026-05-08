#!/usr/bin/env python3
"""Collect a bounded git diff for automated review."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MAX_CHARS = 60000

EXCLUDED_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "build",
    "install",
    "log",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".bag",
    ".db3",
}


@dataclass(frozen=True)
class CollectedDiff:
    text: str
    truncated: bool
    included_files: tuple[str, ...]
    excluded_files: tuple[str, ...]


def should_include_path(path: str) -> bool:
    file_path = Path(path)
    if any(part in EXCLUDED_PARTS for part in file_path.parts):
        return False
    if file_path.suffix in EXCLUDED_SUFFIXES:
        return False
    return True


def truncate_text(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False

    notice = f"\n\n[diff truncated to {max_chars} characters]\n"
    return text[: max_chars - len(notice)] + notice, True


def run_git(args: list[str], repo_root: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def changed_files(base_ref: str, head_ref: str, repo_root: Path) -> list[str]:
    output = run_git(["diff", "--name-only", base_ref, head_ref], repo_root)
    return [line.strip() for line in output.splitlines() if line.strip()]


def collect_diff(base_ref: str, head_ref: str, repo_root: Path, max_chars: int) -> CollectedDiff:
    files = changed_files(base_ref, head_ref, repo_root)
    included_files = tuple(path for path in files if should_include_path(path))
    excluded_files = tuple(path for path in files if not should_include_path(path))

    sections = []
    for path in included_files:
        diff = run_git(["diff", "--find-renames", "--find-copies", base_ref, head_ref, "--", path], repo_root)
        if diff.strip():
            sections.append(diff)

    text, truncated = truncate_text("\n".join(sections), max_chars)
    return CollectedDiff(
        text=text,
        truncated=truncated,
        included_files=included_files,
        excluded_files=excluded_files,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect bounded git diff for AI review.")
    parser.add_argument("--base", required=True, help="Base git ref.")
    parser.add_argument("--head", required=True, help="Head git ref.")
    parser.add_argument("--output", required=True, type=Path, help="Output diff file.")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    collected = collect_diff(args.base, args.head, args.repo_root, args.max_chars)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(collected.text, encoding="utf-8")

    print(f"included_files={len(collected.included_files)}")
    print(f"excluded_files={len(collected.excluded_files)}")
    print(f"truncated={str(collected.truncated).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

