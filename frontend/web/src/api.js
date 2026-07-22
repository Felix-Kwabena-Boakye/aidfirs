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
  timeout: 120000,
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
    api.patch(`/accounts/profile/${id}/`, data),

  deleteUser: (id) =>
    api.delete(`/accounts/users/${id}/`),

  activateUser: (id) =>
    api.post(`/accounts/users/${id}/activate/`, {
      action: "activate",
    }),

  deactivateUser: (id) =>
    api.post(`/accounts/users/${id}/deactivate/`, {
      action: "deactivate",
    }),

  resetPassword: (id, password) =>
    api.post(`/accounts/users/${id}/reset-password/`, {
      password,
    }),
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

  runDiagnostics: (data) =>
    api.post("/devices/diagnostics/", data),

  deleteDevice: (id) =>
    api.delete(`/devices/${id}/`),
};

/* =========================================================
   📁 RECOVERY API
 ========================================================= */
export const recoveryAPI = {
  // Start a new recovery job
  startRecovery: (data) => api.post("/recovery/start/", data),

  // Jobs
  getJobs: (params) => api.get("/recovery/jobs/", { params }),
  getJob: (id) => api.get(`/recovery/jobs/${id}/`),
  getPendingJobs: () => api.get("/recovery/jobs/pending/"),
  updateJob: (id, data) => api.patch(`/recovery/jobs/${id}/`, data),

  // Recovered files
  getRecoveredFiles: (caseId, params) =>
    api.get(`/recovery/files/`, { params: { case_id: caseId, ...params } }),

  getAllFiles: (params) => api.get("/recovery/files/", { params }),

  searchFiles: (params) => api.get("/recovery/files/search/", { params }),

  getFile: (id) => api.get(`/recovery/files/${id}/`),


  // Hash verification - calls server to re-compute and compare
  verifyFileHash: (id) => api.post(`/recovery/files/${id}/verify/`),

  // Preview endpoint returns file content with appropriate MIME type
  previewFileUrl: (id) =>
    `${API_BASE_URL}/recovery/files/${id}/preview/`,

  // Download URL (token appended by component)
  downloadFileUrl: (id) =>
    `${API_BASE_URL}/recovery/files/${id}/download/`,

  // ZIP export of all files in a case
  exportZip: (caseId) =>
    api.get(`/recovery/export/?case_id=${caseId}`, { responseType: "blob" }),
};

/* =========================================================
   📅 TIMELINE API
========================================================= */
export const timelineAPI = {
  getTimeline: (caseId, params) =>
    api.get(`/recovery/timeline/`, { params: { case_id: caseId, ...params } }),

  addEvent: (data) =>
    api.post("/recovery/timeline/", data),

  exportTimeline: (caseId) =>
    api.get(`/recovery/timeline/export/?case_id=${caseId}`, {
      responseType: "blob",
    }),
};

/* =========================================================
   🔗 CHAIN OF CUSTODY API
========================================================= */
export const chainOfCustodyAPI = {
  getChainOfCustody: (caseId) =>
    api.get(`/cases/${caseId}/chain_of_custody/`),

  exportCoC: (caseId) =>
    api.get(`/recovery/coc/export/?case_id=${caseId}`, {
      responseType: "blob",
    }),
};

/* =========================================================
   📊 REPORTS API
========================================================= */
export const reportsAPI = {
  generateReport: (data) =>
    api.post("/reports/generate/", data),

  getReports: (caseId) =>
    api.get(`/reports/?case_id=${caseId}`),

  getReport: (id) =>
    api.get(`/reports/${id}/`),

  downloadReport: (id, format) =>
    api.get(`/reports/${id}/download/?format=${format}`, {
      responseType: "blob",
    }),

  deleteReport: (id) =>
    api.delete(`/reports/${id}/`),
};

/* =========================================================
   ANALYSIS
========================================================= */
export const analysisAPI = {
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

  trainModel: () =>
    api.post("/analysis/train-model/"),

  getModelInfo: () =>
    api.get("/analysis/model-info/"),

  predictRecoverability: (data) =>
    api.post("/analysis/predict-recoverability/", data),

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
