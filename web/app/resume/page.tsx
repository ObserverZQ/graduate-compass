"use client";

import { useState } from "react";
import FileUpload from "@/components/file-upload";
import PreferencesChat from "@/components/preferences-chat";

export default function ResumePage() {
  const [extractedText, setExtractedText] = useState<string | null>(null);

  return (
    <main className="flex-1 max-w-2xl mx-auto w-full px-6 py-16 flex flex-col gap-16">
      <section>
        <h1 className="text-2xl font-semibold mb-2 text-zinc-900 dark:text-zinc-100">
          Upload your resume
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-8">
          We&apos;ll read your profile to help match graduate programs.
        </p>
        <FileUpload onSuccess={(text) => setExtractedText(text)} />
      </section>

      {extractedText && (
        <section className="animate-fade-in">
          <h2 className="text-xl font-semibold mb-2 text-zinc-900 dark:text-zinc-100">
            Tell us your preferences
          </h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-6">
            All questions are optional — skip anything that doesn&apos;t apply.
          </p>
          <PreferencesChat resumeText={extractedText} />
        </section>
      )}
    </main>
  );
}
