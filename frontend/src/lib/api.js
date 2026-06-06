const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/**
 * Helper to handle fetch responses and parse JSON
 */
async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = "API call failed";
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch (_) {}
    throw new Error(errorDetail);
  }
  return response.json();
}

let isRefreshing = false;
let refreshSubscribers = [];

function subscribeTokenRefresh(cb) {
  refreshSubscribers.push(cb);
}

function onRefreshed(token) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

/**
 * Custom request wrapper supporting dynamic header injection
 * and queued JWT token refreshing.
 */
async function request(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;
  options.headers = options.headers || {};
  
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      options.headers["Authorization"] = `Bearer ${token}`;
    }
  }

  let response = await fetch(url, options);

  // Catch 401 to silently run Token Rotation
  if (response.status === 401 && typeof window !== "undefined") {
    const refreshToken = localStorage.getItem("refresh_token");
    // Don't loop refresh requests
    if (refreshToken && !options._retry && !path.includes("/auth/refresh") && !path.includes("/auth/login")) {
      options._retry = true;
      
      if (!isRefreshing) {
        isRefreshing = true;
        try {
          const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken })
          });
          
          if (refreshRes.ok) {
            const data = await refreshRes.json();
            localStorage.setItem("access_token", data.access_token);
            localStorage.setItem("refresh_token", data.refresh_token);
            localStorage.setItem("user", JSON.stringify(data.user));
            
            isRefreshing = false;
            onRefreshed(data.access_token);
          } else {
            isRefreshing = false;
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
            localStorage.removeItem("user");
            window.location.href = "/login";
            return response;
          }
        } catch (e) {
          isRefreshing = false;
          return response;
        }
      }

      // Queue concurrent requests
      const retryOriginalRequest = new Promise((resolve) => {
        subscribeTokenRefresh((token) => {
          options.headers["Authorization"] = `Bearer ${token}`;
          resolve(fetch(url, options));
        });
      });
      
      response = await retryOriginalRequest;
    }
  }

  return response;
}

