import axios from "axios";

/* =========================================================
   🌐 BASE URL CONFIG
========================================================= */
const getApiBaseUrl = () => {
  // Vercel / production env
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }

  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }

  // local development
  if (
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
  ) {
    return "http://127.0.0.1:8000/api";
  }

  // fallback production backend
  return "https://aidfirs.onrender.com/api";
};

const API_BASE_URL = getApiBaseUrl();

/* =========================================================
   ⚙️ AXIOS INSTANCE
========================================================= */
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    "Content-Type": "application/json",
  },
});

/* =========================================================
   🔐 REQUEST INTERCEPTOR (JWT ATTACH)
========================================================= */
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

/* =========================================================
   📡 CASES API (USED BY TopBar.jsx)
========================================================= */
export const casesAPI = {
  getCases: () => api.get("/cases/"),

  globalSearch: (q) =>
    api.get(`/cases/search/?q=${encodeURIComponent(q)}`),

  getCase: (id) => api.get(`/cases/${id}/`),
  createCase: (data) => api.post("/cases/", data),
  updateCase: (id, data) => api.patch(`/cases/${id}/`, data),
  deleteCase: (id) => api.delete(`/cases/${id}/`),
};

/* =========================================================
   📁 EVIDENCE API
========================================================= */
export const evidenceAPI = {
  getEvidence: () => api.get("/evidence/"),
  uploadEvidence: (data) => api.post("/evidence/", data),
  getEvidenceItem: (id) => api.get(`/evidence/${id}/`),
};

/* =========================================================
   🧠 ANALYSIS API
========================================================= */
export const analysisAPI = {
  getAnalyses: () => api.get("/analysis/"),
  createAnalysis: (data) => api.post("/analysis/", data),
};

/* =========================================================
   🔧 DEVICES API
========================================================= */
export const devicesAPI = {
  getDevices: () => api.get("/devices/"),
};

/* =========================================================
   🔑 AUTH API
========================================================= */
export const authAPI = {
  login: (data) => api.post("/accounts/login/", data),
  register: (data) => api.post("/accounts/register/", data),
  getProfile: () => api.get("/accounts/profile/"),
};

/* =========================================================
   📊 AUDIT LOGS
========================================================= */
export const auditLogsAPI = {
  getAuditLogs: () => api.get("/accounts/audit-logs/"),
};

/* =========================================================
   EXPORT DEFAULT
========================================================= */
export default api;
