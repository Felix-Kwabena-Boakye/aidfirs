import axios from "axios";

/* =========================================================
   🌐 BASE URL CONFIG
========================================================= */
const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }

  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }

  if (
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
  ) {
    return "http://127.0.0.1:8000/api";
  }

  return "https://aidfirs.onrender.com/api";
};

const API_BASE_URL = getApiBaseUrl();

/* =========================================================
   AXIOS INSTANCE
========================================================= */
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    "Content-Type": "application/json",
  },
});

/* =========================================================
   REQUEST INTERCEPTOR
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
   RESPONSE INTERCEPTOR
========================================================= */
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      localStorage.getItem("refresh_token")
    ) {
      originalRequest._retry = true;

      try {
        const res = await axios.post(
          `${API_BASE_URL}/accounts/token/refresh/`,
          {
            refresh: localStorage.getItem("refresh_token"),
          }
        );

        const access = res.data.access;

        localStorage.setItem("access_token", access);

        originalRequest.headers.Authorization = `Bearer ${access}`;

        return api(originalRequest);
      } catch (err) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");
        window.location.href = "/";
        return Promise.reject(err);
      }
    }

    return Promise.reject(error);
  }
);

/* =========================================================
   AUTH API
========================================================= */
export const authAPI = {
  login: (data) => api.post("/accounts/login/", data),

  register: (data) => api.post("/accounts/register/", data),

  refreshToken: (refresh) =>
    api.post("/accounts/token/refresh/", { refresh }),

  getProfile: () =>
    api.get("/accounts/profile/"),

  googleOAuth: (data) =>
    api.post("/accounts/oauth/google/", data),

  changePassword: (data) =>
    api.post("/accounts/change-password/", data),
};

/* =========================================================
   USERS API
========================================================= */
export const usersAPI = {
  getUsers: () =>
    api.get("/accounts/users/"),

  createUser: (data) =>
    api.post("/accounts/users/create/", data),

  updateUser: (id, data) =>
    api.patch(`/accounts/users/${id}/`, data),

  deleteUser: (id) =>
    api.delete(`/accounts/users/${id}/`),
};

/* =========================================================
   AI SETTINGS
========================================================= */
export const aiSettingsAPI = {
  getSettings: () =>
    api.get("/accounts/ai-settings/"),

  updateSettings: (data) =>
    api.post("/accounts/ai-settings/", data),
};

/* =========================================================
   CASES
========================================================= */
export const casesAPI = {
  getCases: () =>
    api.get("/cases/"),

  getCase: (id) =>
    api.get(`/cases/${id}/`),

  createCase: (data) =>
    api.post("/cases/", data),

  updateCase: (id, data) =>
    api.patch(`/cases/${id}/`, data),

  deleteCase: (id) =>
    api.delete(`/cases/${id}/`),

  getEvidence: (id) =>
    api.get(`/cases/${id}/evidence/`),

  getTimeline: (id) =>
    api.get(`/cases/${id}/timeline/`),

  getChainOfCustody: (id) =>
    api.get(`/cases/${id}/chain_of_custody/`),

  globalSearch: (q) =>
    api.get(`/cases/search/?q=${encodeURIComponent(q)}`),
};

/* =========================================================
   EVIDENCE
========================================================= */
export const evidenceAPI = {
  getEvidence: () =>
    api.get("/evidence/"),

  uploadEvidence: (data) =>
    api.post("/evidence/", data),

  getEvidenceItem: (id) =>
    api.get(`/evidence/${id}/`),

  updateEvidence: (id, data) =>
    api.patch(`/evidence/${id}/`, data),

  deleteEvidence: (id) =>
    api.delete(`/evidence/${id}/`),

  verifyIntegrity: (id) =>
    api.post(`/evidence/${id}/verify_integrity/`),

  photorecCarve: (id) =>
    api.post(`/evidence/${id}/photorec-carve/`),

  testdiskScan: (id) =>
    api.post(`/evidence/${id}/testdisk-scan/`),

  autopsyIngest: (id) =>
    api.post(`/evidence/${id}/autopsy-ingest/`),

  recoverAndAnalyze: (id) =>
    api.post(`/evidence/${id}/recover-and-analyze/`),
};

/* =========================================================
   DEVICES
========================================================= */
export const devicesAPI = {
  getDevices: () =>
    api.get("/devices/"),

  startScanning: () =>
    api.post("/devices/scan/"),

  stopScanning: () =>
    api.delete("/devices/scan/"),

  refreshDevices: () =>
    api.post("/devices/refresh/"),
};

/* =========================================================
   ANALYSIS
========================================================= */
export const analysisAPI = {
  // =========================
  // CRUD
  // =========================
  getAnalyses: () =>
    api.get("/analysis/"),

  createAnalysis: (data) =>
    api.post("/analysis/", data),

  getAnalysis: (id) =>
    api.get(`/analysis/${id}/`),

  updateAnalysis: (id, data) =>
    api.patch(`/analysis/${id}/`, data),

  deleteAnalysis: (id) =>
    api.delete(`/analysis/${id}/`),

  completeAnalysis: (id) =>
    api.post(`/analysis/${id}/complete/`),

  // =========================
  // AI Assistant
  // =========================
  chatWithAssistant: (
    case_context,
    forensic_data,
    message,
    history = []
  ) =>
    api.post("/analysis/chat/", {
      case_context,
      forensic_data,
      message,
      history,
    }),

  classify: (forensic_data) =>
    api.post("/analysis/classify/", {
      forensic_data,
    }),

  detectAnomalies: (forensic_data) =>
    api.post("/analysis/detect-anomalies/", {
      forensic_data,
    }),

  generateReport: (data) =>
    api.post("/analysis/generate-report/", data),

  evidenceSuggestions: (case_context) =>
    api.post("/analysis/evidence-suggestions/", {
      case_context,
    }),

  // =========================
  // AI Oracle
  // =========================
  trainModel: () =>
    api.post("/analysis/train-model/"),

  getModelInfo: () =>
    api.get("/analysis/model-info/"),

  predictRecoverability: (data) =>
    api.post("/analysis/predict-recoverability/", data),

  // =========================
  // System Agent
  // =========================
  systemExecute: (instruction) =>
    api.post("/analysis/system-execute/", {
      instruction,
    }),
};

/* =========================================================
   AUDIT LOGS
========================================================= */
export const auditLogsAPI = {
  getAuditLogs: (limit = 500) =>
    api.get(`/accounts/audit-logs/?limit=${limit}`),
};

export default api;
