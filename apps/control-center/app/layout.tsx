import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AppChrome } from "../components/chrome.tsx";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Agent Research Control Center",
    template: "%s · Agent Research Control Center",
  },
  description:
    "Read-only standalone research-service status and local observations alongside clearly identified operator interface fixtures.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function RootLayout({ children }: { readonly children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppChrome>{children}</AppChrome>
      </body>
    </html>
  );
}