export const api = {
  // --- Authentication APIs ---

  async register(fullName, email, password) {
    const response = await request("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_name: fullName, email, password })
    });
    return handleResponse(response);
  },

  async login(email, password) {
    const response = await request("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    return handleResponse(response);
  },

  async googleLogin(idToken) {
    const response = await request("/auth/google", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_token: idToken })
    });
    return handleResponse(response);
  },

  async logout() {
    const refreshToken = localStorage.getItem("refresh_token") || "";
    const response = await request("/auth/logout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken })
    });
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    return handleResponse(response);
  },

  async forgotPassword(email) {
    const response = await request("/auth/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });
    return handleResponse(response);
  },

  async resetPassword(token, newPassword) {
    const response = await request("/auth/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password: newPassword })
    });
    return handleResponse(response);
  },

  // --- Super Admin Panel APIs ---

  async getUsers(skip = 0, limit = 50, search = "", role = "") {
    let url = `/admin/users?skip=${skip}&limit=${limit}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (role) url += `&role=${encodeURIComponent(role)}`;
    const response = await request(url);
    return handleResponse(response);
  },

  async getUser(id) {
    const response = await request(`/admin/users/${id}`);
    return handleResponse(response);
  },

  async updateUserRole(id, role) {
    const response = await request(`/admin/users/${id}/role`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role })
    });
    return handleResponse(response);
  },

  async updateUserStatus(id, isActive) {
    const response = await request(`/admin/users/${id}/status`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: isActive })
    });
    return handleResponse(response);
  },

  async deleteUser(id) {
    const response = await request(`/admin/users/${id}`, {
      method: "DELETE"
    });
    return handleResponse(response);
  },

  async getAuditLogs(skip = 0, limit = 100, action = "", userId = "", resourceType = "") {
    let url = `/admin/audit-logs?skip=${skip}&limit=${limit}`;
    if (action) url += `&action=${encodeURIComponent(action)}`;
    if (userId) url += `&user_id=${encodeURIComponent(userId)}`;
    if (resourceType) url += `&resource_type=${encodeURIComponent(resourceType)}`;
    const response = await request(url);
    return handleResponse(response);
  },

  async getSystemHealth() {
    const response = await request("/admin/health");
    return handleResponse(response);
  },

  async getPlatformStats() {
    const response = await request("/admin/stats");
    return handleResponse(response);
  },

  async getApiUsageTelemetry() {
    const response = await request("/admin/api-usage");
    return handleResponse(response);
  },

  // --- Original Tender Ingestion APIs ---

  async getTenders(skip = 0, limit = 50, search = "") {
    let url = `/tenders?skip=${skip}&limit=${limit}`;
    if (search) {
      url += `&search=${encodeURIComponent(search)}`;
    }
    const response = await request(url);
    return handleResponse(response);
  },

  async getTender(id) {
    const response = await request(`/tenders/${id}`);
    return handleResponse(response);
  },

  async createTender(tenderData) {
    const response = await request("/tenders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(tenderData)
    });
    return handleResponse(response);
  },

  async getTenderMetadata(id) {
    const response = await request(`/metadata/${id}`);
    return handleResponse(response);
  },

  async getBOQ(id) {
    const response = await request(`/tenders/${id}/boq`);
    return handleResponse(response);
  },

  async getBOQSummary(id) {
    const response = await request(`/tenders/${id}/boq/summary`);
    return handleResponse(response);
  },

  async getBOQCategories(id) {
    const response = await request(`/tenders/${id}/boq/categories`);
    return handleResponse(response);
  },

  async getRiskAnalysis(id) {
    const response = await request(`/tenders/${id}/risk`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });
    return handleResponse(response);
  },

  async matchEligibility(eligibilityRule, limit = 5) {
    const response = await request("/projects/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        eligibility_rule: eligibilityRule,
        limit: limit
      })
    });
    return handleResponse(response);
  },

  async getProjects(skip = 0, limit = 10, search = "", domain = "", minValue = null) {
    let url = `/projects?skip=${skip}&limit=${limit}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (domain) url += `&domain=${encodeURIComponent(domain)}`;
    if (minValue) url += `&min_value=${minValue}`;
    const response = await request(url);
    return handleResponse(response);
  },

  async uploadProject(documentType, file) {
    const formData = new FormData();
    formData.append("file", file);
    const response = await request(`/projects/extract?document_type=${documentType}`, {
      method: "POST",
      body: formData
    });
    return handleResponse(response);
  },

  async getCapabilities() {
    const response = await request("/projects/capabilities");
    return handleResponse(response);
  },

  async getRecommendation(id, annualTurnovers, netWorth, eligibilityRules) {
    const response = await request(`/tenders/${id}/recommendation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        annual_turnovers: annualTurnovers,
        net_worth: netWorth,
        eligibility_rules: eligibilityRules
      })
    });
    return handleResponse(response);
  },

  async getAIAnalystReport(id, annualTurnovers, netWorth, eligibilityRules) {
    const response = await request(`/tenders/${id}/analyst`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        annual_turnovers: annualTurnovers,
        net_worth: netWorth,
        eligibility_rules: eligibilityRules
      })
    });
    return handleResponse(response);
  },

  async importExcel(file) {
    const formData = new FormData();
    formData.append("file", file);
    const response = await request("/imports/excel", {
      method: "POST",
      body: formData
    });
    return handleResponse(response);
  },

  async getReviewQueue() {
    const response = await request("/reviews/queue");
    return handleResponse(response);
  },

  async submitReview(id, payload) {
    const response = await request(`/reviews/${id}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return handleResponse(response);
  },

  async getReviewHistory(id) {
    const response = await request(`/reviews/${id}/history`);
    return handleResponse(response);
  }
};
