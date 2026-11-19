/** Typed client for the netlab API (see docs/api.md). */

import { apiBase, getToken } from '../lib/auth';

export interface Objective {
  id: string;
  title: string;
  description: string;
  engine: string;
  node: string;
}

export interface Lab {
  id: string;
  title: string;
  description: string;
  estimated_minutes: number;
  objectives: Objective[];
  guide?: string;
}

export interface LabNode {
  name: string;
  kind: string;
  image: string;
  status: string;
}

export interface Session {
  id: string;
  lab_slug: string;
  status: string;
  created_at?: string;
  expires_at?: string;
  queue_position?: number | null;
  nodes?: LabNode[];
  links?: { from_node: string; to_node: string }[];
}

export interface GradeResult {
  objective_id: string;
  passed: boolean;
  evidence: string;
  engine: string;
}

export interface StudentSummary {
  id: number;
  email: string;
  name: string;
  role: string;
  sessions: number;
  objectives_passed: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `API error ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  me: () => request<{ id: number; email: string; name: string; role: string }>('/api/v1/auth/me'),
  listLabs: () => request<Lab[]>('/api/v1/labs'),
  getLab: (slug: string) => request<Lab>(`/api/v1/labs/${slug}`),
  deployLab: (labSlug: string, ttlSeconds?: number) =>
    request<Session>('/api/v1/labs', {
      method: 'POST',
      body: JSON.stringify({ lab_slug: labSlug, ttl_seconds: ttlSeconds }),
    }),
  listSessions: () => request<Session[]>('/api/v1/labs/sessions'),
  getSession: (id: string) => request<Session>(`/api/v1/labs/sessions/${id}`),
  destroySession: (id: string) =>
    request<Session>(`/api/v1/labs/sessions/${id}/destroy`, { method: 'POST' }),
  resetSession: (id: string) =>
    request<Session>(`/api/v1/labs/sessions/${id}/reset`, { method: 'POST' }),
  snapshotSession: (id: string) =>
    request<{ session_id: string; configs: Record<string, string> }>(
      `/api/v1/labs/sessions/${id}/snapshot`,
      { method: 'POST' },
    ),
  gradeSession: (id: string) =>
    request<{ session_id: string; score: number; total: number; results: GradeResult[] }>(
      `/api/v1/labs/sessions/${id}/grade`,
      { method: 'POST' },
    ),
  sessionResults: (id: string) =>
    request<{
      session_id: string;
      progress: { objective_id: string; status: string; detail: string }[];
      grades: { score: number; total: number }[];
    }>(`/api/v1/labs/sessions/${id}/results`),
  consoleInfo: (sessionId: string, node: string) =>
    request<{
      session_id: string;
      node: string;
      driver: string;
      console_method: string;
      websocket_url: string;
      container: string;
      command: string[];
    }>(`/api/v1/labs/sessions/${sessionId}/nodes/${node}/console-info`),
  listImages: () =>
    request<
      { id: number; name: string; vendor: string; image_ref: string; sha256: string; loaded: boolean }[]
    >('/api/v1/images'),
  instructorStudents: () => request<StudentSummary[]>('/api/v1/instructor/students'),
  instructorLabProgress: (slug: string) =>
    request<
      { user_id: number; objective_id: string; status: string; detail: string }[]
    >(`/api/v1/instructor/labs/${slug}/progress`),
};
