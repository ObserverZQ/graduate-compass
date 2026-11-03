"use client";

import { createContext, useContext, useSyncExternalStore } from "react";

export type Lang = "en" | "zh";

interface LanguageContextValue {
  lang: Lang;
  toggleLang: () => void;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);
const LANGUAGE_CHANGED = "graduate-compass-language-changed";

function subscribeToLanguage(onChange: () => void): () => void {
  window.addEventListener("storage", onChange);
  window.addEventListener(LANGUAGE_CHANGED, onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(LANGUAGE_CHANGED, onChange);
  };
}

function storedLanguage(): Lang {
  return localStorage.getItem("lang") === "zh" ? "zh" : "en";
}

function serverLanguage(): Lang {
  return "en";
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const lang = useSyncExternalStore(subscribeToLanguage, storedLanguage, serverLanguage);

  function toggleLang() {
    const next: Lang = lang === "en" ? "zh" : "en";
    localStorage.setItem("lang", next);
    window.dispatchEvent(new Event(LANGUAGE_CHANGED));
  }

  return (
    <LanguageContext.Provider value={{ lang, toggleLang }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
}
