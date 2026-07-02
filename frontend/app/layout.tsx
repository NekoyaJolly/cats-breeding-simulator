import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { FeedbackWidget } from "@/components/FeedbackWidget";
import { PwaStatus } from "@/components/PwaStatus";
import "driver.js/dist/driver.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cat Coat Planner",
  description: "Kitten coat color & pattern simulator / 猫の色柄シミュレーター",
  applicationName: "Cat Coat Planner",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      { url: "/icons/icon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
  appleWebApp: {
    capable: true,
    title: "Coat Planner",
    statusBarStyle: "default",
  },
};

export const viewport: Viewport = {
  themeColor: "#0f172a",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        {children}
        <PwaStatus />
        <FeedbackWidget />
      </body>
    </html>
  );
}
