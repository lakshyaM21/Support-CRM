/**
 * Support CRM - Central API Client Module
 * Provides unified, promise-based HTTP request methods using Vanilla Fetch API.
 */

// Dynamically determine the backend API base URL
// If frontend is served directly by FastAPI (e.g. http://localhost:8000/frontend/...)
// origin matches. If served from another port/file, falls back to http://127.0.0.1:8000
const API_BASE_URL = (function() {
    if (window.location.protocol.startsWith("http")) {
        // If served from FastAPI on port 8000
        return window.location.origin;
    }
    // Fallback for file:// or external tools
    return "http://127.0.0.1:8000";
})();

const API = {
    /**
     * Get stored JWT access token from localStorage.
     */
    getToken: function() {
        return localStorage.getItem("crm_token");
    },

    /**
     * Store JWT token and user info.
     */
    setSession: function(token, user, role) {
        localStorage.setItem("crm_token", token);
        localStorage.setItem("crm_user", JSON.stringify(user));
        localStorage.setItem("crm_role", role);
    },

    /**
     * Clear session data.
     */
    clearSession: function() {
        localStorage.removeItem("crm_token");
        localStorage.removeItem("crm_user");
        localStorage.removeItem("crm_role");
    },

    /**
     * Make an authenticated HTTP request.
     * @param {string} endpoint - API route (e.g., "/tickets/")
     * @param {object} options - Fetch options (method, body, headers, etc.)
     */
    request: async function(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const headers = {
            "Content-Type": "application/json",
            ...(options.headers || {})
        };

        const token = this.getToken();
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            // Handle unauthorized / token expired
            if (response.status === 401) {
                // If on a protected page, prompt to login
                const currentPath = window.location.pathname;
                if (!currentPath.includes("login.html") && !currentPath.includes("register.html") && currentPath !== "/" && !currentPath.endsWith("index.html")) {
                    this.clearSession();
                    // Determine redirect path
                    const rootPrefix = currentPath.includes("/customer/") || currentPath.includes("/agent/") || currentPath.includes("/admin/") ? "../" : "./";
                    window.location.href = `${rootPrefix}login.html?expired=1`;
                    return null;
                }
            }

            // Parse response body
            let data = null;
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.includes("application/json")) {
                data = await response.json();
            } else {
                data = await response.text();
            }

            if (!response.ok) {
                // Format error message from FastAPI response
                let errorMsg = "An error occurred";
                if (data && data.detail) {
                    if (Array.isArray(data.detail)) {
                        errorMsg = data.detail.map(d => `${d.loc ? d.loc.join('.') : ''}: ${d.msg}`).join(', ');
                    } else {
                        errorMsg = data.detail;
                    }
                } else if (data && data.message) {
                    errorMsg = data.message;
                }
                throw new Error(errorMsg);
            }

            return data;
        } catch (err) {
            console.error(`API Error on ${endpoint}:`, err);
            throw err;
        }
    },

    // Convenience methods
    get: function(endpoint) {
        return this.request(endpoint, { method: "GET" });
    },

    post: function(endpoint, body) {
        return this.request(endpoint, {
            method: "POST",
            body: JSON.stringify(body)
        });
    },

    put: function(endpoint, body) {
        return this.request(endpoint, {
            method: "PUT",
            body: JSON.stringify(body)
        });
    },

    delete: function(endpoint) {
        return this.request(endpoint, { method: "DELETE" });
    }
};
