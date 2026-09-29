/**
 * api.js — Centralised API client
 * All fetch() calls go through this module so that the base URL
 * can be changed in one place (e.g. when deploying to production).
 */

const API_BASE = "http://127.0.0.1:8000";

async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

// --- Jobs ---
const JobAPI = {
  list: ()           => apiFetch("/api/jobs"),
  get:  (id)         => apiFetch(`/api/jobs/${id}`),
  create: (data)     => apiFetch("/api/jobs",     { method: "POST", body: JSON.stringify(data) }),
  update: (id, data) => apiFetch(`/api/jobs/${id}`,{ method: "PUT",  body: JSON.stringify(data) }),
  close:  (id)       => apiFetch(`/api/jobs/${id}/close`, { method: "PATCH" }),
};

// --- Applications ---
const ApplicationAPI = {
  listByJob:    (jobId)        => apiFetch(`/api/applications?job_id=${jobId}`),
  updateStatus: (id, status)   => apiFetch(`/api/applications/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  }),
  getDetail:    (id)           => apiFetch(`/api/applications/${id}`),
  apply:        (formData)     => fetch(`${API_BASE}/api/applications/apply`, {
    method: "POST",
    body: formData,   // multipart — do NOT set Content-Type header manually
  }).then(r => r.json()),
};
