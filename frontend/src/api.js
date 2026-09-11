// Single source of truth for where the backend lives.
//
// Vite inlines import.meta.env at build time, so the bundle Vercel ships points
// at the deployed API while a plain `npm run dev` still falls back to the local
// uvicorn - no .env needed to work on a fresh clone.
export const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export const API = `${API_BASE}/api/v1`;
