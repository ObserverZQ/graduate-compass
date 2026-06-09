import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Upload Resume — Graduate Compass",
};

export default function ResumeLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
