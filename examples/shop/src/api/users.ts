import { api } from "./client";

export interface User {
  id: string;
  name: string;
  email: string;
}

export const me = () => api.get<User>("/users/me");

export const updateProfile = (patch: Partial<User>) => api.put<User>("/users/me", patch);

export const login = (email: string, password: string) =>
  fetch("/auth/session", {
    method: "POST",
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });

export const logout = () => fetch("/auth/session", { method: "DELETE", credentials: "include" });
