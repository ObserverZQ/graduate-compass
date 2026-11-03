/** Show the third API call's progress and explained program results. */
'use client';

import { useEffect, useState } from 'react';
import { streamMatches } from '@/lib/api';
import type { ProgramMatchResult } from '@/lib/types';

interface MatchResultsProps {
  sessionId: string;
}

export default function MatchResults({ sessionId }: MatchResultsProps) {
  const [attempt, setAttempt] = useState(0);

  // A new keyed run gets fresh state; the prior stream is aborted on unmount.
  return (
    <MatchResultsRun
      key={`${sessionId}:${attempt}`}
      sessionId={sessionId}
      onRetry={() => setAttempt((current) => current + 1)}
    />
  );
}

function MatchResultsRun({ sessionId, onRetry }: MatchResultsProps & { onRetry: () => void }) {
  const [message, setMessage] = useState('Starting your program review…');
  const [progress, setProgress] = useState<string>();
  const [warning, setWarning] = useState<string>();
  const [results, setResults] = useState<ProgramMatchResult[]>([]);
  const [disclaimer, setDisclaimer] = useState<string>();
  const [status, setStatus] = useState<'running' | 'complete' | 'error'>('running');
  const [canRetry, setCanRetry] = useState(false);
  useEffect(() => {
    const controller = new AbortController();

    async function run() {
      try {
        for await (const event of streamMatches(sessionId, controller.signal)) {
          if (event.message) setMessage(event.message);
          if (event.type === 'stage_started') setProgress(undefined);
          if (event.type === 'stage_progress' && event.total !== undefined) {
            setProgress(`${event.processed} of ${event.total} programs reviewed`);
          }
          if (event.type === 'warning' && event.message) {
            setWarning(event.message);
          }
          if (event.type === 'candidate_explained' && event.result) {
            const incoming = event.result;
            setResults((current) => {
              const withoutDuplicate = current.filter(
                (item) => item.program_id !== incoming.program_id,
              );
              return [...withoutDuplicate, incoming].sort((a, b) => a.rank - b.rank);
            });
          }
          if (event.type === 'complete') {
            setResults(event.results ?? []);
            setDisclaimer(event.disclaimer);
            setProgress(undefined);
            setStatus('complete');
          }
          if (event.type === 'error') {
            setProgress(undefined);
            setCanRetry(event.retryable ?? false);
            setStatus('error');
          }
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        setMessage(error instanceof Error ? error.message : 'Matching failed. Please try again.');
        setCanRetry(true);
        setStatus('error');
      }
    }
    void run();
    return () => controller.abort();
  }, [sessionId]);

  return (
    <section className='flex flex-col gap-6' aria-live='polite'>
      <div className='rounded-xl border border-zinc-200 dark:border-zinc-700 p-6'>
        <h2 className='text-xl font-semibold text-zinc-900 dark:text-zinc-100'>
          {status === 'complete' ? 'Your program matches' : 'Finding your matches'}
        </h2>
        <p className='mt-2 text-sm text-zinc-600 dark:text-zinc-300' role='status'>
          {message}
        </p>
        {status === 'running' && (
          <p className='mt-2 text-xs text-zinc-500'>
            {progress ?? 'Working through the available program information…'}
          </p>
        )}
        {warning && <p className='mt-2 text-sm text-amber-700 dark:text-amber-300'>{warning}</p>}
        {status === 'error' && canRetry && (
          <button
            type='button'
            onClick={onRetry}
            className='mt-4 text-sm underline underline-offset-2'
          >
            Try matching again
          </button>
        )}
      </div>

      {results.map((result) => (
        <article
          key={result.program_id}
          className='rounded-xl border border-zinc-200 dark:border-zinc-700 p-6'
        >
          <div className='flex items-start justify-between gap-4'>
            <div>
              <p className='text-xs text-zinc-500'>Match #{result.rank}</p>
              <h3 className='text-lg font-semibold text-zinc-900 dark:text-zinc-100'>
                {result.name}
              </h3>
              <p className='text-sm text-zinc-500'>{result.university} · {result.country}</p>
            </div>
            <p className='shrink-0 text-sm font-medium'>{result.fit_score}/100 fit</p>
          </div>
          <p className='mt-4 text-sm'>{result.why_match}</p>
          {result.strengths.length > 0 && <EvidenceList title='Strengths' items={result.strengths} />}
          {result.gaps.length > 0 && <EvidenceList title='Gaps' items={result.gaps} />}
          {result.uncertainties.length > 0 && <EvidenceList title='Uncertain information' items={result.uncertainties} />}
          <p className='mt-4 text-sm'><span className='font-medium'>Next step:</span> {result.next_action}</p>
          {result.official_website && (
            <a
              href={result.official_website}
              target='_blank'
              rel='noopener noreferrer'
              className='mt-3 inline-block text-sm underline underline-offset-2'
            >
              Official program page
            </a>
          )}
        </article>
      ))}
      {disclaimer && <p className='text-xs text-zinc-500'>{disclaimer}</p>}
    </section>
  );
}

function EvidenceList({ title, items }: { title: string; items: string[] }) {
  /** Keep detailed evidence scannable inside each recommendation card. */

  return (
    <div className='mt-4'>
      <h4 className='text-sm font-medium'>{title}</h4>
      <ul className='mt-1 list-disc pl-5 text-sm text-zinc-600 dark:text-zinc-300'>
        {items.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}
      </ul>
    </div>
  );
}
