import axios from "axios";

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || "http://51.158.125.49:34130/",
  headers: {
    "Content-Type": "application/json",
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle 401 Unauthorized errors
    if (error.response && error.response.status === 401) {
      // Get auth store and logout user
      const { logout } =
        require("../contexts/authStore").useAuthStore.getState();
      logout();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;
