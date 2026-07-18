/* Dashboard logic: stats strip + filterable transaction ledger */

let currentFilter = "all";

function riskClass(level) {
  return level ? level.toLowerCase() : "low";
}

async function loadStats() {
  const strip = document.getElementById("statsStrip");
  try {
    const res = await fetch("/api/stats");
    const s = await res.json();

    strip.innerHTML = `
      <div class="signal-cell info">
        <div class="label">Total transactions</div>
        <div class="value">${s.total_transactions}</div>
      </div>
      <div class="signal-cell high">
        <div class="label">High risk</div>
        <div class="value">${s.high_risk}</div>
      </div>
      <div class="signal-cell medium">
        <div class="label">Medium risk</div>
        <div class="value">${s.medium_risk}</div>
      </div>
      <div class="signal-cell low">
        <div class="label">Low risk</div>
        <div class="value">${s.low_risk}</div>
      </div>
      <div class="signal-cell info">
        <div class="label">Avg. risk score</div>
        <div class="value">${s.avg_risk_score}</div>
      </div>
    `;
  } catch (err) {
    strip.innerHTML = `<div class="form-msg error">${err.message}</div>`;
  }
}

async function loadTransactions() {
  const wrap = document.getElementById("tableWrap");
  try {
    const res = await fetch(`/api/transactions?risk_level=${currentFilter}&limit=500`);
    const data = await res.json();
    const rows = data.transactions;

    if (!rows || rows.length === 0) {
      wrap.innerHTML = `
        <div class="empty-state">
          <div class="glyph">📭</div>
          No transactions loaded yet. <a href="/upload">Load data to get started →</a>
        </div>`;
      return;
    }

    wrap.innerHTML = `
      <table class="grid">
        <thead>
          <tr>
            <th>Ref</th><th>Customer</th><th>Timestamp</th><th>Amount</th>
            <th>Category</th><th>Risk score</th><th>Level</th><th>Flags</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map(t => `
            <tr>
              <td class="mono"><a href="/transaction/${t.transaction_ref}">${t.transaction_ref}</a></td>
              <td>${t.customer_id}</td>
              <td class="mono">${t.timestamp}</td>
              <td class="mono">$${Number(t.amount).toFixed(2)}</td>
              <td>${t.merchant_category}</td>
              <td>
                <div class="risk-bar-track" style="width:80px; display:inline-block; vertical-align:middle;">
                  <div class="risk-bar-fill ${riskClass(t.risk_level)}" style="width:${t.final_risk_score || 0}%;"></div>
                </div>
                <span class="mono" style="margin-left:0.5em;">${t.final_risk_score ?? '—'}</span>
              </td>
              <td><span class="risk-badge ${riskClass(t.risk_level)}">${t.risk_level || 'Unscored'}</span></td>
              <td>${(t.rule_flags || []).length} flag${(t.rule_flags || []).length === 1 ? '' : 's'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (err) {
    wrap.innerHTML = `<div class="form-msg error">${err.message}</div>`;
  }
}

document.querySelectorAll(".chip-filter").forEach(chip => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".chip-filter").forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
    currentFilter = chip.dataset.level;
    loadTransactions();
  });
});

async function rescoreAll() {
  const btn = document.getElementById("rescoreBtn");
  btn.disabled = true;
  btn.textContent = "Rescoring…";
  try {
    const res = await fetch("/api/transactions/rescore", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ retrain_model: true, contamination: 0.06 })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Rescore failed");
    await loadStats();
    await loadTransactions();
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Rescore all";
  }
}

loadStats();
loadTransactions();
