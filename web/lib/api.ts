/**
 * Graduate Compass — API Service Layer
 *
 * Maps Next.js frontend calls to FastAPI backend routes.
 * Base URL is controlled by NEXT_PUBLIC_API_URL in .env.local.
 *
 * FastAPI source: apps/api/main.py
 */

import type { ExtractedProfile, MatchStreamEvent, SubmitProfilePayload } from './types';

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
 * Upload a PDF resume.
 * Stores the PDF and returns validated LLM-extracted fields for review.
 */
export async function uploadResume(
  file: File,
  sessionId?: string | null,
): Promise<{ session_id: string; extracted_profile: ExtractedProfile }> {
  const form = new FormData();
  form.append('file', file);
  if (sessionId) {
    form.append('session_id', sessionId);
  }
  const data = await request<{
    session_id: string;
    extracted_profile: ExtractedProfile;
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
 * Optional retry path if extraction must be attempted again after upload.
 */
export async function analyzeResume(
  sessionId: string,
): Promise<ExtractedProfile> {
  return request<ExtractedProfile>('/profile/analyze-resume', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
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

/**
 * POST /match/stream reads SSE frames as they arrive. SSE comments keep the
 * connection open but are not user-facing progress events.
 */
export async function* streamMatches(
  sessionId: string,
  signal?: AbortSignal,
): AsyncGenerator<MatchStreamEvent> {
  const response = await fetch(`${BASE_URL}/match/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({ session_id: sessionId }),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new ApiError(response.status, 'Unable to start program matching.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finished = false;
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, '\n');
      let boundary = buffer.indexOf('\n\n');
      while (boundary !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const data = frame.split('\n')
          .filter((line) => line.startsWith('data: '))
          .map((line) => line.slice(6))
          .join('\n');
        if (data) {
          const event = JSON.parse(data) as MatchStreamEvent;
          yield event;
          if (event.type === 'complete' || event.type === 'error') {
            finished = true;
            return;
          }
        }
        boundary = buffer.indexOf('\n\n');
      }
      if (done) break;
    }
    if (!finished) throw new ApiError(502, 'Matching ended before results arrived.');
  } finally {
    await reader.cancel();
  }
}
