import type { Metadata } from "next";
import type { ReactNode } from "react";
import { FeedbackWidget } from "@/components/FeedbackWidget";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cat Coat Planner",
  description: "Kitten coat color & pattern simulator / 猫の色柄シミュレーター",
  applicationName: "Cat Coat Planner",
  icons: {
    icon: [
      {
        url: "/icons/app-icon.svg",
        type: "image/svg+xml",
        sizes: "any",
      },
    ],
    shortcut: [
      {
        url: "/icons/app-icon.svg",
        type: "image/svg+xml",
        sizes: "any",
      },
    ],
  },
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    title: "Coat Planner",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        {children}
        <FeedbackWidget />
      </body>
    </html>
  );
}
