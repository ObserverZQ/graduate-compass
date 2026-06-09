import Link from "next/link";
import ContactButton from "./contact";
import LanguageToggle from "./language";
import ThemeToggle from "./theme";

export default function Topbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-sm">
      <nav className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
        <Link
          href="/"
          className="font-semibold text-sm tracking-tight text-zinc-900 dark:text-zinc-100 hover:opacity-75 transition-opacity"
        >
          Graduate Compass
        </Link>
        <div className="flex items-center gap-1">
          <ThemeToggle />
          <LanguageToggle />
          <ContactButton />
        </div>
      </nav>
    </header>
  );
}
