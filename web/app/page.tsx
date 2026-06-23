import Link from 'next/link';

export default function Home() {
  return (
    <div className='flex flex-col font-sans'>

      {/* Section 1 — Hero */}
      <section className='min-h-screen flex items-center justify-center px-6'>
        <div className='max-w-2xl flex flex-col gap-6 text-center'>
          <h1 className='text-5xl sm:text-6xl font-bold tracking-tight text-[#006994] dark:text-[#B9D9EB]'>
            Graduate Compass
          </h1>
          <p className='text-xl sm:text-2xl font-medium text-zinc-700 dark:text-zinc-300'>
            Your AI advisor for graduate school applications.
          </p>
          <p className='text-base text-zinc-600 dark:text-zinc-400 leading-relaxed'>
            Upload your resume. Our AI extracts your academic profile — GPA, research, publications, and experience.
            Then get matched to programs that actually fit who you are, not just where you went to school.
          </p>
          <div className='flex flex-row gap-4 justify-center mt-2'>
            <Link
              href='/resume'
              className='px-6 py-3 rounded-full bg-[#006994] dark:bg-[#B9D9EB] text-white dark:text-[#082f49] font-semibold text-sm transition-opacity hover:opacity-90'
            >
              Get Started
            </Link>
            <div className='relative group'>
              <button
                disabled
                className='px-6 py-3 rounded-full border border-[#006994] dark:border-[#B9D9EB] text-[#006994] dark:text-[#B9D9EB] font-semibold text-sm cursor-not-allowed opacity-50'
              >
                Explore Programs
              </button>
              <span className='absolute -top-9 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-gray-800 dark:bg-gray-200 px-2 py-1 text-xs text-white dark:text-gray-800 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none'>
                Coming soon
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2 — Why us */}
      <section className='min-h-screen flex items-center justify-center px-6 bg-white/40 dark:bg-[#006994]/20'>
        <div className='max-w-2xl flex flex-col gap-10 text-center sm:text-left'>
          <h2 className='text-3xl sm:text-4xl font-bold tracking-tight text-[#006994] dark:text-[#B9D9EB]'>
            Skip the $5,000 agency.<br />Keep the edge.
          </h2>
          <ul className='flex flex-col gap-6'>
            {[
              {
                label: 'Fraction of the cost',
                desc: "Traditional agencies charge $3,000–$10,000 per cycle. We don’t.",
              },
              {
                label: 'Built on your actual profile',
                desc: 'AI reads your resume and real experience — not a generic checklist.',
              },
              {
                label: 'Always on',
                desc: 'Instant feedback, no appointments, no waiting weeks for a counselor.',
              },
              {
                label: 'Your data, your control',
                desc: 'Nothing sold or shared with third parties. Ever.',
              },
            ].map(({ label, desc }) => (
              <li key={label} className='flex flex-col sm:flex-row gap-1 sm:gap-3'>
                <span className='font-semibold text-[#006994] dark:text-[#B9D9EB] min-w-max'>
                  {label} —
                </span>
                <span className='text-zinc-600 dark:text-zinc-400'>{desc}</span>
              </li>
            ))}
          </ul>
          <Link
            href='/resume'
            className='self-center sm:self-start px-6 py-3 rounded-full bg-[#006994] dark:bg-[#B9D9EB] text-white dark:text-[#082f49] font-semibold text-sm transition-opacity hover:opacity-90'
          >
            Get Started Free
          </Link>
        </div>
      </section>

    </div>
  );
}
