/**
 * Graduate Compass — API Service Layer
 *
 * Maps Next.js frontend calls to FastAPI backend routes.
 * Base URL is controlled by NEXT_PUBLIC_API_URL in .env.local.
 *
 * FastAPI source: apps/api/main.py
 */

import type { ExtractedProfile, SubmitProfilePayload } from './types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, text);
  }
  return res.json() as Promise<T>;
}

// ─── Resume ──────────────────────────────────────────────────────────────────

/**
 * POST /profile/upload-resume
 * Upload a resume file (PDF, DOC, DOCX).
 * Fast path: extracts plain text and stores the file, but does not run the
 * LLM analysis (see analyzeResume).
 */
export async function uploadResume(
  file: File,
  sessionId?: string | null,
): Promise<{ extracted_text: string; session_id: string; resume_file_url: string }> {
  const form = new FormData();
  form.append('file', file);
  if (sessionId) {
    form.append('session_id', sessionId);
  }
  const data = await request<{
    extracted_text: string;
    session_id: string;
    resume_file_url: string;
  }>('/profile/upload-resume', {
    method: 'POST',
    body: form,
  });

  // Store session_id in localStorage for future requests
  localStorage.setItem('gradcompass_session_id', data.session_id);

  return data;
}

/**
 * POST /profile/analyze-resume
 * Slow path: runs the LLM extraction over the resume text returned by
 * uploadResume() and persists the structured fields.
 */
export async function analyzeResume(
  sessionId: string,
  resumeRawText: string,
): Promise<ExtractedProfile> {
  return request<ExtractedProfile>('/profile/analyze-resume', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      resume_raw_text: resumeRawText,
    }),
  });
}

/**
 * POST /profile/preferences
 * Final submit — persists the user's preferences plus any edits they made
 * to the extracted resume fields on the review screen.
 */
export async function submitProfile(
  payload: SubmitProfilePayload,
): Promise<{ session_id: string; status: string }> {
  return request<{ session_id: string; status: string }>('/profile/preferences', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

// ─── Health ───────────────────────────────────────────────────────────────────

/**
 * GET /health
 * Check API and database connectivity.
 */
export async function checkHealth(): Promise<{ status: string; db: string }> {
  return request<{ status: string; db: string }>('/health');
}

// ─── Stubs (not yet implemented) ─────────────────────────────────────────────

/**
 * GET /programs/match  (TODO)
 * Return ranked graduate programs based on resume + preferences.
 */
// export async function matchPrograms(): Promise<unknown[]> { ... }
