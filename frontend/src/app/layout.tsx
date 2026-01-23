import type { Metadata } from "next";
import { Oswald, Inter } from "next/font/google";
import "../styles/globals.css";  // ← Kembali ke path original

const oswald = Oswald({
  subsets: ["latin"],
  weight: ["500"],
  variable: "--font-oswald",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["500"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "PenineMate - AI Movie Q&A",
  description: "Ask anything about movies powered by AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${oswald.variable} ${inter.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
