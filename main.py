#!/usr/bin/env python3
"""
main.py - CLI runner for Password Strength Analyzer + Wordlist Generator

Usage examples (from project root, with your venv activated):
  python main.py analyze --password "P@ssw0rd123!" --out results.json
  python main.py analyze --file samples.txt --out results.json
  python main.py generate --name "alice" --year 1997 --pet "toby" --length 10 --out wordlist.txt
  python main.py generate --from-file seed_words.txt --out custom_wordlist.txt

This script expects:
- analyzer.py exposing `analyze_password(password: str) -> dict`
- generator.py exposing `generate_wordlist(seeds: List[str], options: dict) -> Iterable[str]`
If those functions differ in your files, either adapt them or modify the import fallbacks below.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Iterable, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Try to import analysis/generator functions from local modules.
# If your function names differ, change these references accordingly.
try:
    from analyzer import analyze_password  # type: ignore
except Exception as e:
    analyze_password = None
    logging.debug("Could not import analyze_password from analyzer.py: %s", e)

try:
    from generator import generate_wordlist  # type: ignore
except Exception as e:
    generate_wordlist = None
    logging.debug("Could not import generate_wordlist from generator.py: %s", e)


def require_analyzer_or_exit():
    if analyze_password is None:
        logging.error(
            "analyzer.py doesn't expose analyze_password(password: str) -> dict\n"
            "Open analyzer.py and ensure function name and signature match.\n"
            "Aborting."
        )
        sys.exit(2)


def require_generator_or_exit():
    if generate_wordlist is None:
        logging.error(
            "generator.py doesn't expose generate_wordlist(seeds: List[str], options: dict) -> Iterable[str]\n"
            "Open generator.py and ensure function name and signature match.\n"
            "Aborting."
        )
        sys.exit(2)


# ---------- helpers ----------
def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    logging.info("Wrote JSON results to %s", path)


def write_lines(path: Path, lines: Iterable[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(f"{line}\n")
    logging.info("Wrote %d lines to %s", sum(1 for _ in lines), path)


def analyze_single(password: str) -> dict:
    require_analyzer_or_exit()
    logging.info("Analyzing password -> length %d", len(password))
    result = analyze_password(password)
    if not isinstance(result, dict):
        logging.warning("analyze_password returned unexpected type (%s). Converting to dict.", type(result))
        return {"result": result}
    return result


def analyze_file(file_path: Path) -> List[dict]:
    require_analyzer_or_exit()
    if not file_path.exists():
        logging.error("Input file not found: %s", file_path)
        sys.exit(2)
    results = []
    with file_path.open("r", encoding="utf-8", errors="ignore") as fh:
        for ln in fh:
            pw = ln.strip()
            if not pw:
                continue
            res = analyze_password(pw)
            results.append({"password": pw, "analysis": res})
    logging.info("Analyzed %d passwords from %s", len(results), file_path)
    return results


def generate_from_seeds(seeds: List[str], options: dict) -> Iterable[str]:
    require_generator_or_exit()
    logging.info("Generating wordlist from %d seed(s) with options: %s", len(seeds), options)
    return generate_wordlist(seeds, options)


# ---------- CLI ----------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="main.py", description="Password analyzer & custom wordlist generator")
    sub = p.add_subparsers(dest="command", required=True)

    # analyze
    a = sub.add_parser("analyze", help="Analyze password(s) for strength and issues")
    group = a.add_mutually_exclusive_group(required=True)
    group.add_argument("--password", "-p", type=str, help="Single password to analyze")
    group.add_argument("--file", "-f", type=Path, help="File with one password per line")
    a.add_argument("--out", "-o", type=Path, default=None, help="Write JSON output to file (if omitted, print to stdout)")

    # generate
    g = sub.add_parser("generate", help="Generate a custom wordlist from seeds / user inputs")
    gmut = g.add_mutually_exclusive_group(required=True)
    gmut.add_argument("--from-file", type=Path, help="File containing seed words (one per line)")
    gmut.add_argument("--seeds", type=str, help="Comma-separated seed words (e.g. name,pet,year)")
    # Add typical quick options for generation
    g.add_argument("--name", type=str, help="User name to include as seed")
    g.add_argument("--year", type=int, help="Year to append / combine")
    g.add_argument("--pet", type=str, help="Pet name to include")
    g.add_argument("--length", type=int, default=12, help="Target length or max length (generator-specific)")
    g.add_argument("--rules", type=str, default="", help="Optional custom generator rules (implementation-dependent)")
    g.add_argument("--out", "-o", type=Path, default=Path("wordlist.txt"), help="Output wordlist file (TXT)")

    # basic debug / dev helpers
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Verbose mode enabled")

    if args.command == "analyze":
        if args.password:
            res = analyze_single(args.password)
            if args.out:
                write_json(Path(args.out), {"password": args.password, "analysis": res})
            else:
                print(json.dumps({"password": args.password, "analysis": res}, indent=2, ensure_ascii=False))
        else:
            results = analyze_file(args.file)
            if args.out:
                write_json(Path(args.out), results)
            else:
                print(json.dumps(results, indent=2, ensure_ascii=False))

    elif args.command == "generate":
        # seed collection
        seeds = []
        if args.from_file:
            if not args.from_file.exists():
                logging.error("Seed file not found: %s", args.from_file)
                sys.exit(2)
            with args.from_file.open("r", encoding="utf-8", errors="ignore") as fh:
                seeds = [ln.strip() for ln in fh if ln.strip()]
        elif args.seeds:
            seeds = [s.strip() for s in args.seeds.split(",") if s.strip()]

        # add optional named seeds
        if args.name:
            seeds.append(args.name)
        if args.pet:
            seeds.append(args.pet)
        if args.year:
            seeds.append(str(args.year))

        # generator options to pass-through
        options = {
            "length": args.length,
            "rules": args.rules,
        }

        if not seeds:
            logging.error("No seeds provided. Use --from-file, --seeds, or supply --name/--pet/--year.")
            sys.exit(2)

        words_iter = generate_from_seeds(seeds, options)
        # Ensure generator returns an iterable of strings
        # If it returns a generator, we materialize to list to count lines and write to file.
        words = list(words_iter)
        if not words:
            logging.warning("Generator returned 0 words. Check generator implementation or seeds.")
        out_path = Path(args.out)
        write_lines(out_path, words)
        logging.info("Generated wordlist saved: %s (total %d)", out_path, len(words))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()