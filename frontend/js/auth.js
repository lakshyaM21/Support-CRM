/**
 * Support CRM - Authentication & Session Helper
 */

const Auth = {
    /**
     * Get current authenticated user object.
     */
    getUser: function() {
        const raw = localStorage.getItem("crm_user");
        try {
            return raw ? JSON.parse(raw) : null;
        } catch (e) {
            return null;
        }
    },

    /**
     * Get current user role ('customer', 'agent', 'admin').
     */
    getRole: function() {
        return localStorage.getItem("crm_role");
    },

    /**
     * Check if user is currently logged in.
     */
    isLoggedIn: function() {
        return !!API.getToken();
    },

    /**
     * Log out current user and redirect to login page.
     */
    logout: function() {
        API.clearSession();
        const currentPath = window.location.pathname;
        const prefix = currentPath.includes("/customer/") || currentPath.includes("/agent/") || currentPath.includes("/admin/") ? "../" : "./";
        window.location.href = `${prefix}login.html`;
    },

    /**
     * Enforce authentication and role permissions on protected pages.
     * @param {string|string[]} allowedRoles - 'customer', 'agent', 'admin', or array of roles
     */
    requireAuth: function(allowedRoles = null) {
        if (!this.isLoggedIn()) {
            const currentPath = window.location.pathname;
            const prefix = currentPath.includes("/customer/") || currentPath.includes("/agent/") || currentPath.includes("/admin/") ? "../" : "./";
            window.location.href = `${prefix}login.html`;
            return false;
        }

        const role = this.getRole();
        if (allowedRoles) {
            const roles = Array.isArray(allowedRoles) ? allowedRoles : [allowedRoles];
            if (!roles.includes(role)) {
                alert(`Access Denied: Your account role (${role}) is not authorized for this section.`);
                // Redirect to appropriate dashboard
                const currentPath = window.location.pathname;
                const prefix = currentPath.includes("/customer/") || currentPath.includes("/agent/") || currentPath.includes("/admin/") ? "../" : "./";
                if (role === "customer") {
                    window.location.href = `${prefix}customer/dashboard.html`;
                } else if (role === "admin") {
                    window.location.href = `${prefix}admin/dashboard.html`;
                } else {
                    window.location.href = `${prefix}agent/dashboard.html`;
                }
                return false;
            }
        }

        this.updateNavUser();
        return true;
    },

    /**
     * Populate user details in navigation bar if elements exist.
     */
    updateNavUser: function() {
        const user = this.getUser();
        const role = this.getRole();
        const userNameEl = document.getElementById("nav-user-name");
        const userRoleEl = document.getElementById("nav-user-role");

        if (userNameEl && user) {
            userNameEl.textContent = user.name || user.username || user.email;
        }
        if (userRoleEl && role) {
            userRoleEl.textContent = role.toUpperCase();
        }
    },

    /**
     * Helper to display temporary alert messages in forms.
     */
    showAlert: function(elementId, message, type = "danger") {
        const alertEl = document.getElementById(elementId);
        if (!alertEl) return;
        alertEl.className = `alert alert-${type}`;
        alertEl.textContent = message;
        alertEl.style.display = "flex";
    },

    hideAlert: function(elementId) {
        const alertEl = document.getElementById(elementId);
        if (alertEl) {
            alertEl.style.display = "none";
        }
    }
};
