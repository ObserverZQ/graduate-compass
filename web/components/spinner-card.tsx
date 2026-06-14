interface SpinnerCardProps {
  label: string;
}

export default function SpinnerCard({ label }: SpinnerCardProps) {
  return (
    <div className='rounded-xl border-2 border-dashed border-zinc-200 dark:border-zinc-700 p-12 text-center animate-fade-in'>
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
      <p className='text-sm text-zinc-500 dark:text-zinc-400'>{label}</p>
    </div>
  );
}
