const totalSessionsEl = document.getElementById("totalSessions");
const totalInteractionsEl = document.getElementById("totalInteractions");
const interactions24El = document.getElementById("interactions24");
const recentTableEl = document.getElementById("recentTable");

function rowTemplate(item) {
  const created = item.created_at ? new Date(item.created_at).toLocaleString() : "-";
  return `
    <div class="admin-row">
      <div class="admin-cell">${created}</div>
      <div class="admin-cell">${item.subject || "-"}</div>
      <div class="admin-cell">${item.mode || "-"}</div>
      <div class="admin-cell">${item.has_image ? "Yes" : "No"}</div>
      <div class="admin-cell">${(item.question || "").slice(0, 80)}</div>
    </div>
  `;
}

async function loadSummary() {
  try {
    const res = await fetch("/v1/admin/summary");
    if (!res.ok) throw new Error("summary_failed");
    const data = await res.json();

    totalSessionsEl.textContent = data.total_sessions ?? "0";
    totalInteractionsEl.textContent = data.total_interactions ?? "0";
    interactions24El.textContent = data.interactions_24h ?? "0";

    if (data.recent_interactions && data.recent_interactions.length) {
      const header = `
        <div class="admin-row admin-header">
          <div class="admin-cell">Time</div>
          <div class="admin-cell">Subject</div>
          <div class="admin-cell">Mode</div>
          <div class="admin-cell">Image</div>
          <div class="admin-cell">Question</div>
        </div>
      `;
      recentTableEl.innerHTML = header + data.recent_interactions.map(rowTemplate).join("");
    } else {
      recentTableEl.textContent = "No interactions yet.";
    }
  } catch {
    recentTableEl.textContent = "Analytics unavailable. Check Supabase config.";
  }
}

loadSummary();
