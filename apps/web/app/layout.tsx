import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';

export const metadata: Metadata = {
  title: 'SentinelGraph',
  description: 'AI-Assisted Payment Abuse Detection',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-50 font-sans">
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
