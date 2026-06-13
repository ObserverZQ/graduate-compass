'use client';

import { useEffect, useRef, useState } from 'react';
import { uploadResume, ApiError } from '@/lib/api';

type UploadState =
  | { status: 'idle' }
  | { status: 'uploading' }
  | { status: 'success'; extractedText: string; sessionId: string }
  | { status: 'error'; message: string };

interface FileUploadProps {
  onSuccess: (extractedText: string, sessionId: string) => void;
}

export default function FileUpload({ onSuccess }: FileUploadProps) {
  const [state, setState] = useState<UploadState>({ status: 'idle' });
  const [dragOver, setDragOver] = useState(false);
  // Restore the session_id from a previous upload so a re-upload updates the
  // same user_profiles row instead of creating a new one.
  const [sessionId, setSessionId] = useState<string | null>(() =>
    typeof window === 'undefined'
      ? null
      : localStorage.getItem('gradcompass_session_id'),
  );
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (state.status === 'success') {
      onSuccess(state.extractedText, state.sessionId);
    }
  }, [state, onSuccess]);

  async function handleFile(file: File) {
    if (!file) return;
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['pdf', 'doc', 'docx'].includes(ext ?? '')) {
      setState({
        status: 'error',
        message: 'Please upload a PDF, DOC, or DOCX file.',
      });
      return;
    }
    setState({ status: 'uploading' });
    try {
      const result = await uploadResume(file, sessionId);
      setSessionId(result.session_id);
      setState({
        status: 'success',
        extractedText: result.extracted_text,
        sessionId: result.session_id,
      });
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Upload failed (${err.status}): ${err.message}`
          : 'Something went wrong. Please try again.';
      setState({ status: 'error', message: msg });
    }
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  if (state.status === 'success') {
    return (
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
        <p className='text-sm font-medium text-zinc-800 dark:text-zinc-200 mb-1'>
          Resume uploaded
        </p>
        <p className='text-xs text-zinc-400 dark:text-zinc-500 line-clamp-2 mb-4 max-w-sm mx-auto'>
          {state.extractedText.slice(0, 200)}…
        </p>
        <button
          onClick={() => {
            setState({ status: 'idle' });
            if (inputRef.current) inputRef.current.value = '';
          }}
          className='text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 underline underline-offset-2 transition-colors'
        >
          Replace file
        </button>
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div className='rounded-xl border border-red-200 dark:border-red-900 p-8 text-center animate-fade-in'>
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
            className='text-red-400'
            aria-hidden='true'
          >
            <circle cx='12' cy='12' r='10' />
            <path d='m15 9-6 6M9 9l6 6' />
          </svg>
        </div>
        <p className='text-sm text-red-500 dark:text-red-400 mb-4'>
          {state.message}
        </p>
        <button
          onClick={() => setState({ status: 'idle' })}
          className='text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 underline underline-offset-2 transition-colors'
        >
          Try again
        </button>
      </div>
    );
  }

  if (state.status === 'uploading') {
    return (
      <div className='rounded-xl border-2 border-dashed border-zinc-200 dark:border-zinc-700 p-12 text-center'>
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
            className='text-zinc-400 animate-spin'
            aria-hidden='true'
          >
            <path d='M21 12a9 9 0 1 1-6.219-8.56' />
          </svg>
        </div>
        <p className='text-sm text-zinc-500 dark:text-zinc-400'>
          Uploading and analyzing…
        </p>
      </div>
    );
  }

  return (
    <div
      role='button'
      tabIndex={0}
      aria-label='Upload resume — click or drag and drop'
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      className={`rounded-xl border-2 border-dashed p-12 text-center cursor-pointer transition-colors select-none ${
        dragOver
          ? 'border-zinc-500 bg-zinc-50 dark:border-zinc-400 dark:bg-zinc-900'
          : 'border-zinc-300 dark:border-zinc-700 hover:border-zinc-400 dark:hover:border-zinc-500'
      }`}
    >
      <input
        ref={inputRef}
        type='file'
        accept='.pdf,.doc,.docx'
        onChange={onInputChange}
        className='hidden'
        aria-hidden='true'
      />
      <div className='flex justify-center mb-3'>
        <svg
          xmlns='http://www.w3.org/2000/svg'
          width='28'
          height='28'
          viewBox='0 0 24 24'
          fill='none'
          stroke='currentColor'
          strokeWidth='1.5'
          strokeLinecap='round'
          strokeLinejoin='round'
          className='text-zinc-300 dark:text-zinc-600'
          aria-hidden='true'
        >
          <path d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4' />
          <polyline points='17 8 12 3 7 8' />
          <line x1='12' x2='12' y1='3' y2='15' />
        </svg>
      </div>
      <p className='text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1'>
        Upload your resume
      </p>
      <p className='text-xs text-zinc-400 dark:text-zinc-500'>
        PDF, DOC, or DOCX · drag &amp; drop or click
      </p>
    </div>
  );
}
