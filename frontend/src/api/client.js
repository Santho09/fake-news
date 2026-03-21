import axios from "axios";

const apiBase =
  import.meta.env.VITE_API_BASE?.toString() || "http://localhost:5001";

export const api = axios.create({
  baseURL: apiBase,
  timeout: 60000,
});

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("token");
  if (token) {
    cfg.headers.Authorization = `Bearer ${token}`;
  }
  return cfg;
});

