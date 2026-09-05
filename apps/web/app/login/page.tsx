'use client';
import { Shield, Loader2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';

export default function LoginPage() {
    const [u, setU] = useState('');
    const [p, setP] = useState('');
    const [err, setErr] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const { login, isAuthenticated, isLoading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!isLoading && isAuthenticated) {
            router.replace('/dashboard');
        }
    }, [isAuthenticated, isLoading, router]);

    const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        if (isSubmitting) return;

        if (!u.trim() || !p) {
            setErr('Please enter both username and password.');
            return;
        }

        setIsSubmitting(true);
        setErr('');
        try {
            await login(u.trim(), p);
            router.push('/dashboard');
        } catch (error: any) {
            setErr(error?.message || 'Invalid credentials');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4">
            <div className="w-full max-w-md bg-slate-900 p-8 rounded-lg border border-slate-800 shadow-xl">
                <div className="flex flex-col items-center mb-8">
                    <Shield className="w-12 h-12 text-primary mb-4" />
                    <h1 className="text-2xl font-bold text-white tracking-tight">SentinelGraph</h1>
                    <p className="text-slate-400 text-sm mt-2">Analyst Dashboard Login</p>
                </div>
                <form onSubmit={onSubmit} className="space-y-4">
                    {err && (
                        <div className="p-3 bg-red-950/50 border border-red-900 text-red-400 rounded text-sm text-center">
                            {err}
                        </div>
                    )}
                    <div>
                        <label htmlFor="username" className="block text-xs font-medium text-slate-400 mb-1.5">
                            Username
                        </label>
                        <input
                            id="username"
                            name="username"
                            type="text"
                            autoComplete="username"
                            disabled={isSubmitting}
                            className="w-full bg-slate-950 border border-slate-800 rounded p-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary transition-colors disabled:opacity-50"
                            placeholder="Enter username"
                            value={u}
                            onChange={e => setU(e.target.value)}
                        />
                    </div>
                    <div>
                        <label htmlFor="password" className="block text-xs font-medium text-slate-400 mb-1.5">
                            Password
                        </label>
                        <input
                            id="password"
                            name="password"
                            type="password"
                            autoComplete="current-password"
                            disabled={isSubmitting}
                            className="w-full bg-slate-950 border border-slate-800 rounded p-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary transition-colors disabled:opacity-50"
                            placeholder="Enter password"
                            value={p}
                            onChange={e => setP(e.target.value)}
                        />
                    </div>
                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="w-full bg-primary hover:bg-primary/90 disabled:opacity-50 text-white font-medium p-3 rounded transition-colors flex items-center justify-center gap-2 mt-6 cursor-pointer"
                    >
                        {isSubmitting ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                <span>Authenticating...</span>
                            </>
                        ) : (
                            <span>Login</span>
                        )}
                    </button>
                    <p className="text-center text-xs text-slate-500 pt-4">Demo credentials: admin / admin123</p>
                </form>
            </div>
        </div>
    );
}
