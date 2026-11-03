/**
 * Graduate Compass — Shared Types
 *
 * Types shared between the API service layer (lib/api.ts) and the resume
 * upload / review flow (app/resume/page.tsx and its components).
 */

export interface WorkExperience {
  company: string | null;
  title: string | null;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
}

export interface ResearchExperience {
  institution: string | null;
  title: string | null;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
}

export interface Publication {
  title: string | null;
  venue: string | null;
  year: string | number | null;
  authors: string | null;
}

export interface ExtractedProfile {
  name: string | null;
  gpa: number | null;
  gpa_base: number | null;
  gpa_ranking: string | null;
  toefl_scale_6: number | null;
  toefl_scale_120: number | null;
  ielts: number | null;
  target_degrees: string[];
  work_experiences: WorkExperience[];
  research_experiences: ResearchExperience[];
  publications: Publication[];
}

export type Preferences = Record<string, string | string[]>;

export interface SubmitProfilePayload extends ExtractedProfile {
  session_id: string;
  preferences: Preferences;
}

/** A ranked recommendation, including evidence and a practical next step. */
export interface ProgramMatchResult {
  rank: number;
  program_id: string;
  name: string;
  university: string;
  country: string;
  fit_score: number;
  why_match: string;
  strengths: string[];
  gaps: string[];
  uncertainties: string[];
  next_action: string;
  official_website: string | null;
}

/** Fields used by the results screen from the versioned backend SSE events. */
export interface MatchStreamEvent {
  type: string;
  message?: string;
  stage?: string;
  code?: string;
  processed?: number;
  total?: number;
  result?: ProgramMatchResult;
  results?: ProgramMatchResult[];
  disclaimer?: string;
  retryable?: boolean;
  run_id: string;
  sequence: number;
}
