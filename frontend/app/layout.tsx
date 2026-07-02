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
      {
        url: "/icons/app-icon-192.png",
        type: "image/png",
        sizes: "192x192",
      },
      {
        url: "/icons/app-icon-512.png",
        type: "image/png",
        sizes: "512x512",
      },
    ],
    shortcut: [
      {
        url: "/icons/app-icon-192.png",
        type: "image/png",
        sizes: "192x192",
      },
    ],
    apple: [
      {
        url: "/icons/app-icon-180.png",
        type: "image/png",
        sizes: "180x180",
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
