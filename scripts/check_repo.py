#!/usr/bin/env python3
"""Validate the public documentation repository without third-party packages."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parent.parent
LOCALES = ("zh-CN", "zh-TW", "en", "ko", "ja", "fr", "it", "de", "ru", "vi")
PRIVATE_MEDIA_SUFFIXES = {
    ".7z",
    ".doc",
    ".docx",
    ".gif",
    ".heic",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".rar",
    ".tif",
    ".tiff",
    ".wav",
    ".webp",
    ".zip",
}
PUBLIC_BINARY_ASSETS = {
    Path("assets/possibility-hero.webp"),
}
REQUIRED_FILES = (
    "README.md",
    "MANIFESTO.md",
    "PRIVACY.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "CITATION.cff",
    "CHANGELOG.md",
    "LICENSE",
    "SECURITY.md",
    "assets/possibility-hero.webp",
)
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*]\(([^)]+)\)")
NUMBERED_H2 = re.compile(r"^##\s+(\d+)\.", re.MULTILINE)


def repository_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and not {".git", "__pycache__"}.intersection(path.relative_to(ROOT).parts)
    )


def main() -> int:
    errors: list[str] = []
    files = repository_files()

    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    for path in files:
        relative = path.relative_to(ROOT)
        if path.stat().st_size > 1_000_000:
            errors.append(f"file exceeds 1 MB: {relative}")
        if (
            path.suffix.lower() in PRIVATE_MEDIA_SUFFIXES
            and relative not in PUBLIC_BINARY_ASSETS
        ):
            errors.append(f"private/raw media format is not allowed: {relative}")

        if relative in PUBLIC_BINARY_ASSETS:
            continue

        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"file is not UTF-8: {relative}")
            continue

        if raw and not raw.endswith(b"\n"):
            errors.append(f"missing final newline: {relative}")

        if path.suffix.lower() != ".md":
            continue

        for match in MARKDOWN_LINK.finditer(text):
            target = match.group(1).strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            target = target.split(maxsplit=1)[0].strip("\"'")
            if (
                not target
                or target.startswith(("#", "https://", "http://", "mailto:", "data:"))
            ):
                continue
            target_path = unquote(target.split("#", 1)[0])
            resolved = (path.parent / target_path).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                errors.append(f"link escapes repository: {relative} -> {target}")
                continue
            if not resolved.exists():
                errors.append(f"broken relative link: {relative} -> {target}")

    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for locale in LOCALES:
        guide = ROOT / "docs" / locale / "README.md"
        if not guide.is_file():
            errors.append(f"missing locale guide: docs/{locale}/README.md")
            continue
        text = guide.read_text(encoding="utf-8")
        sections = [int(item) for item in NUMBERED_H2.findall(text)]
        if sections != list(range(1, 15)):
            errors.append(
                f"locale sections must be exactly 1..14: docs/{locale}/README.md"
            )
        expected_name = "多恩" if locale in {"zh-CN", "zh-TW"} else "touen"
        first_line = text.splitlines()[0] if text else ""
        if expected_name not in first_line:
            errors.append(
                f"formal project name missing from title: docs/{locale}/README.md"
            )
        selector = f"docs/{locale}/README.md"
        if selector not in root_readme:
            errors.append(f"language selector missing: {selector}")

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if 'version: "0.2.0"' not in citation:
        errors.append("CITATION.cff version must match release 0.2.0")
    if "## [0.2.0] - 2026-07-31" not in changelog:
        errors.append("CHANGELOG.md must contain release 0.2.0")

    if errors:
        print("Repository validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    markdown_count = sum(path.suffix.lower() == ".md" for path in files)
    print(
        "Repository validation passed: "
        f"{len(files)} files, {markdown_count} Markdown files, "
        f"{len(LOCALES)} locale guides."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
