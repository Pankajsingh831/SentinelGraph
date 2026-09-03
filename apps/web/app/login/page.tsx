'use client';
import { Shield } from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '@/lib/auth';

export default function LoginPage() {
    const [u, setU] = useState('');
    const [p, setP] = useState('');
    const [err, setErr] = useState('');
    const { login } = useAuth();

    const onSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await login(u, p);
        } catch (error) {
            setErr('Invalid credentials');
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-950">
            <div className="w-full max-w-md bg-slate-900 p-8 rounded-lg border border-slate-800 shadow-xl">
                <div className="flex flex-col items-center mb-8">
                    <Shield className="w-12 h-12 text-primary mb-4" />
                    <h1 className="text-2xl font-bold text-white tracking-tight">SentinelGraph</h1>
                    <p className="text-slate-400 text-sm mt-2">Analyst Dashboard Login</p>
                </div>
                <form onSubmit={onSubmit} className="space-y-4">
                    {err && <div className="p-3 bg-red-950/50 border border-red-900 text-red-500 rounded text-sm text-center">{err}</div>}
                    <div>
                        <input className="w-full bg-slate-950 border border-slate-800 rounded p-3 text-white placeholder-slate-500" placeholder="Username" value={u} onChange={e => setU(e.target.value)} />
                    </div>
                    <div>
                        <input className="w-full bg-slate-950 border border-slate-800 rounded p-3 text-white placeholder-slate-500" type="password" placeholder="Password" value={p} onChange={e => setP(e.target.value)} />
                    </div>
                    <button type="submit" className="w-full bg-primary hover:bg-primary/90 text-white font-medium p-3 rounded transition-colors">Login</button>
                    <p className="text-center text-xs text-slate-500 pt-4">Demo: analyst / analyst123</p>
                </form>
            </div>
        </div>
    );
}
