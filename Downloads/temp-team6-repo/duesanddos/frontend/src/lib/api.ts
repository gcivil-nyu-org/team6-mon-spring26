import axios, { AxiosError } from "axios";

export const api = axios.create({
  baseURL: "/api/",
  withCredentials: true, // send httpOnly cookies
  headers: { "Content-Type": "application/json" },
});

// Intercept 401 and attempt token refresh once
let isRefreshing = false;
let failedQueue: { resolve: (v: unknown) => void; reject: (e: unknown) => void }[] = [];

const processQueue = (error: AxiosError | null) => {
  failedQueue.forEach((p) => (error ? p.reject(error) : p.resolve(null)));
  failedQueue = [];
};

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const originalRequest = error.config as typeof error.config & { _retry?: boolean };
    
    // Don't retry on 401 for auth endpoints or if already retried
    const isAuthRequest = originalRequest?.url?.includes("/auth/");
    const isMeRequest = originalRequest?.url === "me/" || originalRequest?.url === "/api/me/";
    
    if (error.response?.status === 401 && !originalRequest?._retry && !isAuthRequest && !isMeRequest) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(() => api(originalRequest!));
      }
      originalRequest!._retry = true;
      isRefreshing = true;
      try {
        await api.post("/auth/token/refresh/");
        processQueue(null);
        return api(originalRequest!);
      } catch (refreshError) {
        processQueue(refreshError as AxiosError);
        // Clear auth state — let the app handle redirect
        window.dispatchEvent(new Event("auth:logout"));
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

// ─── Auth API ─────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: { username: string; email: string; password: string; full_name?: string }) =>
    api.post("auth/register/", data),
  login: (data: { username_or_email: string; password: string }) => api.post("auth/login/", data),
  googleLogin: (credential: string) => api.post("auth/google/", { credential }),
  logout: () => api.post("auth/logout/"),
  forgotPassword: (data: { email: string }) => api.post("auth/forgot-password/", data),
  resetPassword: (data: { uid: string; token: string; new_password: string }) =>
    api.post("auth/reset-password/", data),
  me: () => api.get("me/"),
  updateMe: (data: FormData | Record<string, string>) => api.patch("me/", data),
};
