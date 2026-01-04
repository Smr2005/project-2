document.addEventListener("DOMContentLoaded", () => {
  const API = "/analyze";

  // Prevent browser autofill from lingering
  const clearForm = () => {
    const inputsToClear = ["db_host", "db_user", "db_pass", "db_name", "ssh_host", "ssh_user", "ssh_pass", "master_pass"];
    inputsToClear.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = "";
    });
    const dbPort = document.getElementById("db_port");
    if (dbPort) dbPort.value = "3306";
    const sshPort = document.getElementById("ssh_port");
    if (sshPort) sshPort.value = "22";
  };

  clearForm();
  setTimeout(clearForm, 500); // Second pass for aggressive browser autofill

  const sqlEl = document.getElementById("sql");
  const sandboxEl = document.getElementById("sandbox");
  const runBtn = document.getElementById("run");
  const clearBtn = document.getElementById("clear");

  const dbHostEl = document.getElementById("db_host");
  const dbPortEl = document.getElementById("db_port");
  const dbUserEl = document.getElementById("db_user");
  const dbPassEl = document.getElementById("db_pass");
  const dbNameEl = document.getElementById("db_name");

  const useSshEl = document.getElementById("use_ssh");
  const sshConfigEl = document.getElementById("ssh-config");
  const sshHostEl = document.getElementById("ssh_host");
  const sshPortEl = document.getElementById("ssh_port");
  const sshUserEl = document.getElementById("ssh_user");
  const sshPassEl = document.getElementById("ssh_pass");
  const sshKeyEl = document.getElementById("ssh_key");

  const masterPassEl = document.getElementById("master_pass");
  const saveVaultBtn = document.getElementById("save_vault");
  const loadVaultBtn = document.getElementById("load_vault");

  if (useSshEl) {
    useSshEl.onchange = () => {
      if (sshConfigEl) sshConfigEl.classList.toggle("hidden", !useSshEl.checked);
    };
  }

  function getDatabaseConfig() {
    const config = {
      host: dbHostEl.value.trim(),
      port: parseInt(dbPortEl.value) || 3306,
      user: dbUserEl.value.trim(),
      password: dbPassEl.value,
      database: dbNameEl.value.trim(),
      use_ssh: useSshEl.checked
    };

    if (config.use_ssh) {
      config.ssh_config = {
        host: sshHostEl.value.trim(),
        port: parseInt(sshPortEl.value) || 22,
        user: sshUserEl.value.trim(),
        password: sshPassEl.value,
        private_key: sshKeyEl.value
      };
    }

    return config;
  }

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

  if (runBtn) {
    runBtn.onclick = async () => {
      messageEl.className = "hidden";
      const sql = sqlEl.value.trim();
      if (!sql) {
        showMessage("Please paste a SQL query.", "error");
        return;
      }

      const database = getDatabaseConfig();
      if (!database.host || !database.user || !database.database) {
        showMessage("Please fill in all database connection details.", "error");
        return;
      }

      if (database.use_ssh) {
        const s = database.ssh_config;
        if (!s.host || !s.user || (!s.password && !s.private_key)) {
          showMessage("Please fill in SSH host, user, and either password or private key.", "error");
          return;
        }
      }

      const run_in_sandbox = sandboxEl.value === "true";

      runBtn.disabled = true;
      runBtn.textContent = "⏳ Running...";

      try {
        const resp = await fetch(API, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sql, database, run_in_sandbox })
        });

        if (resp.status === 401) {
          window.location.href = "/login";
          return;
        }

        if (!resp.ok) {
          const txt = await resp.text();
          showMessage("Server error: " + resp.status + " - " + txt, "error");
          return;
        }

        const data = await resp.json();
        console.log("Response:", data);
        renderResults(data);

      } catch (err) {
        showMessage("Request failed: " + err.message, "error");
      } finally {
        runBtn.disabled = false;
        runBtn.textContent = "▶ Run Analysis";
      }
    };
  }

  if (clearBtn) {
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
  }

  function showMessage(text, type = "info") {
    messageEl.textContent = text;
    messageEl.className = type === "error" ? "message-container error" : "message-container info";
    messageEl.classList.remove("hidden");
  }

  function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(text).replace(/[&<>"']/g, m => map[m]);
  }

  function formatSQL(sql) {
    return sql
      .replace(/\bSELECT\b/gi, '\nSELECT')
      .replace(/\bFROM\b/gi, '\nFROM')
      .replace(/\bWHERE\b/gi, '\nWHERE')
      .replace(/\bJOIN\b/gi, '\nJOIN')
      .replace(/\bLEFT\s+JOIN\b/gi, '\nLEFT JOIN')
      .replace(/\bRIGHT\s+JOIN\b/gi, '\nRIGHT JOIN')
      .replace(/\bGROUP\s+BY\b/gi, '\nGROUP BY')
      .replace(/\bHAVING\b/gi, '\nHAVING')
      .replace(/\bORDER\s+BY\b/gi, '\nORDER BY')
      .replace(/\bLIMIT\b/gi, '\nLIMIT')
      .replace(/\bAND\b/gi, '\n  AND')
      .replace(/\bOR\b/gi, '\n  OR')
      .trim();
  }

  function makeTable(rows) {
    if (!Array.isArray(rows) || rows.length === 0) return "<p>No data</p>";

    const headers = Object.keys(rows[0]);
    let html = `<div style="overflow-x: auto; margin: 1rem 0;">
    <table style="width: 100%; border-collapse: collapse; min-width: 600px;">
      <thead>
        <tr style="background: rgba(0,217,255,0.15); position: sticky; top: 0;">`;
    
    headers.forEach(h => {
      html += `<th style="padding: 12px; text-align: left; border: 1px solid rgba(0,217,255,0.2); color: var(--primary-blue); font-weight: 700; min-width: 100px; white-space: nowrap;">${escapeHtml(h)}</th>`;
    });
    
    html += `</tr>
      </thead>
      <tbody>`;

    rows.forEach(r => {
      html += `<tr style="border-bottom: 1px solid rgba(0,217,255,0.1);">`;
      headers.forEach(h => {
        const cellValue = r[h];
        html += `<td style="padding: 12px; border: 1px solid rgba(0,217,255,0.1); color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(String(cellValue || ''))}</td>`;
      });
      html += `</tr>`;
    });

    html += `</tbody>
    </table>
  </div>`;
    return html;
  }

  function renderResults(data) {
    resultsEl.classList.remove("hidden");

    const db = data.database || data.database_used || "unknown";
    const query = data.original_query || "";
    const summary = data.summary || {};
    const opt = data.optimization || {};
    const cost = data.cost_analysis || {};
    const schema = data.schema_improvements || {};
    const validator = data.data_quality || {};
    const technical = data.technical_details || {};

    const impactLevel = (summary.performance_impact || "unknown").toLowerCase();
    summaryEl.innerHTML = `<h3>📊 Analysis Summary</h3>
<p><strong>Database:</strong> ${db}</p>
<p><strong>Performance Impact:</strong> <span class="impact-${impactLevel}">${impactLevel.charAt(0).toUpperCase() + impactLevel.slice(1)}</span></p>
<p><strong>Key Findings:</strong> ${summary.optimization_reason || "Query analyzed"}</p>`;

    if (opt.status === "success") {
      const optimizedQuery = opt.optimized_query || query;
      const formattedQuery = formatSQL(optimizedQuery);
      optQueryEl.innerHTML = `<strong>Optimized Query:</strong><pre>${escapeHtml(formattedQuery)}</pre>
<p><strong>Why Faster:</strong> ${opt.why_faster || "See recommendations below"}</p>`;
    } else {
      optQueryEl.innerHTML = "<p>⚠ Optimization analysis in progress</p>";
    }

    if (opt.recommendations && opt.recommendations.length > 0) {
      recsEl.innerHTML = "<strong>💡 Optimization Tips:</strong><ul>" + opt.recommendations.map(r => `<li>${r}</li>`).join("") + "</ul>";
    } else {
      recsEl.innerHTML = "<p>✓ No specific optimizations needed</p>";
    }

    if (opt.warnings && opt.warnings.length > 0) {
      warningsEl.innerHTML = "<strong>⚠ Warnings:</strong><ul>" + opt.warnings.map(w => `<li>${w}</li>`).join("") + "</ul>";
    } else {
      warningsEl.innerHTML = "<p>✓ No issues detected</p>";
    }

    const estimatedImpact = (opt.estimated_impact || "unknown").toLowerCase();
    impactEl.innerHTML = `<strong>Impact Level:</strong> <span class="impact-${estimatedImpact}">${estimatedImpact.charAt(0).toUpperCase() + estimatedImpact.slice(1)}</span>`;
    if (opt.engine_advice && opt.engine_advice.length > 0) {
      impactEl.innerHTML += `<br><strong>🔧 Engine Tips:</strong><ul>${opt.engine_advice.map(a => `<li>${a}</li>`).join("")}</ul>`;
    }

    let aiHTML = "";

    aiHTML += `<h4>💰 Cost Analysis</h4>`;
    if (cost.status === "success") {
      const costLevel = (cost.estimated_cost || "medium").toLowerCase();
      aiHTML += `<p><strong>Estimated Cost:</strong> <strong class="cost-${costLevel}">${costLevel.charAt(0).toUpperCase() + costLevel.slice(1)}</strong></p>`;
      if (cost.cost_saving_tips && cost.cost_saving_tips.length > 0) {
        aiHTML += `<ul>${cost.cost_saving_tips.map(t => `<li>${t}</li>`).join("")}</ul>`;
      }
      if (cost.warnings && cost.warnings.length > 0) {
        aiHTML += `<p><strong>Warnings:</strong><ul>${cost.warnings.map(w => `<li>${w}</li>`).join("")}</ul></p>`;
      }
    } else {
      aiHTML += `<p>⚠ ${cost.error || "Cost analysis unavailable"}</p>`;
    }

    aiHTML += `<h4>🗄️ Schema Improvements</h4>`;
    if (schema.status === "success") {
      if (schema.recommended_indexes && schema.recommended_indexes.length > 0) {
        aiHTML += `<p><strong>Recommended Indexes:</strong></p><ul>${schema.recommended_indexes.map(idx => `<li><code>${escapeHtml(idx)}</code></li>`).join("")}</ul>`;
      }
      if (schema.schema_changes && schema.schema_changes.length > 0) {
        aiHTML += `<p><strong>Schema Changes:</strong></p><ul>${schema.schema_changes.map(change => `<li>${escapeHtml(change)}</li>`).join("")}</ul>`;
      }
      if (!schema.recommended_indexes && !schema.schema_changes) {
        aiHTML += `<p>✓ Current schema is well-designed</p>`;
      }
    } else if (schema.status === "unsafe") {
      aiHTML += `<p>⚠️ Query contains unsafe operations</p>`;
    } else {
      aiHTML += `<p>⚠ ${schema.error || "Schema analysis unavailable"}</p>`;
    }

    aiHTML += `<h4>✅ Data Quality</h4>`;
    if (validator.status === "success") {
      if (validator.issues && validator.issues.length > 0) {
        aiHTML += `<p><strong>Issues Found (${validator.confidence || "Medium"} confidence):</strong></p><ul>${validator.issues.map(issue => `<li>${issue}</li>`).join("")}</ul>`;
        if (validator.reasoning) aiHTML += `<p><em>${validator.reasoning}</em></p>`;
      } else {
        aiHTML += `<p>✓ Data quality looks good</p>`;
        if (validator.reasoning) aiHTML += `<p><em>${validator.reasoning}</em></p>`;
      }
    } else {
      aiHTML += `<p>⚠ ${validator.error || "Data validation unavailable"}</p>`;
    }

    aiNotesEl.innerHTML = aiHTML;

    if (Array.isArray(technical.explain_plan) && technical.explain_plan.length > 0) {
      planEl.innerHTML = makeTable(technical.explain_plan);
    } else {
      planEl.innerHTML = "<p>⚠ No explain plan available</p>";
    }

    if (technical.sample_rows && technical.sample_rows.rows && technical.sample_rows.rows.length > 0) {
      rowsEl.innerHTML = makeTable(technical.sample_rows.rows);
      if (technical.sample_rows.message) {
        rowsEl.innerHTML += `<p><em>${technical.sample_rows.message}</em></p>`;
      }
    } else if (technical.sample_rows && technical.sample_rows.error) {
      rowsEl.innerHTML = `<p>⚠ ${technical.sample_rows.error}</p>`;
    } else {
      rowsEl.innerHTML = "<p>⚠ No sample data available</p>";
    }

    renderRawJson(technical);
  }

  function renderRawJson(technical) {
    let html = "";

    if (technical.schema_context) {
      html += `<h3>📂 Schema Context</h3>`;
      const schema = technical.schema_context;
      if (typeof schema === "object" && !Array.isArray(schema)) {
        for (const [table, cols] of Object.entries(schema)) {
          html += `
<div style="margin-top: 1.5rem; padding: 1rem; background: rgba(0,217,255,0.05); border: 1px solid rgba(0,217,255,0.2); border-radius: 12px;">
  <h4 style="color: var(--primary-blue); margin-top: 0;">📋 Table: <code>${escapeHtml(table)}</code></h4>`;
          
          if (Array.isArray(cols)) {
            html += `
  <div style="overflow-x: auto; margin-top: 1rem;">
  <table style="width: 100%; border-collapse: collapse; min-width: 600px;">
    <thead>
      <tr style="background: rgba(0,217,255,0.15); position: sticky; top: 0;">
        <th style="padding: 12px; text-align: left; border-bottom: 2px solid rgba(0,217,255,0.3); color: var(--primary-blue); font-weight: 700; min-width: 120px;">Field</th>
        <th style="padding: 12px; text-align: left; border-bottom: 2px solid rgba(0,217,255,0.3); color: var(--primary-blue); font-weight: 700; min-width: 120px;">Type</th>
        <th style="padding: 12px; text-align: center; border-bottom: 2px solid rgba(0,217,255,0.3); color: var(--primary-blue); font-weight: 700; min-width: 80px;">Null</th>
        <th style="padding: 12px; text-align: center; border-bottom: 2px solid rgba(0,217,255,0.3); color: var(--primary-blue); font-weight: 700; min-width: 80px;">Key</th>
        <th style="padding: 12px; text-align: left; border-bottom: 2px solid rgba(0,217,255,0.3); color: var(--primary-blue); font-weight: 700; min-width: 100px;">Default</th>
        <th style="padding: 12px; text-align: left; border-bottom: 2px solid rgba(0,217,255,0.3); color: var(--primary-blue); font-weight: 700; min-width: 100px;">Extra</th>
      </tr>
    </thead>
    <tbody>`;
            
            cols.forEach(col => {
              const fieldName = col.COLUMN_NAME || col.Field || '—';
              const fieldType = col.COLUMN_TYPE || col.Type || '—';
              const isNull = col.IS_NULLABLE || col.Null || 'NO';
              const keyType = col.COLUMN_KEY || col.Key || '—';
              const defaultVal = col.COLUMN_DEFAULT || col.Default || 'null';
              const extra = col.EXTRA || col.Extra || '—';
              
              const nullDisplay = isNull === 'YES' ? '<span style="color: var(--warning-color); font-weight: 600;">YES</span>' : '<span style="color: var(--text-secondary);">NO</span>';
              const keyDisplay = keyType === 'PRI' ? '<strong style="color: var(--accent-cyan);">PRI</strong>' :
                                keyType === 'MUL' ? '<strong style="color: var(--warning-color);">MUL</strong>' :
                                keyType === 'UNI' ? '<strong style="color: var(--primary-blue);">UNI</strong>' : '—';
              
              html += `
      <tr style="border-bottom: 1px solid rgba(0,217,255,0.1);">
        <td style="padding: 12px; font-family: monospace; color: var(--text-primary); white-space: nowrap;"><code>${escapeHtml(fieldName)}</code></td>
        <td style="padding: 12px; color: var(--text-secondary); font-family: monospace; white-space: nowrap;"><code>${escapeHtml(fieldType)}</code></td>
        <td style="padding: 12px; text-align: center; color: var(--text-secondary);">${nullDisplay}</td>
        <td style="padding: 12px; text-align: center;">${keyDisplay}</td>
        <td style="padding: 12px; color: var(--text-secondary); font-family: monospace; white-space: nowrap;"><code>${escapeHtml(String(defaultVal))}</code></td>
        <td style="padding: 12px; color: var(--text-secondary);">${escapeHtml(String(extra))}</td>
      </tr>`;
            });
            
            html += `
    </tbody>
  </table>
  </div>
</div>`;
          } else if (cols && typeof cols === "object") {
            html += `<p>${JSON.stringify(cols)}</p>`;
          }
        }
      }
    }

    rawEl.innerHTML = html;
  }

  async function analyzeSchema() {
    const resultDiv = document.getElementById("schema-results");
    try {
      const database = getDatabaseConfig();
      if (!database.host || !database.user || !database.database) {
        alert("Please fill in database connection details first.");
        return;
      }

      resultDiv.innerHTML = "<p>⏳ Fetching full schema context... please wait.</p>";
      resultDiv.classList.remove("hidden");

      const response = await fetch("/analyze-schema", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ database })
      });

      if (!response.ok) {
        const errTxt = await response.text();
        throw new Error(errTxt || "Server error");
      }

      const data = await response.json();
      let html = `<h3>🗄 Schema Overview</h3>
<p><strong>Database:</strong> ${data.database || "unknown"}</p>`;

      if (data.tables && typeof data.tables === 'object') {
        for (const [tableName, columns] of Object.entries(data.tables)) {
          if (!Array.isArray(columns)) continue;

          html += `
<div style="margin-top: 2rem; padding: 1.5rem; background: rgba(0,217,255,0.05); border: 1px solid rgba(0,217,255,0.2); border-radius: 12px;">
  <h4 style="color: var(--primary-blue); margin-top: 0;">📋 Table: <code>${escapeHtml(tableName)}</code></h4>
  <table style="width: 100%; border-collapse: collapse;">
    <thead>
      <tr style="background: rgba(0,217,255,0.15);">
        <th style="padding: 10px; text-align: left; border-bottom: 2px solid rgba(0,217,255,0.3); color: var(--primary-blue);">Column</th>
        <th style="padding: 10px; text-align: left; border-bottom: 2px solid rgba(0,217,255,0.3); color: var(--primary-blue);">Type</th>
        <th style="padding: 10px; text-align: left; border-bottom: 2px solid rgba(0,217,255,0.3); color: var(--primary-blue);">Nullable</th>
        <th style="padding: 10px; text-align: left; border-bottom: 2px solid rgba(0,217,255,0.3); color: var(--primary-blue);">Key</th>
      </tr>
    </thead>
    <tbody>`;

          columns.forEach(col => {
            const nullable = col.IS_NULLABLE === 'YES' ? '✓ YES' : '✗ NO';
            const key = col.COLUMN_KEY || '—';
            const keyDisplay = key === 'PRI' ? '<strong style="color: var(--accent-cyan);">PRIMARY</strong>' : 
                              key === 'MUL' ? '<strong style="color: var(--warning-color);">FOREIGN</strong>' : key;

            html += `
      <tr style="border-bottom: 1px solid rgba(0,217,255,0.1);">
        <td style="padding: 10px; font-family: monospace; color: var(--text-primary);"><code>${escapeHtml(col.COLUMN_NAME)}</code></td>
        <td style="padding: 10px; color: var(--text-secondary);"><code>${escapeHtml(col.COLUMN_TYPE)}</code></td>
        <td style="padding: 10px; color: var(--text-secondary);">${nullable}</td>
        <td style="padding: 10px;">${keyDisplay}</td>
      </tr>`;
          });

          html += `
    </tbody>
  </table>
</div>`;
        }
      }

      resultDiv.innerHTML = html;
    } catch (err) {
      const resultDiv = document.getElementById("schema-results");
      resultDiv.innerHTML = `<p style="color: var(--danger-color);">❌ Failed to load schema: ${err.message}</p>`;
    }
  }

  if (saveVaultBtn) {
    saveVaultBtn.onclick = () => {
      const masterPass = masterPassEl.value;
      if (!masterPass) {
        alert("Please enter a Master Password to encrypt your data.");
        return;
      }

      const config = getDatabaseConfig();
      const encrypted = CryptoJS.AES.encrypt(JSON.stringify(config), masterPass).toString();
      
      localStorage.setItem("queryvault_vault", encrypted);
      alert("Connection encrypted and saved to local vault (localStorage). Your server never sees your plain-text password!");
    };
  }

  if (loadVaultBtn) {
    loadVaultBtn.onclick = () => {
      const masterPass = masterPassEl.value;
      if (!masterPass) {
        alert("Please enter your Master Password to unlock the vault.");
        return;
      }

      const encrypted = localStorage.getItem("queryvault_vault");
      if (!encrypted) {
        alert("No saved connection found in vault.");
        return;
      }

      try {
        const bytes = CryptoJS.AES.decrypt(encrypted, masterPass);
        const decrypted = JSON.parse(bytes.toString(CryptoJS.enc.Utf8));
        
        // Fill the UI if elements exist (Studio page)
        if (dbHostEl) {
          dbHostEl.value = decrypted.host || "";
          if (dbPortEl) dbPortEl.value = decrypted.port || 3306;
          if (dbUserEl) dbUserEl.value = decrypted.user || "";
          if (dbPassEl) dbPassEl.value = decrypted.password || "";
          if (dbNameEl) dbNameEl.value = decrypted.database || "";
          
          if (useSshEl) {
            useSshEl.checked = !!decrypted.use_ssh;
            if (sshConfigEl) sshConfigEl.classList.toggle("hidden", !useSshEl.checked);
          }
          
          if (decrypted.ssh_config) {
            if (sshHostEl) sshHostEl.value = decrypted.ssh_config.host || "";
            if (sshPortEl) sshPortEl.value = decrypted.ssh_config.port || 22;
            if (sshUserEl) sshUserEl.value = decrypted.ssh_config.user || "";
            if (sshPassEl) sshPassEl.value = decrypted.ssh_config.password || "";
            if (sshKeyEl) sshKeyEl.value = decrypted.ssh_config.private_key || "";
          }
          alert("Vault unlocked successfully! Credentials populated.");
        } else {
          // Vault page logic - populate the vault-list div
          const vaultList = document.getElementById("vault-list");
          if (vaultList) {
            vaultList.innerHTML = `
              <div class="guide-card" style="border-style: solid; margin-bottom: 1rem;">
                <h4 style="color: var(--primary-blue); margin-top: 0;">📡 Saved Connection</h4>
                <p><strong>Host:</strong> ${decrypted.host}</p>
                <p><strong>Database:</strong> ${decrypted.database}</p>
                <p><strong>User:</strong> ${decrypted.user}</p>
                <button onclick="window.location.href='/studio'" class="btn btn-secondary" style="width: 100%; margin-top: 1rem;">Use in Studio</button>
              </div>
            `;
            alert("Vault unlocked! Connection details listed below.");
          }
        }
      } catch (e) {
        console.error("Decryption failed:", e);
        alert("Failed to unlock vault. Incorrect Master Password?");
      }
    };
  }

  window.analyzeSchema = analyzeSchema;
});
