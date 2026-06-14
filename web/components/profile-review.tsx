'use client';

import { useState } from 'react';
import { STEPS } from '@/components/preferences-chat';
import type {
  ExtractedProfile,
  Preferences,
  Publication,
  ResearchExperience,
  SubmitProfilePayload,
  WorkExperience,
} from '@/lib/types';

interface ProfileReviewProps {
  sessionId: string;
  initialProfile: ExtractedProfile;
  initialPreferences: Preferences;
  onSubmit: (payload: SubmitProfilePayload) => Promise<void>;
  submitting: boolean;
  submitError?: string;
}

const inputClass =
  'w-full rounded-lg border border-zinc-300 dark:border-zinc-600 bg-transparent px-3 py-2 text-sm text-zinc-800 dark:text-zinc-200 focus:outline-none focus:border-zinc-500 dark:focus:border-zinc-400';

const labelClass = 'block text-xs text-zinc-400 dark:text-zinc-500 mb-1';

const cardClass =
  'rounded-xl border border-zinc-200 dark:border-zinc-700 p-6 animate-fade-in';

const removeLinkClass =
  'text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 underline underline-offset-2 transition-colors';

const addLinkClass =
  'text-sm text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 underline underline-offset-2 transition-colors';

function numOrNull(value: string): number | null {
  if (value.trim() === '') return null;
  const n = Number(value);
  return Number.isNaN(n) ? null : n;
}

