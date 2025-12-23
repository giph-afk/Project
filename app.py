# app.py
import subprocess
import shlex
import json
import os
from pathlib import Path
from flask import Flask, request, send_file, jsonify, abort

app = Flask(__name__, static_folder="static", static_url_path="/static")

# Project root (where main.py lives)
ROOT = Path(__file__).resolve().parent

# Helper to run the CLI commands
def run_main_cmd(args_list, timeout=30):
    """
    args_list: list of command parts, e.g. ['python', 'main.py', 'analyze', '--password', 'abc']
    Returns: dict with keys: ok(bool), stdout(str), stderr(str), returncode(int)
    """
    try:
        proc = subprocess.run(
            args_list,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            encoding="utf-8",
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired as e:
        return {"ok": False, "stdout": "", "stderr": f"Timeout after {timeout}s", "returncode": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "returncode": -2}


@app.route("/")
def index():
    # Serve the existing index.html from the static folder
    index_path = ROOT / "static" / "index.html"
    if not index_path.exists():
        return "index.html not found in static/ - place your UI files in the static/ folder", 500
    return app.send_static_file("index.html")


# Analyze endpoint: expects JSON { "password": "..." }
@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    payload = request.get_json(force=True, silent=True)
    if not payload or "password" not in payload:
        return jsonify({"ok": False, "log": "Missing 'password' in JSON body"}), 400

    pw = str(payload["password"])
    # Call the CLI: python main.py analyze --password "pw"
    cmd = ["python", "main.py", "analyze", "--password", pw]
    res = run_main_cmd(cmd, timeout=15)

    # If main.py writes machine-readable JSON to stdout, return that.
    if res["ok"]:
        # parsing stdout as JSON and return that object if possible
        try:
            parsed = json.loads(res["stdout"])
            return jsonify({"ok": True, "result": parsed, "log": res["stdout"]})
        except Exception:
            # not JSON — pass raw stdout
            return jsonify({"ok": True, "result": None, "log": res["stdout"]})
    else:
        return jsonify({"ok": False, "log": res["stderr"] or res["stdout"]}), 500


# Generate endpoint: expects JSON { "seeds": "a,b,c" OR ["a","b"], "length": 10, "out": "mylist.txt" }
@app.route("/api/generate", methods=["POST"])
def api_generate():
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"ok": False, "log": "Missing JSON body"}), 400

    # seeds can be a comma string or list
    seeds = payload.get("seeds", "")
    if isinstance(seeds, list):
        seeds_arg = ",".join(seeds)
    else:
        seeds_arg = str(seeds)

    length = payload.get("length", None)
    out = payload.get("out", "mylist.txt")
    out = str(out).strip() or "mylist.txt"

    cmd = ["python", "main.py", "generate", "--seeds", seeds_arg, "--length", str(length), "--out", out]
    res = run_main_cmd(cmd, timeout=60)

    if res["ok"]:
        # confirm file exists
        out_path = ROOT / out
        if not out_path.exists():
            # maybe main.py writes it to a different folder; attempt to find same filename in root or wordlists/
            alt = None
            for candidate in [ROOT / out, ROOT / "wordlists" / out, ROOT / "outputs" / out]:
                if candidate.exists():
                    alt = candidate
                    break
            if alt:
                out_path = alt
            else:
                return jsonify({"ok": False, "log": f"Generator executed but output file not found: {out}"}), 500

        return jsonify({"ok": True, "log": res["stdout"], "path": str(out_path)})

    else:
        return jsonify({"ok": False, "log": res["stderr"] or res["stdout"]}), 500


# Download generated file (path must be within project root)
@app.route("/download")
def download():
    # ?path=relative/path.txt
    requested = request.args.get("path", "")
    if not requested:
        return "Missing path parameter", 400

    # Normalize and ensure it's inside project root
    safe_path = (ROOT / Path(requested)).resolve()
    try:
        safe_path.relative_to(ROOT)  # raises ValueError if outside
    except Exception:
        return "Invalid path", 403

    if not safe_path.exists():
        return "File not found", 404

    # send file
    return send_file(str(safe_path), as_attachment=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
