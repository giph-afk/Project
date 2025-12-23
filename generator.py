#!/usr/bin/env python3
"""
generator.py - Custom wordlist generator

Features:
- Cleans and normalizes user-provided seeds (name, pet, year, etc.).
- Uses NLTK stemming to derive linguistic variants.
- Applies leetspeak transforms.
- Adds realistic patterns: years, symbols, and simple number combos.
- Enforces max-length and basic sanity constraints to avoid huge lists.

Exposed API:
    generate_wordlist(seeds: List[str], options: dict) -> Iterable[str]
"""

import re
from typing import Iterable, List, Set

try:
    from nltk.stem import PorterStemmer
    _HAS_NLTK = True
except Exception:  # NLTK optional; generator still works without it
    _HAS_NLTK = False
    PorterStemmer = None  # type: ignore

# --------------------------
# Leetspeak substitution map
# --------------------------

LEET_MAP = {
    "a": ["a", "@", "4"],
    "e": ["e", "3"],
    "i": ["i", "1", "!"],
    "o": ["o", "0"],
    "s": ["s", "$", "5"],
    "t": ["t", "7"],
}


def apply_leet(word: str) -> List[str]:
    """
    Generate leetspeak variants for a word.
    Keeps output bounded by collapsing duplicates via set().
    """
    if not word:
        return []

    variations: List[str] = [""]
    for ch in word.lower():
        options = LEET_MAP.get(ch, [ch])
        new_list: List[str] = []
        for prefix in variations:
            for op in options:
                new_list.append(prefix + op)
        variations = new_list

    return list(set(variations))


def apply_patterns(words: List[str], years: List[str]) -> List[str]:
    """
    Append realistic suffixes/prefixes and year patterns to base words.
    """
    final: Set[str] = set()
    symbols = ["!", "@", "#", "$", "_", "."]

    for word in words:
        if not word:
            continue

        final.add(word)

        # Year suffix / prefix patterns
        for y in years:
            if not y:
                continue
            final.add(word + y)       # alice1997
            final.add(word + "_" + y) # alice_1997
            final.add(y + word)       # 1997alice

        # Symbol suffix / prefix
        for sym in symbols:
            final.add(word + sym)        # alice!
            final.add(sym + word)        # !alice
            final.add(word + sym * 2)    # alice!!
            if years:
                # alice!1997, !alice1997
                for y in years:
                    final.add(word + sym + y)
                    final.add(sym + word + y)

    return list(final)


def _stem_word(word: str) -> List[str]:
    """
    Return a list containing word + its stem (if NLTK available).
    """
    variants = {word}
    if _HAS_NLTK and word.isalpha():
        stemmer = PorterStemmer()
        stem = stemmer.stem(word.lower())
        if stem and stem != word.lower():
            variants.add(stem)
    return list(variants)


def _clean_seeds(seeds: List[str]):
    """
    Split seeds into cleaned alphabetic words and numeric strings.
    Non-alphanumeric characters are stripped.
    """
    clean_words: List[str] = []
    clean_numbers: List[str] = []

    for seed in seeds:
        seed = (seed or "").strip()
        if not seed:
            continue
        cleaned = re.sub(r"[^a-zA-Z0-9]", "", seed)
        if not cleaned:
            continue
        if cleaned.isdigit():
            clean_numbers.append(cleaned)
        else:
            clean_words.append(cleaned)

    return clean_words, clean_numbers


def generate_wordlist(seeds: List[str], options: dict) -> Iterable[str]:
    """
    Main entry point used by main.py.

    Args:
        seeds: List of raw seed values (name, pet, years, etc.).
        options: dict with possible keys:
            - length: int, maximum length of generated words (default: 12)
            - rules:  str, optional extra rule string (currently unused hook)

    Returns:
        Sorted iterable of unique candidate passwords.
    """
    max_len = int(options.get("length", 12) or 12)

    clean_words, clean_numbers = _clean_seeds(seeds)

    final: Set[str] = set()

    # --------------------------
    # Process alphabetic seeds
    # --------------------------
    word_variations: List[str] = []

    for w in clean_words:
        # Add original + stemmed variant(s)
        for base in _stem_word(w):
            word_variations.extend(apply_leet(base))
            # Also keep simple case variations
            word_variations.append(base.lower())
            word_variations.append(base.capitalize())
            word_variations.append(base.upper())

    # Deduplicate early
    word_variations = list(set(word_variations))

    # --------------------------
    # Apply higher-level patterns
    # --------------------------
    patterned = apply_patterns(word_variations, clean_numbers)

    # --------------------------
    # Simple word+number combos
    # --------------------------
    for w in word_variations:
        for num in clean_numbers:
            final.add(w + num)
            final.add(num + w)

    # Include patterned combos
    for item in patterned:
        final.add(item)

    # Always include raw numbers and words (within length)
    for n in clean_numbers:
        final.add(n)
    for w in word_variations:
        final.add(w)

    # --------------------------
    # Optional generic suffixes
    # --------------------------
    common_suffixes = ["123", "!", "!", "99", "007"]
    for w in list(final):
        for suf in common_suffixes:
            candidate = w + suf
            if len(candidate) <= max_len:
                final.add(candidate)

    # --------------------------
    # Final filtering
    # --------------------------
    # remove too-short or too-long entries and obvious garbage
    filtered = {
        w for w in final
        if 3 <= len(w) <= max_len and not w.isspace()
    }

    return sorted(filtered)


def save_wordlist(path: str, words: Iterable[str]) -> None:
    """
    Convenience helper to write a wordlist to disk.
    """
    with open(path, "w", encoding="utf-8") as f:
        for w in words:
            f.write(w + "\n")
