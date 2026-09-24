/**
 * Support CRM - Agent Portal Logic
 */

const AgentApp = {
    formatDate: function(dateStr) {
        if (!dateStr) return "N/A";
        const d = new Date(dateStr);
        return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    },

    renderStatusBadge: function(status) {
        const s = (status || "open").toLowerCase();
        let label = s;
        if (s === "in-progress") label = "In Progress";
        return `<span class="badge badge-${s}">${label}</span>`;
    },

    renderPriorityBadge: function(priority) {
        const p = (priority || "medium").toLowerCase();
        return `<span class="badge badge-priority-${p}">${p.toUpperCase()}</span>`;
    },

    escapeHtml: function(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Load Agent Dashboard.
     */
    loadDashboard: async function() {
        if (!Auth.requireAuth(["agent", "admin"])) return;

        const user = Auth.getUser();
        const welcomeEl = document.getElementById("welcome-agent-name");
        if (welcomeEl && user) {
            welcomeEl.textContent = user.username || user.name || "Agent";
        }

        try {
            const [tickets, customers] = await Promise.all([
                API.get("/tickets/"),
                API.get("/customers/")
            ]);

            let total = tickets.length;
            let open = 0;
            let inProgress = 0;
            let resolved = 0;

            tickets.forEach(t => {
                const s = (t.status || "").toLowerCase();
                if (s === "open") open++;
                else if (s === "in-progress") inProgress++;
                else if (s === "resolved" || s === "closed") resolved++;
            });

            document.getElementById("stat-total-tickets").textContent = total;
            document.getElementById("stat-open-tickets").textContent = open;
            document.getElementById("stat-inprogress-tickets").textContent = inProgress;
            document.getElementById("stat-resolved-tickets").textContent = resolved;
            const custEl = document.getElementById("stat-total-customers");
            if (custEl) custEl.textContent = customers.length;

            // Render recent tickets (up to 6)
            const tbody = document.getElementById("agent-recent-tickets");
            if (tbody) {
                if (tickets.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem; color: var(--text-muted);">No tickets logged in the CRM yet.</td></tr>`;
                } else {
                    const recent = tickets.slice(0, 6);
                    tbody.innerHTML = recent.map(t => `
                        <tr>
                            <td><strong>#${t.id}</strong></td>
                            <td><a href="ticket-detail.html?id=${t.id}" style="color: var(--primary); text-decoration: none; font-weight: 600;">${this.escapeHtml(t.title)}</a></td>
                            <td>${t.customer_name ? this.escapeHtml(t.customer_name) : `#${t.customer_id}`}</td>
                            <td>${this.renderStatusBadge(t.status)}</td>
                            <td>${this.renderPriorityBadge(t.priority)}</td>
                            <td>${t.assigned_agent_name ? this.escapeHtml(t.assigned_agent_name) : '<span style="color: var(--text-muted); font-style: italic;">Unassigned</span>'}</td>
                            <td><a href="ticket-detail.html?id=${t.id}" class="btn btn-secondary btn-sm">Manage</a></td>
                        </tr>
                    `).join("");
                }
            }
        } catch (err) {
            console.error("Agent dashboard failed:", err);
        }
    },

    /**
     * Load All Tickets page for Agent.
     */
    loadTicketsList: async function() {
        if (!Auth.requireAuth(["agent", "admin"])) return;

        try {
            const tickets = await API.get("/tickets/");
            window._allAgentTickets = tickets;
            this.renderFilteredTickets(tickets);
        } catch (err) {
            console.error("Failed to load agent tickets:", err);
            const tbody = document.getElementById("agent-tickets-tbody");
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--danger); padding: 2rem;">Error: ${err.message}</td></tr>`;
            }
        }
    },

    renderFilteredTickets: function(tickets) {
        const tbody = document.getElementById("agent-tickets-tbody");
        if (!tbody) return;

        if (tickets.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2.5rem; color: var(--text-muted);">No tickets match the selected filters.</td></tr>`;
            return;
        }

        tbody.innerHTML = tickets.map(t => `
            <tr>
                <td><strong>#${t.id}</strong></td>
                <td>
                    <a href="ticket-detail.html?id=${t.id}" style="color: var(--primary); text-decoration: none; font-weight: 600;">
                        ${this.escapeHtml(t.title)}
                    </a>
                </td>
                <td>${t.customer_name ? this.escapeHtml(t.customer_name) : `#${t.customer_id}`}</td>
                <td>${this.renderStatusBadge(t.status)}</td>
                <td>${this.renderPriorityBadge(t.priority)}</td>
                <td>${t.assigned_agent_name ? `<span style="font-weight: 600; color: var(--primary);">${this.escapeHtml(t.assigned_agent_name)}</span>` : '<span style="color: var(--text-muted); font-style: italic;">Unassigned</span>'}</td>
                <td><a href="ticket-detail.html?id=${t.id}" class="btn btn-secondary btn-sm">Manage</a></td>
            </tr>
        `).join("");
    },

    filterTickets: function() {
        const statusFilter = document.getElementById("agent-filter-status").value;
        const priorityFilter = document.getElementById("agent-filter-priority").value;
        const searchQuery = (document.getElementById("agent-search-input").value || "").toLowerCase().trim();

        let filtered = (window._allAgentTickets || []).slice();

        if (statusFilter) {
            filtered = filtered.filter(t => (t.status || "").toLowerCase() === statusFilter.toLowerCase());
        }
        if (priorityFilter) {
            filtered = filtered.filter(t => (t.priority || "").toLowerCase() === priorityFilter.toLowerCase());
        }
        if (searchQuery) {
            filtered = filtered.filter(t => 
                (t.title && t.title.toLowerCase().includes(searchQuery)) ||
                (t.customer_name && t.customer_name.toLowerCase().includes(searchQuery)) ||
                (t.id && t.id.toString().includes(searchQuery))
            );
        }

        this.renderFilteredTickets(filtered);
    },

    /**
     * Load Ticket Detail for Agent Management.
     */
    loadTicketDetail: async function() {
        if (!Auth.requireAuth(["agent", "admin"])) return;

        const params = new URLSearchParams(window.location.search);
        const ticketId = params.get("id");
        if (!ticketId) {
            window.location.href = "tickets.html";
            return;
        }

        try {
            const ticket = await API.get(`/tickets/${ticketId}`);
            window._currentTicket = ticket;

            document.getElementById("agent-ticket-id").textContent = `#${ticket.id}`;
            document.getElementById("agent-ticket-title").textContent = ticket.title;
            document.getElementById("agent-ticket-status-badge").innerHTML = this.renderStatusBadge(ticket.status);
            document.getElementById("agent-ticket-priority-badge").innerHTML = this.renderPriorityBadge(ticket.priority);
            document.getElementById("agent-ticket-created").textContent = this.formatDate(ticket.created_at);
            document.getElementById("agent-ticket-desc").textContent = ticket.description || "No description provided.";
            document.getElementById("agent-ticket-customer").textContent = ticket.customer_name ? `${ticket.customer_name} (ID: ${ticket.customer_id})` : `Customer #${ticket.customer_id}`;

            // Populate form controls
            document.getElementById("update-status").value = ticket.status;
            document.getElementById("update-priority").value = ticket.priority;

            // Load communication logs
            this.loadLogs(ticketId);
        } catch (err) {
            alert(`Error loading ticket: ${err.message}`);
            window.location.href = "tickets.html";
        }
    },

    /**
     * Update Ticket Status & Priority.
     */
    handleUpdateTicket: async function(e) {
        e.preventDefault();
        Auth.hideAlert("manage-alert");

        const ticket = window._currentTicket;
        if (!ticket) return;

        const newStatus = document.getElementById("update-status").value;
        const newPriority = document.getElementById("update-priority").value;
        const btn = document.getElementById("update-ticket-btn");

        btn.disabled = true;
        btn.textContent = "Updating...";

        try {
            const updated = await API.put(`/tickets/${ticket.id}`, {
                title: ticket.title,
                description: ticket.description,
                status: newStatus,
                priority: newPriority,
                customer_id: ticket.customer_id,
                assigned_agent_id: ticket.assigned_agent_id
            });

            window._currentTicket = updated;
            document.getElementById("agent-ticket-status-badge").innerHTML = this.renderStatusBadge(updated.status);
            document.getElementById("agent-ticket-priority-badge").innerHTML = this.renderPriorityBadge(updated.priority);
            Auth.showAlert("manage-alert", "Ticket updated successfully!", "success");
        } catch (err) {
            Auth.showAlert("manage-alert", err.message || "Failed to update ticket");
        } finally {
            btn.disabled = false;
            btn.textContent = "Update Ticket";
        }
    },

    /**
     * Assign ticket to current logged-in agent.
     */
    handleAssignToMe: async function() {
        const ticket = window._currentTicket;
        const user = Auth.getUser();
        if (!ticket || !user || !user.id) return;

        try {
            const updated = await API.put(`/tickets/${ticket.id}`, {
                title: ticket.title,
                description: ticket.description,
                status: ticket.status,
                priority: ticket.priority,
                customer_id: ticket.customer_id,
                assigned_agent_id: user.id
            });

            window._currentTicket = updated;
            alert(`Ticket assigned to ${user.username || "you"}!`);
            this.loadTicketDetail();
        } catch (err) {
            alert(`Failed to assign ticket: ${err.message}`);
        }
    },

    /**
     * Load Communication Logs for Agent.
     */
    loadLogs: async function(ticketId) {
        const container = document.getElementById("agent-timeline");
        if (!container) return;

        try {
            const logs = await API.get(`/logs/?ticket_id=${ticketId}`);
            if (logs.length === 0) {
                container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem; padding: 1rem 0;">No communications logged for this ticket yet.</p>`;
                return;
            }

            container.innerHTML = logs.map(l => `
                <div class="timeline-item">
                    <div class="timeline-content">
                        <div class="timeline-header">
                            <span style="font-weight: 700; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.5px; color: var(--primary);">${l.type}</span>
                            <span>${this.formatDate(l.created_at)}</span>
                        </div>
                        <div class="timeline-body">
                            ${this.escapeHtml(l.content)}
                        </div>
                    </div>
                </div>
            `).join("");
        } catch (err) {
            container.innerHTML = `<p style="color: var(--danger); font-size: 0.9rem;">Unable to load logs: ${err.message}</p>`;
        }
    },

    /**
     * Add Communication Log (call, email, chat).
     */
    handleAddLog: async function(e) {
        e.preventDefault();
        const ticket = window._currentTicket;
        if (!ticket) return;

        const type = document.getElementById("log-type").value;
        const contentInput = document.getElementById("agent-log-content");
        const content = contentInput.value.trim();
        const btn = document.getElementById("add-log-btn");

        if (!content) return;

        btn.disabled = true;
        btn.textContent = "Logging...";

        try {
            await API.post("/logs/", {
                type,
                content,
                ticket_id: ticket.id
            });

            contentInput.value = "";
            this.loadLogs(ticket.id);
        } catch (err) {
            alert(`Failed to save communication log: ${err.message}`);
        } finally {
            btn.disabled = false;
            btn.textContent = "Record Communication";
        }
    },

    /**
     * Load Customers list for Agent.
     */
    loadCustomersList: async function() {
        if (!Auth.requireAuth(["agent", "admin"])) return;

        try {
            const customers = await API.get("/customers/");
            const tbody = document.getElementById("agent-customers-tbody");
            if (!tbody) return;

            if (customers.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-muted);">No customers registered in database yet.</td></tr>`;
                return;
            }

            tbody.innerHTML = customers.map(c => `
                <tr>
                    <td><strong>#${c.id}</strong></td>
                    <td style="font-weight: 600;">${this.escapeHtml(c.name)}</td>
                    <td>${this.escapeHtml(c.email)}</td>
                    <td>${c.phone ? this.escapeHtml(c.phone) : '-'}</td>
                    <td>${c.company ? this.escapeHtml(c.company) : '-'}</td>
                    <td>${c.notes ? this.escapeHtml(c.notes) : '-'}</td>
                </tr>
            `).join("");
        } catch (err) {
            console.error("Failed to load customers:", err);
        }
    }
};
