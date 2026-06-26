import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

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

    // Handle 401 Unauthorized - authentication failure or session expiration
    if (error.response?.status === 401) {
      const code = error.response.data?.code;
      const responseMsg = error.response.data?.message;
      let cleanMsg = 'Authentication Failed: Please log in.';

      if (code === 'session_expired' || (responseMsg && responseMsg.toLowerCase().includes('expired'))) {
        cleanMsg = 'Session Expired: Please log in again.';
      } else if (code === 'authentication_failed') {
        cleanMsg = 'Authentication Failed: Credentials are invalid or expired.';
      } else if (responseMsg) {
        cleanMsg = responseMsg;
      }

      error.message = cleanMsg;
      if (error.response.data) {
        error.response.data.error = cleanMsg;
        error.response.data.message = cleanMsg;
      }

      // Check if we can attempt token refresh
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
    }

    // Handle 403 Forbidden - role-based access denied or CSRF error
    if (error.response?.status === 403) {
      const code = error.response.data?.code;
      const responseMsg = error.response.data?.message;
      let cleanMsg = 'Permission Denied: Your role is not authorized to perform this action.';

      if (code === 'csrf_error') {
        cleanMsg = 'CSRF Error: Cross-Site Request Forgery verification failed. Request aborted.';
      } else if (code === 'invalid_role') {
        cleanMsg = 'Invalid Role: Your current user role is not authorized for this operation.';
      } else if (code === 'permission_denied') {
        cleanMsg = responseMsg || 'Permission Denied: Access forbidden.';
      } else if (responseMsg) {
        cleanMsg = responseMsg;
      }
      
      error.message = cleanMsg;
      if (error.response.data) {
        error.response.data.error = cleanMsg;
        error.response.data.message = cleanMsg;
      }
      return Promise.reject(error);
    }

    return Promise.reject(error);
  }
);

export const authAPI = {
  login: (credentials) => api.post('/accounts/login/', credentials),
  register: (userData) => api.post('/accounts/register/', userData),
  refreshToken: (refresh) => api.post('/accounts/token/refresh/', { refresh }),
  getProfile: () => api.get('/accounts/profile/'),
  googleOAuth: (data) => {
    if (typeof data === 'string') {
      return api.post('/accounts/oauth/google/', { token: data });
    }
    return api.post('/accounts/oauth/google/', data);
  },
  changePassword: (passwords) => api.post('/accounts/change-password/', passwords),
};

export const casesAPI = {
  getCases: () => api.get('/cases/'),
  createCase: (data) => api.post('/cases/', data),
  getCase: (id) => api.get(`/cases/${id}/`),
  updateCase: (id, data) => api.patch(`/cases/${id}/`, data),
  deleteCase: (id) => api.delete(`/cases/${id}/`),
  getChainOfCustody: (caseId) => api.get(`/cases/${caseId}/chain_of_custody/`),
  getTimeline: (caseId, params = {}) => api.get(`/cases/${caseId}/timeline/`, { params }),
  getEvidence: (id) => api.get(`/cases/${id}/evidence/`),
  globalSearch: (q) => api.get(`/cases/search/?q=${encodeURIComponent(q)}`),
};

export const evidenceAPI = {
  getEvidence: () => api.get('/evidence/'),
  uploadEvidence: (data) => api.post('/evidence/', data),
  getEvidenceItem: (id) => api.get(`/evidence/${id}/`),
  updateEvidence: (id, data) => api.patch(`/evidence/${id}/`, data),
  deleteEvidence: (id) => api.delete(`/evidence/${id}/`),
  verifyIntegrity: (id) => api.post(`/evidence/${id}/verify_integrity/`),
  tskImage: (id) => api.post(`/evidence/${id}/tsk_image/`),
  tskPartitions: (id) => api.post(`/evidence/${id}/tsk_partitions/`),
  tskFiles: (id, offset = '0') => api.post(`/evidence/${id}/tsk_files/`, { offset }),
  tskExtract: (id, inode, offset = '0') => api.post(`/evidence/${id}/tsk_extract/`, { inode, offset }),
  tskTimeline: (id) => api.post(`/evidence/${id}/tsk_timeline/`),
  tskRecoveredMetadata: (id, offset = '0') => api.post(`/evidence/${id}/tsk_recovered_metadata/`, { offset }),
  tskRecoverDeleted: (id, offset = '0') => api.post(`/evidence/${id}/tsk_recover_deleted/`, { offset }),
  recoverSpecificFiles: (id, filesToRecover) => api.post(`/evidence/${id}/tsk_recover_specific/`, { filesToRecover }),
  downloadReport: (id) => api.get(`/evidence/${id}/report/`, { responseType: 'blob' }),
  downloadFile: (id, filePath) =>
    api.get(`/evidence/${id}/download-file/?file_path=${encodeURIComponent(filePath)}`, { responseType: 'blob' }),
  photorecCarve: (id) => api.post(`/evidence/${id}/photorec-carve/`),
  testdiskScan: (id) => api.post(`/evidence/${id}/testdisk-scan/`),
  autopsyIngest: (id) => api.post(`/evidence/${id}/autopsy-ingest/`),
  runExifTool: (id, filePath) => api.post(`/evidence/${id}/exiftool/`, { file_path: filePath }),
  recoverAndAnalyze: (id) => api.post(`/evidence/${id}/recover-and-analyze/`),
  restoreFiles: (id, payload) => api.post(`/evidence/${id}/restore-files/`, payload),
};

export const devicesAPI = {
  getDevices: () => api.get('/devices/'),
  startScanning: () => api.post('/devices/scan/'),
  stopScanning: () => api.delete('/devices/scan/'),
  refreshDevices: () => api.post('/devices/refresh/'),
  getInotifyLogs: () => api.get('/devices/inotify-logs/'),
  runDiagnostics: (payload) => api.post('/devices/diagnostics/', payload),
};

export const analysisAPI = {
  getAnalyses: () => api.get('/analysis/'),
  createAnalysis: (data) => api.post('/analysis/', data),
  getAnalysis: (id) => api.get(`/analysis/${id}/`),
  chatWithAssistant: (case_context, forensic_data, message, history = []) =>
    api.post('/analysis/chat/', { case_context, forensic_data, message, history }),
  getEvidenceSuggestions: (case_context) =>
    api.post('/analysis/evidence-suggestions/', { case_context }),
  classify: (forensic_data) =>
    api.post('/analysis/classify/', { forensic_data }),
  detectAnomalies: (forensic_data) =>
    api.post('/analysis/detect-anomalies/', { forensic_data }),
  generateReport: (case_context, forensic_data, ai_findings, case_id) =>
    api.post('/analysis/generate-report/', { case_context, forensic_data, ai_findings, case_id }),
  systemExecute: (instruction) =>
    api.post('/analysis/system-execute/', { instruction }),
  predictRecoverability: (features) =>
    api.post('/analysis/predict-recoverability/', features),
  getModelInfo: () =>
    api.get('/analysis/model-info/'),
  trainModel: () =>
    api.post('/analysis/train-model/'),
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
  resetPassword: (userId, newPassword) => api.post(`/accounts/users/${userId}/reset-password/`, { new_password: newPassword }),
};

export const auditLogsAPI = {
  getAuditLogs: (limit = 500) => api.get(`/accounts/audit-logs/?limit=${limit}`),
};

export default api;