export default function ProfileReview({
  sessionId,
  initialProfile,
  initialPreferences,
  onSubmit,
  submitting,
  submitError,
}: ProfileReviewProps) {
  const [profile, setProfile] = useState<ExtractedProfile>(initialProfile);
  const [preferences, setPreferences] = useState<Preferences>(initialPreferences);
  const [targetDegreesText, setTargetDegreesText] = useState(
    initialProfile.target_degrees.join(', '),
  );

  function updateField<K extends keyof ExtractedProfile>(key: K, value: ExtractedProfile[K]) {
    setProfile((prev) => ({ ...prev, [key]: value }));
  }

  function updateWorkExperience(index: number, field: keyof WorkExperience, value: string) {
    setProfile((prev) => ({
      ...prev,
      work_experiences: prev.work_experiences.map((item, i) =>
        i === index ? { ...item, [field]: value } : item,
      ),
    }));
  }

  function updateResearchExperience(index: number, field: keyof ResearchExperience, value: string) {
    setProfile((prev) => ({
      ...prev,
      research_experiences: prev.research_experiences.map((item, i) =>
        i === index ? { ...item, [field]: value } : item,
      ),
    }));
  }

  function updatePublication(index: number, field: keyof Publication, value: string) {
    setProfile((prev) => ({
      ...prev,
      publications: prev.publications.map((item, i) =>
        i === index ? { ...item, [field]: value } : item,
      ),
    }));
  }

  function togglePreference(stepId: string, opt: string, type: 'single' | 'multi') {
    setPreferences((prev) => {
      if (type === 'single') {
        return { ...prev, [stepId]: opt };
      }
      const current = (prev[stepId] as string[] | undefined) ?? [];
      const next = current.includes(opt)
        ? current.filter((o) => o !== opt)
        : [...current, opt];
      return { ...prev, [stepId]: next };
    });
  }

  function handleSubmit() {
    const payload: SubmitProfilePayload = {
      ...profile,
      session_id: sessionId,
      target_degrees: targetDegreesText
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      preferences,
    };
    void onSubmit(payload);
  }

  return (
    <div className='flex flex-col gap-6'>
      {/* Your details */}
      <div className={cardClass}>
        <h3 className='text-sm font-medium text-zinc-800 dark:text-zinc-200 mb-4'>
          Your details
        </h3>
        <div className='grid grid-cols-1 sm:grid-cols-2 gap-4'>
          <div>
            <label className={labelClass}>Name</label>
            <input
              className={inputClass}
              type='text'
              value={profile.name ?? ''}
              onChange={(e) => updateField('name', e.target.value || null)}
            />
          </div>
          <div>
            <label className={labelClass}>School / Ranking</label>
            <input
              className={inputClass}
              type='text'
              value={profile.gpa_ranking ?? ''}
              onChange={(e) => updateField('gpa_ranking', e.target.value || null)}
            />
          </div>
          <div>
            <label className={labelClass}>GPA</label>
            <input
              className={inputClass}
              type='number'
              step='any'
              value={profile.gpa ?? ''}
              onChange={(e) => updateField('gpa', numOrNull(e.target.value))}
            />
          </div>
          <div>
            <label className={labelClass}>GPA Scale</label>
            <input
              className={inputClass}
              type='number'
              step='any'
              value={profile.gpa_base ?? ''}
              onChange={(e) => updateField('gpa_base', numOrNull(e.target.value))}
            />
          </div>
          <div>
            <label className={labelClass}>TOEFL (0–120)</label>
            <input
              className={inputClass}
              type='number'
              step='any'
              value={profile.toefl_scale_120 ?? ''}
              onChange={(e) => updateField('toefl_scale_120', numOrNull(e.target.value))}
            />
          </div>
          <div>
            <label className={labelClass}>TOEFL (0–6)</label>
            <input
              className={inputClass}
              type='number'
              step='any'
              value={profile.toefl_scale_6 ?? ''}
              onChange={(e) => updateField('toefl_scale_6', numOrNull(e.target.value))}
            />
          </div>
          <div>
            <label className={labelClass}>IELTS</label>
            <input
              className={inputClass}
              type='number'
              step='any'
              value={profile.ielts ?? ''}
              onChange={(e) => updateField('ielts', numOrNull(e.target.value))}
            />
          </div>
          <div>
            <label className={labelClass}>Target degrees (comma-separated)</label>
            <input
              className={inputClass}
              type='text'
              value={targetDegreesText}
              onChange={(e) => setTargetDegreesText(e.target.value)}
              placeholder='MS, PhD'
            />
          </div>
        </div>
      </div>

      {/* Work experience */}
      <div className={cardClass}>
        <h3 className='text-sm font-medium text-zinc-800 dark:text-zinc-200 mb-4'>
          Work experience
        </h3>
        <div className='flex flex-col gap-4'>
          {profile.work_experiences.map((exp, i) => (
            <div
              key={i}
              className='rounded-lg border border-zinc-200 dark:border-zinc-700 p-4 flex flex-col gap-3'
            >
              <div className='grid grid-cols-1 sm:grid-cols-2 gap-3'>
                <div>
                  <label className={labelClass}>Company</label>
                  <input
                    className={inputClass}
                    type='text'
                    value={exp.company ?? ''}
                    onChange={(e) => updateWorkExperience(i, 'company', e.target.value)}
                  />
                </div>
                <div>
                  <label className={labelClass}>Title</label>
                  <input
                    className={inputClass}
                    type='text'
                    value={exp.title ?? ''}
                    onChange={(e) => updateWorkExperience(i, 'title', e.target.value)}
                  />
                </div>
                <div>
                  <label className={labelClass}>Start date</label>
                  <input
                    className={inputClass}
                    type='text'
                    value={exp.start_date ?? ''}
                    onChange={(e) => updateWorkExperience(i, 'start_date', e.target.value)}
                  />
                </div>
                <div>
                  <label className={labelClass}>End date</label>
                  <input
                    className={inputClass}
                    type='text'
                    value={exp.end_date ?? ''}
                    onChange={(e) => updateWorkExperience(i, 'end_date', e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label className={labelClass}>Description</label>
                <textarea
                  className={`${inputClass} resize-none`}
                  rows={2}
                  value={exp.description ?? ''}
                  onChange={(e) => updateWorkExperience(i, 'description', e.target.value)}
                />
              </div>
              <button
                onClick={() =>
                  setProfile((prev) => ({
                    ...prev,
                    work_experiences: prev.work_experiences.filter((_, idx) => idx !== i),
                  }))
                }
                className={`${removeLinkClass} self-start`}
              >
                Remove
              </button>
            </div>
          ))}
          <button
            onClick={() =>
              setProfile((prev) => ({
                ...prev,
                work_experiences: [
                  ...prev.work_experiences,
                  { company: '', title: '', start_date: '', end_date: '', description: '' },
                ],
              }))
            }
            className={`${addLinkClass} self-start`}
          >
            + Add work experience
          </button>
        </div>
      </div>

      {/* Research experience */}
      <div className={cardClass}>
        <h3 className='text-sm font-medium text-zinc-800 dark:text-zinc-200 mb-4'>
          Research experience
        </h3>
        <div className='flex flex-col gap-4'>
          {profile.research_experiences.map((exp, i) => (
            <div
              key={i}
              className='rounded-lg border border-zinc-200 dark:border-zinc-700 p-4 flex flex-col gap-3'
            >
              <div className='grid grid-cols-1 sm:grid-cols-2 gap-3'>
                <div>
                  <label className={labelClass}>Institution</label>
                  <input
                    className={inputClass}
                    type='text'
                    value={exp.institution ?? ''}
                    onChange={(e) => updateResearchExperience(i, 'institution', e.target.value)}
                  />
                </div>
                <div>
                  <label className={labelClass}>Title</label>
                  <input
                    className={inputClass}
                    type='text'
                    value={exp.title ?? ''}
                    onChange={(e) => updateResearchExperience(i, 'title', e.target.value)}
                  />
                </div>
                <div>
                  <label className={labelClass}>Start date</label>
                  <input
                    className={inputClass}
                    type='text'
                    value={exp.start_date ?? ''}
                    onChange={(e) => updateResearchExperience(i, 'start_date', e.target.value)}
                  />
                </div>
                <div>
                  <label className={labelClass}>End date</label>
                  <input
                    className={inputClass}
                    type='text'
                    value={exp.end_date ?? ''}
                    onChange={(e) => updateResearchExperience(i, 'end_date', e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label className={labelClass}>Description</label>
                <textarea
                  className={`${inputClass} resize-none`}
                  rows={2}
                  value={exp.description ?? ''}
                  onChange={(e) => updateResearchExperience(i, 'description', e.target.value)}
                />
              </div>
              <button
                onClick={() =>
                  setProfile((prev) => ({
                    ...prev,
                    research_experiences: prev.research_experiences.filter((_, idx) => idx !== i),
                  }))
                }
                className={`${removeLinkClass} self-start`}
              >
                Remove
              </button>
            </div>
          ))}
          <button
            onClick={() =>
              setProfile((prev) => ({
                ...prev,
                research_experiences: [
                  ...prev.research_experiences,
                  { institution: '', title: '', start_date: '', end_date: '', description: '' },
                ],
              }))
            }
            className={`${addLinkClass} self-start`}
          >
            + Add research experience
          </button>
        </div>
      </div>

      {/* Publications */}
      <div className={cardClass}>
        <h3 className='text-sm font-medium text-zinc-800 dark:text-zinc-200 mb-4'>
          Publications
        </h3>
        <div className='flex flex-col gap-4'>
          {profile.publications.map((pub, i) => (
            <div
              key={i}
              className='rounded-lg border border-zinc-200 dark:border-zinc-700 p-4 flex flex-col gap-3'
            >
              <div className='grid grid-cols-1 sm:grid-cols-2 gap-3'>
                <div>
                  <label className={labelClass}>Title</label>
                  <input
                    className={inputClass}
                    type='text'
                    value={pub.title ?? ''}
                    onChange={(e) => updatePublication(i, 'title', e.target.value)}
                  />
                </div>
                <div>
                  <label className={labelClass}>Venue</label>
                  <input
                    className={inputClass}
                    type='text'
                    value={pub.venue ?? ''}
                    onChange={(e) => updatePublication(i, 'venue', e.target.value)}
                  />
                </div>
                <div>
                  <label className={labelClass}>Year</label>
                  <input
                    className={inputClass}
                    type='text'
                    value={pub.year ?? ''}
                    onChange={(e) => updatePublication(i, 'year', e.target.value)}
                  />
                </div>
                <div>
                  <label className={labelClass}>Authors</label>
                  <input
                    className={inputClass}
                    type='text'
                    value={pub.authors ?? ''}
                    onChange={(e) => updatePublication(i, 'authors', e.target.value)}
                  />
                </div>
              </div>
              <button
                onClick={() =>
                  setProfile((prev) => ({
                    ...prev,
                    publications: prev.publications.filter((_, idx) => idx !== i),
                  }))
                }
                className={`${removeLinkClass} self-start`}
              >
                Remove
              </button>
            </div>
          ))}
          <button
            onClick={() =>
              setProfile((prev) => ({
                ...prev,
                publications: [
                  ...prev.publications,
                  { title: '', venue: '', year: '', authors: '' },
                ],
              }))
            }
            className={`${addLinkClass} self-start`}
          >
            + Add publication
          </button>
        </div>
      </div>

      {/* Preferences */}
      <div className={cardClass}>
        <h3 className='text-sm font-medium text-zinc-800 dark:text-zinc-200 mb-4'>
          Your preferences
        </h3>
        <div className='flex flex-col gap-4'>
          {STEPS.map((step) => {
            const value = preferences[step.id];
            const selected = Array.isArray(value) ? value : value ? [value] : [];
            return (
              <div key={step.id}>
                <label className={labelClass}>{step.question}</label>
                <div className='flex flex-wrap gap-2'>
                  {step.options.map((opt) => (
                    <button
                      key={opt}
                      onClick={() => togglePreference(step.id, opt, step.type)}
                      className={`rounded-full px-4 py-1.5 text-sm border transition-colors ${
                        selected.includes(opt)
                          ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 border-transparent'
                          : 'border-zinc-300 dark:border-zinc-600 text-zinc-700 dark:text-zinc-300 hover:border-zinc-400 dark:hover:border-zinc-500'
                      }`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {submitError && (
        <p className='text-sm text-red-500 dark:text-red-400'>{submitError}</p>
      )}

      <button
        onClick={handleSubmit}
        disabled={submitting}
        className='self-start rounded-lg px-5 py-2.5 text-sm font-medium bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 disabled:opacity-40 hover:opacity-80 transition-opacity'
      >
        {submitting ? 'Saving…' : 'Submit'}
      </button>
    </div>
  );
}
