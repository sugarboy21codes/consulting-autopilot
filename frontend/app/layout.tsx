import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Consulting Autopilot | King Makers",
  description:
    "AI-powered diagnostic brief generator. Submit a company URL and problem statement, and receive a structured consulting diagnostic.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
