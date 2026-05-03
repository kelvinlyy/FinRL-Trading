import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinRL-X Command Center",
  description: "Adaptive Rotation strategy backtest results and strategy anatomy.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
