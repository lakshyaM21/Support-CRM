/**
 * Support CRM - Customer Portal Logic
 */

const CustomerApp = {
    /**
     * Format ISO datetime to user-friendly local date string.
     */
    formatDate: function(dateStr) {
        if (!dateStr) return "N/A";
        const d = new Date(dateStr);
        return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    },

    /**
     * Render HTML badge for ticket status.
     */
    renderStatusBadge: function(status) {
        const s = (status || "open").toLowerCase();
        let label = s;
        if (s === "in-progress") label = "In Progress";
        return `<span class="badge badge-${s}">${label}</span>`;
    },

    /**
     * Render HTML badge for ticket priority.
     */
    renderPriorityBadge: function(priority) {
        const p = (priority || "medium").toLowerCase();
        return `<span class="badge badge-priority-${p}">${p.toUpperCase()}</span>`;
    },

    /**
     * Load Customer Dashboard (Metrics and Recent Tickets).
     */
    loadDashboard: async function() {
        if (!Auth.requireAuth("customer")) return;

        const user = Auth.getUser();
        const welcomeEl = document.getElementById("welcome-name");
        if (welcomeEl && user) {
            welcomeEl.textContent = user.name || user.email;
        }

        try {
            const tickets = await API.get("/tickets/");

            // Calculate stats
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

            // Update stats DOM
            const totalEl = document.getElementById("stat-total");
            const openEl = document.getElementById("stat-open");
            const inProgressEl = document.getElementById("stat-in-progress");
            const resolvedEl = document.getElementById("stat-resolved");

            if (totalEl) totalEl.textContent = total;
            if (openEl) openEl.textContent = open;
            if (inProgressEl) inProgressEl.textContent = inProgress;
            if (resolvedEl) resolvedEl.textContent = resolved;

            // Render recent tickets table (up to 5)
            const tbody = document.getElementById("recent-tickets-tbody");
            if (tbody) {
                if (tickets.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 2rem; color: var(--text-muted);">You have not created any tickets yet. <a href="create-ticket.html">Create your first ticket</a>.</td></tr>`;
                } else {
                    const recent = tickets.slice(0, 5);
                    tbody.innerHTML = recent.map(t => `
                        <tr>
                            <td><strong>#${t.id}</strong></td>
                            <td><a href="ticket-detail.html?id=${t.id}" style="color: var(--primary); text-decoration: none; font-weight: 600;">${this.escapeHtml(t.title)}</a></td>
                            <td>${this.renderStatusBadge(t.status)}</td>
                            <td>${this.renderPriorityBadge(t.priority)}</td>
                            <td>${this.formatDate(t.created_at)}</td>
                            <td><a href="ticket-detail.html?id=${t.id}" class="btn btn-secondary btn-sm">View Details</a></td>
                        </tr>
                    `).join("");
                }
            }
        } catch (err) {
            console.error("Dashboard load failed:", err);
        }
    },

    /**
     * Load My Tickets list page with search & filter.
     */
    loadTicketsList: async function() {
        if (!Auth.requireAuth("customer")) return;

        try {
            const tickets = await API.get("/tickets/");
            window._allCustomerTickets = tickets;
            this.renderFilteredTickets(tickets);
        } catch (err) {
            console.error("Failed to load tickets:", err);
            const tbody = document.getElementById("tickets-tbody");
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--danger); padding: 2rem;">Error loading tickets: ${err.message}</td></tr>`;
            }
        }
    },

    renderFilteredTickets: function(tickets) {
        const tbody = document.getElementById("tickets-tbody");
        if (!tbody) return;

        if (tickets.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2.5rem; color: var(--text-muted);">No tickets found matching your criteria.</td></tr>`;
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
                <td>${this.renderStatusBadge(t.status)}</td>
                <td>${this.renderPriorityBadge(t.priority)}</td>
                <td>${this.formatDate(t.created_at)}</td>
                <td>${t.assigned_agent_name ? `<span style="font-weight: 500;">${this.escapeHtml(t.assigned_agent_name)}</span>` : '<span style="color: var(--text-muted); font-style: italic;">Unassigned</span>'}</td>
                <td><a href="ticket-detail.html?id=${t.id}" class="btn btn-secondary btn-sm">View</a></td>
            </tr>
        `).join("");
    },

    filterTickets: function() {
        const statusFilter = document.getElementById("filter-status").value;
        const priorityFilter = document.getElementById("filter-priority").value;
        const searchQuery = (document.getElementById("search-input").value || "").toLowerCase().trim();

        let filtered = (window._allCustomerTickets || []).slice();

        if (statusFilter) {
            filtered = filtered.filter(t => (t.status || "").toLowerCase() === statusFilter.toLowerCase());
        }
        if (priorityFilter) {
            filtered = filtered.filter(t => (t.priority || "").toLowerCase() === priorityFilter.toLowerCase());
        }
        if (searchQuery) {
            filtered = filtered.filter(t => 
                (t.title && t.title.toLowerCase().includes(searchQuery)) ||
                (t.id && t.id.toString().includes(searchQuery))
            );
        }

        this.renderFilteredTickets(filtered);
    },

    /**
     * Submit new customer ticket.
     */
    handleCreateTicket: async function(e) {
        e.preventDefault();
        Auth.hideAlert("ticket-alert");

        const title = document.getElementById("ticket-title").value.trim();
        const description = document.getElementById("ticket-description").value.trim();
        const priority = document.getElementById("ticket-priority").value;
        const btn = document.getElementById("submit-btn");

        if (!title) {
            Auth.showAlert("ticket-alert", "Please provide a ticket title");
            return;
        }

        btn.disabled = true;
        btn.textContent = "Submitting Ticket...";

        try {
            // Note: customer_id is omitted; backend automatically infers it from customer JWT!
            const newTicket = await API.post("/tickets/", {
                title,
                description: description || null,
                priority
            });

            Auth.showAlert("ticket-alert", `Ticket #${newTicket.id} created successfully! Redirecting...`, "success");
            setTimeout(() => {
                window.location.href = `ticket-detail.html?id=${newTicket.id}`;
            }, 1000);
        } catch (err) {
            Auth.showAlert("ticket-alert", err.message || "Failed to create ticket");
            btn.disabled = false;
            btn.textContent = "Submit Ticket";
        }
    },

    /**
     * Load Single Ticket Details and Communication Logs.
     */
    loadTicketDetail: async function() {
        if (!Auth.requireAuth("customer")) return;

        const params = new URLSearchParams(window.location.search);
        const ticketId = params.get("id");

        if (!ticketId) {
            window.location.href = "tickets.html";
            return;
        }

        try {
            // Fetch ticket details (backend performs ownership check!)
            const ticket = await API.get(`/tickets/${ticketId}`);

            document.getElementById("ticket-title-display").textContent = ticket.title;
            document.getElementById("ticket-id-display").textContent = `#${ticket.id}`;
            document.getElementById("ticket-status-badge").innerHTML = this.renderStatusBadge(ticket.status);
            document.getElementById("ticket-priority-badge").innerHTML = this.renderPriorityBadge(ticket.priority);
            document.getElementById("ticket-created-at").textContent = this.formatDate(ticket.created_at);
            document.getElementById("ticket-description-text").textContent = ticket.description || "No description provided.";
            document.getElementById("ticket-agent-name").textContent = ticket.assigned_agent_name || "Support Team (Unassigned)";

            // Fetch communication logs for this ticket
            this.loadTicketLogs(ticketId);
        } catch (err) {
            alert(`Unable to load ticket #${ticketId}: ${err.message}`);
            window.location.href = "tickets.html";
        }
    },

    /**
     * Load Communication Logs for a Ticket.
     */
    loadTicketLogs: async function(ticketId) {
        const container = document.getElementById("timeline-container");
        if (!container) return;

        try {
            const logs = await API.get(`/logs/?ticket_id=${ticketId}`);
            if (logs.length === 0) {
                container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem; padding: 1rem 0;">No messages or updates on this ticket yet.</p>`;
                return;
            }

            container.innerHTML = logs.map(l => `
                <div class="timeline-item">
                    <div class="timeline-content">
                        <div class="timeline-header">
                            <span style="font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.5px;">${l.type}</span>
                            <span>${this.formatDate(l.created_at)}</span>
                        </div>
                        <div class="timeline-body">
                            ${this.escapeHtml(l.content)}
                        </div>
                    </div>
                </div>
            `).join("");
        } catch (err) {
            container.innerHTML = `<p style="color: var(--danger); font-size: 0.9rem;">Unable to load conversation history: ${err.message}</p>`;
        }
    },

    /**
     * Post a reply / communication log to a ticket.
     */
    handleAddLog: async function(e) {
        e.preventDefault();
        const params = new URLSearchParams(window.location.search);
        const ticketId = parseInt(params.get("id"), 10);
        const contentInput = document.getElementById("log-content");
        const content = contentInput.value.trim();
        const btn = document.getElementById("send-log-btn");

        if (!content) return;

        btn.disabled = true;
        btn.textContent = "Posting...";

        try {
            await API.post("/logs/", {
                type: "chat",
                content: content,
                ticket_id: ticketId
            });

            contentInput.value = "";
            this.loadTicketLogs(ticketId);
        } catch (err) {
            alert(`Failed to add message: ${err.message}`);
        } finally {
            btn.disabled = false;
            btn.textContent = "Send Message";
        }
    },

    /**
     * Load Customer Profile.
     */
    loadProfile: async function() {
        if (!Auth.requireAuth("customer")) return;

        try {
            const profile = await API.get("/auth/customer/me");
            document.getElementById("prof-name").value = profile.name || "";
            document.getElementById("prof-email").value = profile.email || "";
            document.getElementById("prof-phone").value = profile.phone || "";
            document.getElementById("prof-company").value = profile.company || "";
            document.getElementById("prof-notes").value = profile.notes || "";
        } catch (err) {
            console.error("Failed to load profile:", err);
        }
    },

    /**
     * Update Customer Profile.
     */
    handleUpdateProfile: async function(e) {
        e.preventDefault();
        Auth.hideAlert("profile-alert");

        const user = Auth.getUser();
        if (!user || !user.id) return;

        const name = document.getElementById("prof-name").value.trim();
        const phone = document.getElementById("prof-phone").value.trim();
        const company = document.getElementById("prof-company").value.trim();
        const notes = document.getElementById("prof-notes").value.trim();
        const btn = document.getElementById("prof-btn");

        btn.disabled = true;
        btn.textContent = "Saving...";

        try {
            const updated = await API.put(`/customers/${user.id}`, {
                name,
                phone: phone || null,
                company: company || null,
                notes: notes || null
            });

            // Update stored session
            user.name = updated.name;
            user.phone = updated.phone;
            user.company = updated.company;
            localStorage.setItem("crm_user", JSON.stringify(user));
            Auth.updateNavUser();

            Auth.showAlert("profile-alert", "Profile updated successfully!", "success");
        } catch (err) {
            Auth.showAlert("profile-alert", err.message || "Failed to update profile");
        } finally {
            btn.disabled = false;
            btn.textContent = "Save Changes";
        }
    },

    escapeHtml: function(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
};
