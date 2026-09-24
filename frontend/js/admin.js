/**
 * Support CRM - Admin Reports & Analytics Logic
 */

const AdminApp = {
    loadReports: async function() {
        if (!Auth.requireAuth(["admin", "agent"])) return;

        const user = Auth.getUser();
        const welcomeEl = document.getElementById("admin-welcome-name");
        if (welcomeEl && user) {
            welcomeEl.textContent = user.username || user.name || "Administrator";
        }

        try {
            // Fetch analytics in parallel from existing reports router
            const [summary, workload, responseTimes] = await Promise.all([
                API.get("/reports/tickets-summary"),
                API.get("/reports/agent-workload"),
                API.get("/reports/response-times")
            ]);

            // Populate summary metrics
            document.getElementById("rep-total").textContent = summary.total_tickets || 0;
            document.getElementById("rep-open").textContent = summary.open || 0;
            document.getElementById("rep-inprogress").textContent = summary.in_progress || 0;
            document.getElementById("rep-resolved").textContent = summary.resolved || 0;

            // Populate response times
            const respEl = document.getElementById("rep-resp-time");
            if (respEl) {
                respEl.textContent = `${responseTimes.average_response_time_hours || 24} hrs`;
            }

            // Populate agent workload table
            const tbody = document.getElementById("workload-tbody");
            if (tbody) {
                const agents = workload.agent_workload || {};
                const entries = Object.entries(agents);
                if (entries.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="2" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No agent assignments found.</td></tr>`;
                } else {
                    tbody.innerHTML = entries.map(([agentName, count]) => `
                        <tr>
                            <td style="font-weight: 600;">${agentName || 'Unassigned'}</td>
                            <td><span class="badge badge-open" style="font-size: 0.85rem;">${count} Tickets</span></td>
                        </tr>
                    `).join("");
                }
            }
        } catch (err) {
            console.error("Failed to load reports:", err);
        }
    }
};
