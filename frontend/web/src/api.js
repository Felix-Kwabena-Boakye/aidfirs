import axios from "axios";

const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }

  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }

  const hostname = window.location.hostname;

  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://127.0.0.1:8000/api";
  }

  return "https://aidfirs.onrender.com/api";
};

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    "Content-Type": "application/json",
  },
});

/* =========================
   CASES API (MISSING BEFORE)
========================= */
export const casesAPI = {
  getCases: () => api.get("/cases/"),
  createCase: (data) => api.post("/cases/", data),
  getCase: (id) => api.get(`/cases/${id}/`),
  updateCase: (id, data) => api.patch(`/cases/${id}/`, data),
  deleteCase: (id) => api.delete(`/cases/${id}/`),

  getChainOfCustody: (id) =>
    api.get(`/cases/${id}/chain_of_custody/`),

  getTimeline: (id, params = {}) =>
    api.get(`/cases/${id}/timeline/`, { params }),

  getEvidence: (id) =>
    api.get(`/cases/${id}/evidence/`),

  globalSearch: (q) =>
    api.get(`/cases/search/?q=${encodeURIComponent(q)}`),
};

export default api;
