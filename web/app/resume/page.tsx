'use client';

import { useEffect, useState } from 'react';
import FileUpload from '@/components/file-upload';
import PreferencesChat from '@/components/preferences-chat';
import ProfileReview from '@/components/profile-review';
import SpinnerCard from '@/components/spinner-card';
import { ApiError, analyzeResume, submitProfile } from '@/lib/api';
import type { ExtractedProfile, Preferences, SubmitProfilePayload } from '@/lib/types';

type AnalysisState =
  | { status: 'pending' }
  | { status: 'done'; profile: ExtractedProfile }
  | { status: 'error'; message: string };

type FlowState =
  | { phase: 'idle' }
  | {
      phase: 'preferences';
      sessionId: string;
      extractedText: string;
      resumeFileUrl: string;
    }
  | {
      phase: 'review';
      sessionId: string;
      extractedText: string;
      resumeFileUrl: string;
      preferences: Preferences;
    }
  | { phase: 'submitted'; sessionId: string };

function errorMessage(err: unknown): string {
  return err instanceof ApiError
    ? `Request failed (${err.status}): ${err.message}`
    : 'Something went wrong. Please try again.';
}

export default function ResumePage() {
  const [flow, setFlow] = useState<FlowState>({ phase: 'idle' });
  const [analysis, setAnalysis] = useState<AnalysisState>({ status: 'pending' });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | undefined>();

  // Kick off resume analysis in the background as soon as upload finishes,
  // so it overlaps with the time the user spends on the preferences chat.
  useEffect(() => {
    if (flow.phase !== 'preferences') return;
    analyzeResume(flow.sessionId, flow.extractedText)
      .then((profile) => setAnalysis({ status: 'done', profile }))
      .catch((err) => setAnalysis({ status: 'error', message: errorMessage(err) }));
  }, [flow]);

  function retryAnalysis() {
    if (flow.phase !== 'preferences' && flow.phase !== 'review') return;
    setAnalysis({ status: 'pending' });
    analyzeResume(flow.sessionId, flow.extractedText)
      .then((profile) => setAnalysis({ status: 'done', profile }))
      .catch((err) => setAnalysis({ status: 'error', message: errorMessage(err) }));
  }

  function handlePreferencesComplete(prefs: Preferences) {
    if (flow.phase !== 'preferences') return;
    setFlow({
      phase: 'review',
      sessionId: flow.sessionId,
      extractedText: flow.extractedText,
      resumeFileUrl: flow.resumeFileUrl,
      preferences: prefs,
    });
  }

  async function handleSubmit(payload: SubmitProfilePayload) {
    setSubmitting(true);
    setSubmitError(undefined);
    try {
      await submitProfile(payload);
      setFlow({ phase: 'submitted', sessionId: payload.session_id });
    } catch (err) {
      setSubmitError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className='flex-1 max-w-2xl mx-auto w-full px-6 py-16 flex flex-col gap-16'>
      <section>
        <h1 className='text-2xl font-semibold mb-2 text-zinc-900 dark:text-zinc-100'>
          Upload your resume
        </h1>
        <p className='text-sm text-zinc-500 dark:text-zinc-400 mb-8'>
          We&apos;ll read your profile to help match graduate programs.
        </p>

        {flow.phase === 'idle' && (
          <FileUpload
            onSuccess={(extractedText, sessionId, resumeFileUrl) =>
              setFlow({ phase: 'preferences', sessionId, extractedText, resumeFileUrl })
            }
          />
        )}

        {flow.phase !== 'idle' && (
          <div className='rounded-xl border border-zinc-200 dark:border-zinc-700 p-8 text-center animate-fade-in'>
            <div className='flex justify-center mb-3'>
              <svg
                xmlns='http://www.w3.org/2000/svg'
                width='24'
                height='24'
                viewBox='0 0 24 24'
                fill='none'
                stroke='currentColor'
                strokeWidth='2'
                strokeLinecap='round'
                strokeLinejoin='round'
                className='text-green-500'
                aria-hidden='true'
              >
                <path d='M22 11.08V12a10 10 0 1 1-5.93-9.14' />
                <path d='m9 11 3 3L22 4' />
              </svg>
            </div>
            <p className='text-sm font-medium text-zinc-800 dark:text-zinc-200'>
              Resume uploaded
            </p>
          </div>
        )}
      </section>

      {flow.phase === 'preferences' && (
        <section className='animate-fade-in'>
          <h2 className='text-xl font-semibold mb-2 text-zinc-900 dark:text-zinc-100'>
            Tell us your preferences
          </h2>
          <p className='text-sm text-zinc-500 dark:text-zinc-400 mb-6'>
            All questions are optional — skip anything that doesn&apos;t apply.
          </p>
          <PreferencesChat
            resumeText={flow.extractedText}
            onComplete={handlePreferencesComplete}
          />
          {analysis.status === 'error' && (
            <p className='mt-4 text-sm text-red-500 dark:text-red-400'>
              {analysis.message}{' '}
              <button
                onClick={retryAnalysis}
                className='underline underline-offset-2 hover:text-red-600 dark:hover:text-red-300'
              >
                Retry analysis
              </button>
            </p>
          )}
        </section>
      )}

      {flow.phase === 'review' && (
        <section className='animate-fade-in'>
          {analysis.status === 'done' && (
            <>
              <h2 className='text-xl font-semibold mb-2 text-zinc-900 dark:text-zinc-100'>
                Review your profile
              </h2>
              <p className='text-sm text-zinc-500 dark:text-zinc-400 mb-6'>
                Double-check what we found and your preferences before submitting.
              </p>
              <ProfileReview
                sessionId={flow.sessionId}
                initialProfile={analysis.profile}
                initialPreferences={flow.preferences}
                onSubmit={handleSubmit}
                submitting={submitting}
                submitError={submitError}
              />
            </>
          )}

          {analysis.status === 'pending' && <SpinnerCard label='Analyzing your resume…' />}

          {analysis.status === 'error' && (
            <p className='text-sm text-red-500 dark:text-red-400'>
              {analysis.message}{' '}
              <button
                onClick={retryAnalysis}
                className='underline underline-offset-2 hover:text-red-600 dark:hover:text-red-300'
              >
                Retry analysis
              </button>
            </p>
          )}
        </section>
      )}

      {flow.phase === 'submitted' && (
        <section className='animate-fade-in'>
          <h2 className='text-xl font-semibold mb-2 text-zinc-900 dark:text-zinc-100'>
            Profile saved!
          </h2>
          <p className='text-sm text-zinc-500 dark:text-zinc-400'>
            We&apos;ll use this to match you with graduate programs. (Program matching coming soon.)
          </p>
        </section>
      )}
    </main>
  );
}
