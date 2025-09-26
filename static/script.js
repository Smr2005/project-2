document.addEventListener("DOMContentLoaded", () => {
  const API = "http://127.0.0.1:8000/analyze";

  const sqlEl = document.getElementById("sql");
  const sandboxEl = document.getElementById("sandbox");
  const runBtn = document.getElementById("run");
  const clearBtn = document.getElementById("clear");

  const resultsEl = document.getElementById("results");
  const summaryEl = document.getElementById("summary");
  const optQueryEl = document.getElementById("opt-query");
  const recsEl = document.getElementById("recommendations");
  const warningsEl = document.getElementById("warnings");
  const impactEl = document.getElementById("impact");
  const aiNotesEl = document.getElementById("ai-notes");
  const planEl = document.getElementById("plan");
  const rowsEl = document.getElementById("rows");
  const rawEl = document.getElementById("raw");
  const messageEl = document.getElementById("message");

  // ---- Run button ----
  runBtn.onclick = async () => {
    messageEl.className = "hidden";
    const sql = sqlEl.value.trim();
    if (!sql) {
      showMessage("Please paste a SQL query.", "error");
      return;
    }
    const run_in_sandbox = sandboxEl.value === "true";

    runBtn.disabled = true;
    runBtn.textContent = "⏳ Running...";

    try {
      const resp = await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sql, run_in_sandbox })
      });

      if (!resp.ok) {
        const txt = await resp.text();
        showMessage("Server error: " + resp.status + " - " + txt, "error");
        return;
      }

      const data = await resp.json();
      renderResults(data);

    } catch (err) {
      showMessage("Request failed: " + err.message, "error");
    } finally {
      runBtn.disabled = false;
      runBtn.textContent = "▶ Run Analysis";
    }
  };

  // ---- Clear button ----
  clearBtn.onclick = () => {
    sqlEl.value = "";
    resultsEl.className = "hidden";
    summaryEl.textContent = "";
    optQueryEl.textContent = "";
    recsEl.textContent = "";
    warningsEl.textContent = "";
    impactEl.textContent = "";
    aiNotesEl.textContent = "";
    planEl.textContent = "";
    rowsEl.textContent = "";
    rawEl.textContent = "";
    messageEl.className = "hidden";
  };

  // ---- Helper: Show message ----
  function showMessage(text, type = "info") {
    messageEl.textContent = text;
    messageEl.className = type === "error" ? "error" : "info";
    messageEl.classList.remove("hidden");
  }

  // ---- Helper: Render API response ----
  function renderResults(data) {
    resultsEl.classList.remove("hidden");

    // Summary
    summaryEl.textContent = `Database: ${data.database_used || "unknown"}
Query: ${data.original_query}
Tables in schema: ${Object.keys(data.schema_context || {}).length}`;

    // Optimizer details
    const details = data.analysis || {};
    optQueryEl.textContent = details.optimized_query || "⚠ No optimized query provided.";

    // Recommendations → list
    if (details.recommendations && details.recommendations.length > 0) {
      recsEl.innerHTML = "<ul>" + details.recommendations.map(r => `<li>${r}</li>`).join("") + "</ul>";
    } else {
      recsEl.textContent = "None";
    }

    // Warnings → list
    if (details.warnings && details.warnings.length > 0) {
      warningsEl.innerHTML = "<ul>" + details.warnings.map(w => `<li>${w}</li>`).join("") + "</ul>";
    } else {
      warningsEl.textContent = "None";
    }

    // Estimated impact
    impactEl.textContent = details.estimated_impact || "Unknown";

    // AI Notes → format sub-agent outputs
    if (details.ai_details) {
      let html = "";
      for (const [agent, data] of Object.entries(details.ai_details)) {
        html += `<h4>${agent.replace('_', ' ').toUpperCase()}</h4>`;
        if (data.status === "success") {
          html += `<pre>${JSON.stringify(data.details, null, 2)}</pre>`;
        } else {
          html += `<p>Error: ${data.details?.error || "Unknown"}</p>`;
        }
      }
      aiNotesEl.innerHTML = html;
    } else {
      aiNotesEl.textContent = "None";
    }

    // Explain Plan → table
    if (Array.isArray(data.explain_plan) && data.explain_plan.length > 0) {
      planEl.innerHTML = makeTable(data.explain_plan);
    } else {
      planEl.textContent = "⚠ No explain plan returned.";
    }

    // Sample Rows → table
    if (data.sample_rows && data.sample_rows.rows && data.sample_rows.rows.length > 0) {
      rowsEl.innerHTML = makeTable(data.sample_rows.rows);
      if (data.sample_rows.message) {
        rowsEl.innerHTML += `<p><em>${data.sample_rows.message}</em></p>`;
      }
    } else if (data.sample_rows && data.sample_rows.error) {
      rowsEl.textContent = "⚠ Error fetching rows: " + data.sample_rows.error;
    } else {
      rowsEl.textContent = "⚠ No sample rows returned.";
    }

    // Raw JSON
    renderRawJson(data);
  }

  // ---- Helper: Convert JSON array → HTML table ----
  function makeTable(rows) {
    if (!Array.isArray(rows) || rows.length === 0) return "<p>No data</p>";

    const headers = Object.keys(rows[0]);
    let html = "<table border='1' cellpadding='4' cellspacing='0'><thead><tr>";
    headers.forEach(h => html += `<th>${h}</th>`);
    html += "</tr></thead><tbody>";

    rows.forEach(r => {
      html += "<tr>";
      headers.forEach(h => html += `<td>${r[h]}</td>`);
      html += "</tr>";
    });

    html += "</tbody></table>";
    return html;
  }

  // ---- Render raw JSON (structured) ----
  function renderRawJson(data) {
    let html = "";

    // Schema context
    if (data.schema_context) {
      html += `<h3>📂 Schema Context</h3>`;
      for (const [table, cols] of Object.entries(data.schema_context)) {
        html += `<h4>Table: ${table}</h4>`;
        html += makeTable(cols);
      }
    }

    // Database info
    if (data.database_used) {
      html += `<p><strong>Database used:</strong> ${data.database_used}</p>`;
    }

    rawEl.innerHTML = html;
  }

  // ---- Schema analysis ----
  async function analyzeSchema() {
    const response = await fetch("/analyze-schema", { method: "POST" });
    const data = await response.json();

    const resultDiv = document.getElementById("schema-results");
    resultDiv.innerHTML = `
      <h3>🗄 Schema Overview</h3>
      <pre>${JSON.stringify(data, null, 2)}</pre>
    `;
  }

  // Expose for button onclick
  window.analyzeSchema = analyzeSchema;
});
