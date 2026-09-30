import axios from "axios";
import { ElMessage } from "element-plus";

const http = axios.create({ baseURL: "/api", timeout: 120000 });

http.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

http.interceptors.response.use(
  (response) => {
    if (response.config.responseType === "blob") return response.data;
    const body = response.data;
    if (body && typeof body.code === "number" && body.code !== 0) {
      ElMessage.error(body.message || "请求失败");
      return Promise.reject(new Error(body.message || "请求失败"));
    }
    return body.data;
  },
  (error) => {
    const message = error.response?.data?.message || error.message || "请求失败";
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      if (location.pathname !== "/login") location.href = "/login";
    }
    ElMessage.error(message);
    return Promise.reject(new Error(message));
  }
);

export default http;
