'use client';

import { ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { RequireAuth } from '@/lib/auth';

interface PageContainerProps {
  children: ReactNode;
  title: string;
}

export default function PageContainer({ children, title }: PageContainerProps) {
  return (
    <RequireAuth>
      <div className="flex h-screen overflow-hidden bg-slate-950">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header title={title} />
          <main className="flex-1 overflow-y-auto p-6">
            {children}
          </main>
        </div>
      </div>
    </RequireAuth>
  );
}
