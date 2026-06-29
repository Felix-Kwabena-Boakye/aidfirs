import axios from 'axios';

// ✅ FIX: use environment variable (Vercel + local safe)
const API_BASE_URL =
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ========================
// AUTH TOKEN ATTACHMENT
// ========================
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ========================
// REFRESH TOKEN SYSTEM
// ========================
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(token);
  });
  failedQueue = [];
};

// ========================
// RESPONSE INTERCEPTOR
// ========================
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // ========================
    // 401 - AUTH ERROR HANDLING
    // ========================
    if (error.response?.status === 401) {
      const code = error.response.data?.code;
      const responseMsg = error.response.data?.message;

      let cleanMsg = 'Authentication Failed. Please log in again.';

      if (
        code === 'session_expired' ||
        responseMsg?.toLowerCase?.().includes('expired')
      ) {
        cleanMsg = 'Session Expired. Please log in again.';
      } else if (code === 'authentication_failed') {
        cleanMsg = 'Invalid credentials or expired session.';
      } else if (responseMsg) {
        cleanMsg = responseMsg;
      }

      error.message = cleanMsg;

      // ========================
      // TOKEN REFRESH LOGIC
      // ========================
      if (!originalRequest._retry) {
        if (originalRequest.url?.includes('/accounts/token/refresh/')) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/';
          return Promise.reject(error);
        }

        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          }).then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          });
        }

        originalRequest._retry = true;
        isRefreshing = true;

        const refreshToken = localStorage.getItem('refresh_token');

        if (!refreshToken) {
          isRefreshing = false;
          localStorage.removeItem('access_token');
          window.location.href = '/';
          return Promise.reject(error);
        }

        try {
          const res = await api.post('/accounts/token/refresh/', {
            refresh: refreshToken,
          });

          const newAccessToken = res.data.access;

          localStorage.setItem('access_token', newAccessToken);

          api.defaults.headers.common[
            'Authorization'
          ] = `Bearer ${newAccessToken}`;

          processQueue(null, newAccessToken);

          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;

          return api(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);

          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/';

          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }
    }

    // ========================
    // 403 - PERMISSION ERRORS
    // ========================
    if (error.response?.status === 403) {
      const code = error.response.data?.code;
      const responseMsg = error.response.data?.message;

      let cleanMsg =
        'Permission Denied: You are not authorized to perform this action.';

      if (code === 'csrf_error') {
        cleanMsg =
          'CSRF Error: Security verification failed. Request blocked.';
      } else if (code === 'invalid_role') {
        cleanMsg = 'Invalid Role: Access denied for your account type.';
      } else if (code === 'permission_denied') {
        cleanMsg = responseMsg || 'Permission denied.';
      } else if (responseMsg) {
        cleanMsg = responseMsg;
      }

      error.message = cleanMsg;
      return Promise.reject(error);
    }

    return Promise.reject(error);
  }
);

// ========================
// AUTH API
// ========================
export const authAPI = {
  login: (credentials) => api.post('/accounts/login/', credentials),
  register: (userData) => api.post('/accounts/register/', userData),
  refreshToken: (refresh) =>
    api.post('/accounts/token/refresh/', { refresh }),
  getProfile: () => api.get('/accounts/profile/'),

  googleOAuth: (data) => {
    if (typeof data === 'string') {
      return api.post('/accounts/oauth/google/', { token: data });
    }
    return api.post('/accounts/oauth/google/', data);
  },

  changePassword: (passwords) =>
    api.post('/accounts/change-password/', passwords),
};

// ========================
// CASES API
// ========================
export const casesAPI = {
  getCases: () => api.get('/cases/'),
  createCase: (data) => api.post('/cases/', data),
  getCase: (id) => api.get(`/cases/${id}/`),
  updateCase: (id, data) => api.patch(`/cases/${id}/`, data),
  deleteCase: (id) => api.delete(`/cases/${id}/`),
  getChainOfCustody: (caseId) =>
    api.get(`/cases/${caseId}/chain_of_custody/`),
  getTimeline: (caseId, params = {}) =>
    api.get(`/cases/${caseId}/timeline/`, { params }),
  getEvidence: (id) => api.get(`/cases/${id}/evidence/`),
  globalSearch: (q) =>
    api.get(`/cases/search/?q=${encodeURIComponent(q)}`),
};

// ========================
// EVIDENCE API
// ========================
export const evidenceAPI = {
  getEvidence: () => api.get('/evidence/'),
  uploadEvidence: (data) => api.post('/evidence/', data),
  getEvidenceItem: (id) => api.get(`/evidence/${id}/`),
  updateEvidence: (id, data) => api.patch(`/evidence/${id}/`, data),
  deleteEvidence: (id) => api.delete(`/evidence/${id}/`),

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

// ========================
// DEVICES API
// ========================
export const devicesAPI = {
  getDevices: () => api.get('/devices/'),
  startScanning: () => api.post('/devices/scan/'),
  stopScanning: () => api.delete('/devices/scan/'),
  refreshDevices: () => api.post('/devices/refresh/'),
};

// ========================
// ANALYSIS API
// ========================
export const analysisAPI = {
  getAnalyses: () => api.get('/analysis/'),
  createAnalysis: (data) => api.post('/analysis/', data),
  getAnalysis: (id) => api.get(`/analysis/${id}/`),

  chatWithAssistant: (case_context, forensic_data, message, history = []) =>
    api.post('/analysis/chat/', {
      case_context,
      forensic_data,
      message,
      history,
    }),

  classify: (forensic_data) =>
    api.post('/analysis/classify/', { forensic_data }),

  detectAnomalies: (forensic_data) =>
    api.post('/analysis/detect-anomalies/', { forensic_data }),
};

// ========================
// AI SETTINGS
// ========================
export const aiSettingsAPI = {
  getSettings: () => api.get('/accounts/ai-settings/'),
  updateSettings: (data) => api.post('/accounts/ai-settings/', data),
};

// ========================
// USERS API
// ========================
export const usersAPI = {
  getUsers: () => api.get('/accounts/users/'),
  createUser: (data) => api.post('/accounts/users/create/', data),
};

// ========================
// AUDIT LOGS
// ========================
export const auditLogsAPI = {
  getAuditLogs: (limit = 500) =>
    api.get(`/accounts/audit-logs/?limit=${limit}`),
};

export default api;
