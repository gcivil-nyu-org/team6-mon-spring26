"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import type { User } from "@/types";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (credential: string) => Promise<void>;
  register: (username: string, email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const fetchUser = useCallback(async () => {
    try {
      const res = await authApi.me();
      setUser(res.data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
    const handleLogout = () => {
      setUser(null);
      router.push("/login");
    };
    window.addEventListener("auth:logout", handleLogout);
    return () => window.removeEventListener("auth:logout", handleLogout);
  }, [fetchUser, router]);

  const login = useCallback(
    async (username_or_email: string, password: string) => {
      const res = await authApi.login({ username_or_email, password });
      setUser(res.data.user);
      if (!res.data.user.username) {
        router.push("/complete-profile");
      } else {
        router.push("/dashboard");
      }
    },
    [router]
  );

  const loginWithGoogle = useCallback(
    async (credential: string) => {
      const res = await authApi.googleLogin(credential);
      setUser(res.data.user);
      if (!res.data.user.username) {
        router.push("/complete-profile");
      } else {
        router.push("/dashboard");
      }
    },
    [router]
  );

  const register = useCallback(
    async (username: string, email: string, password: string, fullName?: string) => {
      const res = await authApi.register({ username, email, password, full_name: fullName });
      setUser(res.data.user);
      router.push("/dashboard");
    },
    [router]
  );

  const logout = useCallback(async () => {
    await authApi.logout().catch(() => {});
    setUser(null);
    router.push("/");
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, loading, login, loginWithGoogle, register, logout, refreshUser: fetchUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
