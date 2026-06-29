import axios from "axios";

/**
 * Central API client for AI Digital Forensics System
 * Works in both:
 * - Local development
 * - Production (Vercel + Render)
 */

const API = axios.create({
    baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000",
    timeout: 60000, // important for AI/forensics processing
    headers: {
        "Content-Type": "application/json",
    },
});

/**
 * Attach JWT token automatically to every request
 */
API.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem("access_token");

        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }

        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

/**
 * Handle global API responses
 * - auto logout on 401
 * - clean error handling
 */
API.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response) {
            const status = error.response.status;

            // Unauthorized → token expired or invalid
            if (status === 401) {
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token");

                // optional redirect
                window.location.href = "/login";
            }
        }

        return Promise.reject(error);
    }
);

export default API;
