import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Add request interceptor to include auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle token refresh on 401
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) prom.reject(error);
    else prom.resolve(token);
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      // Don't retry the token refresh endpoint itself — that would loop forever
      if (originalRequest.url?.includes('/accounts/token/refresh/')) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/';
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Queue any other requests that come in while we're refreshing
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        }).catch(err => Promise.reject(err));
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
        const res = await api.post('/accounts/token/refresh/', { refresh: refreshToken });
        const newAccessToken = res.data.access;
        localStorage.setItem('access_token', newAccessToken);
        api.defaults.headers.common['Authorization'] = `Bearer ${newAccessToken}`;
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

    return Promise.reject(error);
  }
);

export const authAPI = {
  login: (credentials) => api.post('/accounts/login/', credentials),
  register: (userData) => api.post('/accounts/register/', userData),
  refreshToken: (refresh) => api.post('/accounts/token/refresh/', { refresh }),
  getProfile: () => api.get('/accounts/profile/'),
  googleOAuth: (token) => api.post('/accounts/oauth/google/', { token }),
  appleOAuth: (token) => api.post('/accounts/oauth/apple/', { token }),
};

export const casesAPI = {
  getCases: () => api.get('/cases/'),
  createCase: (data) => api.post('/cases/', data),
  getCase: (id) => api.get(`/cases/${id}/`),
  updateCase: (id, data) => api.patch(`/cases/${id}/`, data),
  deleteCase: (id) => api.delete(`/cases/${id}/`),
};

export const evidenceAPI = {
  getEvidence: () => api.get('/evidence/'),
  uploadEvidence: (data) => api.post('/evidence/', data),
  getEvidenceItem: (id) => api.get(`/evidence/${id}/`),
  updateEvidence: (id, data) => api.patch(`/evidence/${id}/`, data),
  deleteEvidence: (id) => api.delete(`/evidence/${id}/`),
  // Digital Forensics API Endpoints
  tskImage: (id) => api.post(`/evidence/${id}/tsk_image/`),
  tskPartitions: (id) => api.post(`/evidence/${id}/tsk_partitions/`),
  tskFiles: (id, offset = '0') => api.post(`/evidence/${id}/tsk_files/`, { offset }),
  tskExtract: (id, inode, offset = '0') => api.post(`/evidence/${id}/tsk_extract/`, { inode, offset }),
  tskTimeline: (id) => api.post(`/evidence/${id}/tsk_timeline/`),
  tskRecoveredMetadata: (id, offset = '0') => api.post(`/evidence/${id}/tsk_recovered_metadata/`, { offset }),
  downloadReport: (id) => api.get(`/evidence/${id}/report/`, { responseType: 'blob' }),
};

export const analysisAPI = {
  getAnalyses: () => api.get('/analysis/'),
  createAnalysis: (data) => api.post('/analysis/', data),
  getAnalysis: (id) => api.get(`/analysis/${id}/`),
  // AI Assistant Endpoint
  chatWithAssistant: (case_context, forensic_data, message, history = []) =>
    api.post('/analysis/chat/', { case_context, forensic_data, message, history }),
  getEvidenceSuggestions: (case_context) =>
    api.post('/analysis/evidence-suggestions/', { case_context }),
  classify: (forensic_data) =>
    api.post('/analysis/classify/', { forensic_data }),
  detectAnomalies: (forensic_data) =>
    api.post('/analysis/detect-anomalies/', { forensic_data }),
  generateReport: (case_context, forensic_data, ai_findings) =>
    api.post('/analysis/generate-report/', { case_context, forensic_data, ai_findings }),
};

export const aiSettingsAPI = {
  getSettings: () => api.get('/accounts/ai-settings/'),
  updateSettings: (data) => api.post('/accounts/ai-settings/', data),
};

export const usersAPI = {
  getUsers: () => api.get('/accounts/users/'),
  createUser: (data) => api.post('/accounts/users/create/', data),
  activateUser: (userId) => api.post(`/accounts/users/${userId}/activate/`, { action: 'activate' }),
  deactivateUser: (userId) => api.post(`/accounts/users/${userId}/deactivate/`, { action: 'deactivate' }),
};

export const auditLogsAPI = {
  getAuditLogs: (limit = 500) => api.get(`/accounts/audit-logs/?limit=${limit}`),
};

export default api;
