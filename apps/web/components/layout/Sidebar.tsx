'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Shield, Network, Play } from 'lucide-react';
import { cn } from '@/lib/utils';

export function Sidebar() {
  const pathname = usePathname();

  const links = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Cases', href: '/cases', icon: Shield },
    { name: 'Graph Explorer', href: '/graph', icon: Network },
    { name: 'Detection Replay', href: '/replay', icon: Play },
  ];

  return (
    <div className="flex h-screen w-64 flex-col border-r border-slate-800 bg-slate-900">
      <div className="flex h-16 items-center px-6 border-b border-slate-800">
        <Link href="/" className="flex items-center gap-2">
          <Shield className="h-6 w-6 text-primary" />
          <span className="text-lg font-bold text-white tracking-tight">SentinelGraph</span>
        </Link>
      </div>
      <div className="flex-1 overflow-y-auto py-4">
        <nav className="space-y-1 px-3">
          {links.map((link) => {
            const Icon = link.icon;
            const isActive = pathname.startsWith(link.href);
            return (
              <Link
                key={link.name}
                href={link.href}
                className={cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive 
                    ? 'bg-slate-800 text-white' 
                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'
                )}
              >
                <Icon className={cn("h-4 w-4", isActive ? "text-primary" : "")} />
                {link.name}
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
