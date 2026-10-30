#!/usr/bin/env python3
"""
convert.py - Document converter

Supported conversions:
    PDF        -> DOCX (Word)
    PDF        -> MD   (Markdown)
    DOCX       -> MD
    PPTX / PPT -> MD   (.ppt and .doc are first converted via LibreOffice)

Install:
    pip install pdf2docx pymupdf4llm "markitdown[docx,pptx]"
    # Optional, only for legacy .ppt / .doc files:
    #   Debian/Ubuntu: sudo apt install libreoffice
    #   macOS:         brew install --cask libreoffice

Usage:
    python convert.py report.pdf --to docx
    python convert.py report.pdf --to md
    python convert.py notes.docx              # default target for docx/ppt(x) is md
    python convert.py slides.pptx -o out/slides.md
    python convert.py ./docs --to md -r       # batch: every supported file in a folder
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SUPPORTED = {
    ".pdf": {"docx", "md"},
    ".docx": {"md"},
    ".doc": {"md"},
    ".pptx": {"md"},
    ".ppt": {"md"},
}


# --------------------------------------------------------------------------- #
# Converters
# --------------------------------------------------------------------------- #
def pdf_to_docx(src: Path, dst: Path) -> None:
    from pdf2docx import Converter

    cv = Converter(str(src))
    try:
        cv.convert(str(dst))
    finally:
        cv.close()


def pdf_to_md(src: Path, dst: Path) -> None:
    import pymupdf4llm

    md = pymupdf4llm.to_markdown(str(src))
    dst.write_text(md, encoding="utf-8")


def office_to_md(src: Path, dst: Path) -> None:
    """DOCX / PPTX -> Markdown via Microsoft's markitdown."""
    from markitdown import MarkItDown

    result = MarkItDown().convert(str(src))
    dst.write_text(result.text_content, encoding="utf-8")


def legacy_to_modern(src: Path, workdir: Path) -> Path:
    """Convert .ppt -> .pptx or .doc -> .docx using LibreOffice (headless)."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError(
            f"{src.suffix} files need LibreOffice to be converted first. "
            "Install it, or save the file as .pptx/.docx and retry."
        )
    target = {".ppt": "pptx", ".doc": "docx"}[src.suffix.lower()]
    subprocess.run(
        [soffice, "--headless", "--convert-to", target, "--outdir", str(workdir), str(src)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    out = workdir / f"{src.stem}.{target}"
    if not out.exists():
        raise RuntimeError(f"LibreOffice failed to convert {src}")
    return out


# --------------------------------------------------------------------------- #
# Dispatcher
# --------------------------------------------------------------------------- #
def convert(src: Path, to: str, dst: Path | None = None) -> Path:
    ext = src.suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError(f"Unsupported input type: {ext}")
    if to not in SUPPORTED[ext]:
        allowed = ", ".join(sorted(SUPPORTED[ext]))
        raise ValueError(f"Cannot convert {ext} to {to} (allowed: {allowed})")

    dst = dst or src.with_suffix(f".{to}")
    dst.parent.mkdir(parents=True, exist_ok=True)

    if ext == ".pdf" and to == "docx":
        pdf_to_docx(src, dst)
    elif ext == ".pdf" and to == "md":
        pdf_to_md(src, dst)
    elif ext in (".docx", ".pptx"):
        office_to_md(src, dst)
    elif ext in (".doc", ".ppt"):
        with tempfile.TemporaryDirectory() as tmp:
            modern = legacy_to_modern(src, Path(tmp))
            office_to_md(modern, dst)
    return dst


def default_target(path: Path) -> str:
    return "docx" if path.suffix.lower() == ".pdf" else "md"


def iter_inputs(path: Path, recursive: bool):
    if path.is_file():
        yield path
        return
    pattern = "**/*" if recursive else "*"
    for p in sorted(path.glob(pattern)):
        if p.is_file() and p.suffix.lower() in SUPPORTED:
            yield p


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Convert PDF -> Word/Markdown, Word -> Markdown, PowerPoint -> Markdown."
    )
    ap.add_argument("input", type=Path, help="Input file or folder")
    ap.add_argument("--to", choices=["docx", "md"],
                    help="Target format (default: docx for PDF, md for Word/PowerPoint)")
    ap.add_argument("-o", "--output", type=Path,
                    help="Output file (single input) or output folder (folder input)")
    ap.add_argument("-r", "--recursive", action="store_true",
                    help="Recurse into subfolders when input is a folder")
    args = ap.parse_args()

    if not args.input.exists():
        print(f"Error: {args.input} not found", file=sys.stderr)
        return 1

    files = list(iter_inputs(args.input, args.recursive))
    if not files:
        print("No supported files found.", file=sys.stderr)
        return 1

    failures = 0
    for src in files:
        to = args.to or default_target(src)
        if to not in SUPPORTED[src.suffix.lower()]:
            print(f"skip  {src} (cannot convert to {to})")
            continue

        if args.output is None:
            dst = None
        elif args.input.is_file():
            dst = args.output
        else:
            rel = src.relative_to(args.input).with_suffix(f".{to}")
            dst = args.output / rel

        try:
            out = convert(src, to, dst)
            print(f"ok    {src} -> {out}")
        except Exception as e:  # keep going on batch runs
            failures += 1
            print(f"FAIL  {src}: {e}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
