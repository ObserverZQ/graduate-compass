'use client';

import { useEffect, useRef, useState } from 'react';
import type { Preferences } from '@/lib/types';

export const STEPS = [
  {
    id: 'locations',
    question: 'Where would you like to study? You can pick multiple.',
    type: 'multi' as const,
    options: ['USA', 'Europe', 'Singapore', 'Australia', 'Canada', 'Other'],
  },
  {
    id: 'climate',
    question: 'What kind of climate do you prefer?',
    type: 'single' as const,
    options: ['Warm', 'Cold', 'Mild', 'No preference'],
  },
  {
    id: 'budget',
    question: "What's your annual tuition budget?",
    type: 'single' as const,
    options: ['< $20k / yr', '$20–40k / yr', '$40k+ / yr', 'No limit'],
  },
  {
    id: 'careerGoal',
    question: "What's your primary goal after graduation?",
    type: 'single' as const,
    options: ['PhD / research', 'Industry job', 'Not sure yet'],
  },
];

type Message =
  | { role: 'assistant'; text: string }
  | { role: 'user'; text: string };

interface PreferencesChatProps {
  resumeText: string;
  onComplete: (preferences: Preferences) => void;
}

export default function PreferencesChat({
  resumeText: _resumeText,
  onComplete,
}: PreferencesChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', text: STEPS[0].question },
  ]);
  const [currentStep, setCurrentStep] = useState(0);
  const [selections, setSelections] = useState<string[]>([]);
  const [preferences, setPreferences] = useState<Preferences>({});
  const [done, setDone] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  function toggleOption(opt: string) {
    const step = STEPS[currentStep];
    if (step.type === 'single') {
      setSelections([opt]);
    } else {
      setSelections((prev) =>
        prev.includes(opt) ? prev.filter((s) => s !== opt) : [...prev, opt],
      );
    }
  }

  function advance(skipped: boolean) {
    const step = STEPS[currentStep];
    const answer = skipped ? 'Skipped' : selections.join(', ');
    const newPrefs = skipped
      ? preferences
      : {
          ...preferences,
          [step.id]: step.type === 'multi' ? selections : selections[0],
        };

    setPreferences(newPrefs);
    setMessages((prev) => [...prev, { role: 'user', text: answer }]);
    setSelections([]);

    const nextStep = currentStep + 1;
    if (nextStep < STEPS.length) {
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', text: STEPS[nextStep].question },
        ]);
        setCurrentStep(nextStep);
      }, 220);
    } else {
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', text: buildSummary(newPrefs) },
        ]);
        setDone(true);
        setTimeout(() => onComplete(newPrefs), 220);
      }, 220);
    }
  }

  function skipAll() {
    setDone(true);
    onComplete({});
  }

  function buildSummary(prefs: Record<string, string | string[]>) {
    const lines = STEPS.map((s) => {
      const val = prefs[s.id];
      if (!val) return null;
      const display = `${s.id}: ${Array.isArray(val) ? val.join(', ') : val}`;
      return `• ${display}`;
    }).filter(Boolean);

    if (lines.length === 0) {
      return "No preferences selected — we'll show you the full list of programs. Good luck!";
    }
    return `Here's what I've got:\n${lines.join('\n')}\n\nWe'll use this to match you with the best programs.`;
  }

  const step = STEPS[currentStep];
  const canConfirm = selections.length > 0;

  return (
    <div className='flex flex-col gap-4'>
      {/* Message history */}
      <div className='flex flex-col gap-3'>
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex animate-fade-in ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`rounded-2xl px-4 py-3 text-sm max-w-prose whitespace-pre-line ${
                msg.role === 'assistant'
                  ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 rounded-tl-sm'
                  : 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 rounded-tr-sm'
              }`}
            >
              {msg.text}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Current step input */}
      {!done && (
        <div className='animate-fade-in'>
          {/* Option chips */}
          <div className='flex flex-wrap gap-2 mb-4'>
            {step.options.map((opt) => (
              <button
                key={opt}
                onClick={() => toggleOption(opt)}
                className={`rounded-full px-4 py-1.5 text-sm border transition-colors ${
                  selections.includes(opt)
                    ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 border-transparent'
                    : 'border-zinc-300 dark:border-zinc-600 text-zinc-700 dark:text-zinc-300 hover:border-zinc-400 dark:hover:border-zinc-500'
                }`}
              >
                {opt}
              </button>
            ))}
          </div>

          {/* Actions */}
          <div className='flex items-center gap-4'>
            <button
              onClick={() => advance(false)}
              disabled={!canConfirm}
              className='rounded-lg px-4 py-2 text-sm font-medium bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 disabled:opacity-30 hover:opacity-80 transition-opacity'
            >
              Confirm
            </button>
            <button
              onClick={() => advance(true)}
              className='text-sm text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors'
            >
              Skip →
            </button>
            {currentStep === 0 && (
              <button
                onClick={skipAll}
                className='text-sm text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors ml-auto underline underline-offset-2'
              >
                Skip preferences →
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
