import argparse
import json
import math
import sys
from datetime import datetime
from typing import List, Dict, Any
from datetime import datetime, timezone

try:
    from zxcvbn import zxcvbn  # type: ignore

    _HAS_ZXCVBN = True
except Exception:
    _HAS_ZXCVBN = False
    zxcvbn = None  # type: ignore

# Entropy & helpers
def shannon_entropy(password: str) -> float:
    """
    Compute Shannon entropy (bits) based on character frequency.
    """
    if not password:
        return 0.0

    freq = {}
    for ch in password:
        freq[ch] = freq.get(ch, 0) + 1

    length = len(password)
    entropy = 0.0
    for cnt in freq.values():
        p = cnt / length
        entropy -= p * math.log2(p)

    # Total bits for the whole string
    return entropy * length


def charset_size(password: str) -> int:
    """
    Rough estimate of character-set size based on character classes used.
    """
    size = 0
    if any(c.islower() for c in password):
        size += 26
    if any(c.isupper() for c in password):
        size += 26
    if any(c.isdigit() for c in password):
        size += 10
    if any(not c.isalnum() for c in password):
        size += 32  # crude symbol estimate
    return size


def _human_time(seconds: float) -> str:
    """
    Convert seconds into a human-readable time span.
    """
    if seconds == float("inf"):
        return "infinite"
    if seconds < 1:
        return "<1 second"

    units = [
        ("years", 3600 * 24 * 365),
        ("days", 3600 * 24),
        ("hours", 3600),
        ("minutes", 60),
        ("seconds", 1),
    ]

    parts = []
    remaining = seconds
    for name, val in units:
        if remaining >= val:
            v = int(remaining // val)
            parts.append(f"{v} {name}")
            remaining -= v * val
        if len(parts) >= 2:
            break

    return ", ".join(parts)


def entropy_estimator(password: str) -> Dict[str, Any]:
    """
    Fallback estimator when zxcvbn is not available.
    """
    entropy = shannon_entropy(password)
    size = charset_size(password)

    # brute-force search-space estimate
    guesses = 2 ** entropy if entropy > 0 else 1
    guesses_per_sec = 1e9  # configurable assumption
    seconds = guesses / guesses_per_sec if guesses_per_sec > 0 else float("inf")

    suggestions = []

    if len(password) < 8:
        suggestions.append("Use at least 8 characters.")
    if not any(c.isupper() for c in password):
        suggestions.append("Add uppercase letters.")
    if not any(c.islower() for c in password):
        suggestions.append("Add lowercase letters.")
    if not any(c.isdigit() for c in password):
        suggestions.append("Add digits (0–9).")
    if not any(not c.isalnum() for c in password):
        suggestions.append("Add special characters (e.g. !@#$%).")

    lower = password.lower()
    common_weak = {"password", "123456", "qwerty", "letmein"}
    if lower in common_weak or "password" in lower:
        suggestions.append("Avoid common passwords or obvious dictionary words.")

    # repeated-character check
    if any(lower.count(ch) > len(password) // 2 for ch in set(lower)):
        suggestions.append("Avoid excessive repetition of the same character.")

    # Simple entropy-based scoring → 0–4
    if entropy < 20:
        score = 0
        strength = "Very Weak"
    elif entropy < 40:
        score = 1
        strength = "Weak"
    elif entropy < 60:
        score = 2
        strength = "Moderate"
    elif entropy < 80:
        score = 3
        strength = "Strong"
    else:
        score = 4
        strength = "Very Strong"

    return {
        "engine": "entropy_fallback",
        "entropy_bits": round(entropy, 2),
        "charset_estimate": size,
        "estimated_crack_time_seconds": round(seconds, 2),
        "estimated_crack_time_human": _human_time(seconds),
        "score": score,
        "strength": strength,
        "suggestions": suggestions,
    }

# zxcvbn-based analyzer
def analyze_with_zxcvbn(password: str, user_inputs: List[str] | None = None) -> Dict[str, Any]:
    """
    Use zxcvbn for in-depth analysis, enriched with a nicer output format.
    """
    user_inputs = user_inputs or []
    res = zxcvbn(password, user_inputs=user_inputs)  # type: ignore[arg-type]

    score = res.get("score", 0)
    labels = ["Very Weak", "Weak", "Moderate", "Strong", "Very Strong"]
    strength = labels[score] if 0 <= score < len(labels) else "Unknown"

    # Extract matched patterns (dictionary, spatial, repeat, sequence, etc.)
    patterns = []
    for m in res.get("sequence", []):
        pat = {
            "pattern": m.get("pattern"),
            "token": m.get("token"),
            "dictionary_name": m.get("dictionary_name", None),
            "l33t": m.get("l33t", False),
        }
        patterns.append(pat)

    feedback = res.get("feedback", {}) or {}
    warning = feedback.get("warning") or ""
    suggestions = feedback.get("suggestions") or []

    return {
        "engine": "zxcvbn",
        "score": score,
        "strength": strength,
        "entropy_bits": res.get("entropy", None),
        "crack_times_seconds": res.get("crack_times_seconds", {}),
        "crack_times_display": res.get("crack_times_display", {}),
        "feedback_warning": warning,
        "suggestions": suggestions,
        "matched_patterns": patterns,
    }

# Public API
def analyze_password(password: str, user_inputs: List[str] | None = None) -> Dict[str, Any]:
    """
    Unified analyzer used by main.py and web API.

    If zxcvbn is installed, uses it plus optional `user_inputs` (e.g. name, pet)
    so that passwords based on those personal identifiers are penalized more.
    Otherwise falls back to entropy_estimator().
    """
    if not password:
        return {
            "engine": "none",
            "score": 0,
            "strength": "Very Weak",
            "error": "Empty password",
        }

    if _HAS_ZXCVBN:
        try:
            base = analyze_with_zxcvbn(password, user_inputs=user_inputs)
            # Also attach fallback entropy for extra insight
            ent = entropy_estimator(password)
            base["fallback_entropy_bits"] = ent.get("entropy_bits")
            base["fallback_crack_time_human"] = ent.get("estimated_crack_time_human")
            return base
        except Exception as e:
            # Graceful fallback
            return {
                "engine": "zxcvbn_error",
                "error": f"zxcvbn error: {e}",
                **entropy_estimator(password),
            }
    else:
        return entropy_estimator(password)

# CLI glue
def process_passwords(passwords: List[str]) -> List[Dict[str, Any]]:
    results = []
    for pwd in passwords:
        pwd = pwd.rstrip("\n")
        if not pwd:
            continue
        res = analyze_password(pwd)
        results.append({"password": pwd, "analysis": res})
    return results


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Password Strength Analyzer (CLI)")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--password", "-p", help="Analyze a single password string")
    group.add_argument("--file", "-f", help="Analyze passwords from a file (one per line)")
    group.add_argument("--interactive", "-i", action="store_true", help="Interactive mode (enter passwords)")

    p.add_argument("--json", action="store_true", help="Output JSON instead of human-readable text")
    p.add_argument(
        "--user-inputs",
        type=str,
        default="",
        help="Comma-separated personal words (name, pet, etc.) to feed into zxcvbn",
    )
    return p


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    user_inputs = [s.strip() for s in args.user_inputs.split(",") if s.strip()]

    passwords: List[str] = []

    if args.password:
        passwords = [args.password]
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8", errors="ignore") as fh:
                passwords = [line.strip() for line in fh.readlines()]
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(2)
    elif args.interactive:
        print("Interactive mode. Enter password (blank line to finish):")
        while True:
            try:
                pwd = input("> ")
            except EOFError:
                break
            if pwd == "":
                break
            passwords.append(pwd)

    results = []
    for pwd in passwords:
        res = analyze_password(pwd, user_inputs=user_inputs)
        results.append({"password": pwd, "analysis": res})

    if args.json:
        print(json.dumps(
            {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": results,
            },
        indent=2,
        default=str,
    ))
    else:
        for entry in results:
            pwd = entry["password"]
            analysis = entry["analysis"]
            print("=" * 60)
            print(f"Password: {pwd}")
            engine = analysis.get("engine")
            print(f"Engine: {engine}")
            print(f"Strength: {analysis.get('strength')} (Score: {analysis.get('score')})")

            entropy_bits = analysis.get("entropy_bits") or analysis.get("fallback_entropy_bits")
            if entropy_bits is not None:
                print(f"Entropy (bits): {entropy_bits}")

            # Crack time
            if engine == "zxcvbn":
                ct = analysis.get("crack_times_display", {}).get("online_no_throttling_10_per_second")
                if ct:
                    print(f"Estimated Crack Time: {ct} (online, 10 guesses/s)")
            else:
                print(f"Estimated Crack Time: {analysis.get('estimated_crack_time_human')}")

            if analysis.get("feedback_warning"):
                print(f"Warning: {analysis.get('feedback_warning')}")
            suggestions = analysis.get("suggestions") or []
            if suggestions:
                print("Suggestions:")
                for s in suggestions:
                    print(f" - {s}")

    if not args.json:
        print("=" * 60)


if __name__ == "__main__":
    main()
