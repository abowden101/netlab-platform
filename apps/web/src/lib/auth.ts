/** Token storage + API/WS base URLs. */

const TOKEN_KEY = 'netlab-token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function apiBase(): string {
  return import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
}

export function wsBase(): string {
  const base = apiBase();
  return base.replace(/^http/, 'ws');
}
