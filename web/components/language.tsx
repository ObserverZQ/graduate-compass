"use client";

import { useLanguage } from "@/context/language-context";

export default function LanguageToggle() {
  const { lang, toggleLang } = useLanguage();

  return (
    <div className="flex rounded-lg border border-zinc-200 dark:border-zinc-700 overflow-hidden text-xs font-medium">
      <button
        onClick={lang === "zh" ? toggleLang : undefined}
        aria-pressed={lang === "en"}
        className={`px-2.5 py-1.5 transition-colors ${
          lang === "en"
            ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
            : "text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
        }`}
      >
        EN
      </button>
      <button
        onClick={lang === "en" ? toggleLang : undefined}
        aria-pressed={lang === "zh"}
        className={`px-2.5 py-1.5 transition-colors ${
          lang === "zh"
            ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
            : "text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
        }`}
      >
        中文
      </button>
    </div>
  );
}
