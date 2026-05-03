import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinRL-X",
  description: "Home: configure Adaptive Rotation and run backtests. Results: charts and exports for saved runs.",
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
