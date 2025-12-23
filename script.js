async function analyzePassword() {
  const pwd = document.getElementById("passwordInput").value.trim();
  const output = document.getElementById("analyzeOutput");

  if (!pwd) {
    output.textContent = "Please enter a password.";
    return;
  }

  output.textContent = "Analyzing...";

  try {
    const resp = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pwd })
    });

    const data = await resp.json();

    if (!data.ok) {
      output.textContent = "Error: " + (data.log || "Unknown error.");
      return;
    }

    const payload = data.result || data;
    const entry =
      payload.analysis ? payload :
      (payload.results && payload.results[0]) ? payload.results[0] :
      { password: pwd, analysis: payload };

    const a = entry.analysis || {};

    const length = pwd.length;
    const strength = a.strength || "Unknown";
    const score = a.score ?? "-";
    const entropy = a.entropy_bits || a.entropy || "n/a";
    const engine = a.engine || (a.crack_times_seconds ? "zxcvbn" : "entropy_fallback");

    const crack =
      a.estimated_crack_time_human ||
      (a.crack_times_display &&
        (a.crack_times_display.online_no_throttling_10_per_second ||
         a.crack_times_display.offline_fast_hashing_1e10_per_second)) ||
      "n/a";

    const suggestions = (a.suggestions && a.suggestions.length)
      ? a.suggestions
      : [];

    let lines = [];
    lines.push(`Password length: ${length}`);
    lines.push(`Engine: ${engine}`);
    lines.push(`Strength: ${strength} (score ${score})`);
    lines.push(`Entropy: ${entropy} bits`);
    lines.push(`Estimated crack time: ${crack}`);
    if (suggestions.length) {
      lines.push("");
      lines.push("Suggestions:");
      suggestions.forEach(s => lines.push(`- ${s}`));
    }

    output.textContent = lines.join("\n");
  } catch (err) {
    output.textContent = "Request failed: " + err;
  }
}

async function generateWordlist() {
    
  const seeds = document.getElementById("seedsInput").value.trim();
  const length = document.getElementById("lengthInput").value.trim();
  const outFile = document.getElementById("outputFileInput").value.trim() || "mylist.txt";

  const output = document.getElementById("generateOutput");

  if (!seeds) {
    output.textContent = "Please enter seeds.";
    return;
  }

  output.textContent = "Generating wordlist...";

  try {
    const resp = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        seeds: seeds,
        length: parseInt(length, 10),
        out: outFile
      })
    });

    const data = await resp.json();

    if (!data.ok) {
      output.textContent = "Error: " + (data.log || "Unknown error.");
      return;
    }

    const fullPath = data.path || outFile;
    const fileName = fullPath.split(/[\\/]/).pop();

    output.innerHTML =
      `Wordlist generated successfully.<br>` +
      `File: <code>${fileName}</code><br>` +
      `<a href="/download?path=${encodeURIComponent(fullPath)}" target="_blank">Download here</a>`;
  } catch (err) {
    output.textContent = "Request failed: " + err;
  }
}

window.addEventListener("DOMContentLoaded", () => {
  const analyzeBtn = document.getElementById("analyzeBtn");
  const generateBtn = document.getElementById("generateBtn");

  if (analyzeBtn) analyzeBtn.addEventListener("click", analyzePassword);
  if (generateBtn) generateBtn.addEventListener("click", generateWordlist);

  const toggle = document.getElementById("togglePwd");
  const pwdField = document.getElementById("passwordInput");

  if (toggle && pwdField) {
    // ensure initial face is the "open" face as placed in HTML
    toggle.addEventListener("click", () => {
  if (pwdField.type === "password") {
    pwdField.type = "text";
    toggle.textContent = "(─‿─)";   // closed face when showing password
  } else {
    pwdField.type = "password";
    toggle.textContent = "(◕‿◕)";   // open face when hiding password
  }
});
    // For keyboard accessibility: toggle with Enter/Space when focused
    toggle.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggle.click();
      }
    });
  }
});
