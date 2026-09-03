'use client';
import { useCases } from '@/lib/hooks/use-cases';
import PageContainer from '@/components/layout/PageContainer';
import { Shield, AlertTriangle, Activity, BarChart3 } from 'lucide-react';
import Link from 'next/link';
import { formatRiskScore, getRiskTierColor, formatDate } from '@/lib/utils';

export default function DashboardPage() {
    const { data: response, isLoading, error, refetch } = useCases({});
    const cases = response?.items;

    if (isLoading) return <PageContainer title="Dashboard"><div>Loading...</div></PageContainer>;
    if (error) return <PageContainer title="Dashboard"><div className="text-red-500">Error loading data. <button onClick={() => refetch()}>Retry</button></div></PageContainer>;

    const total = cases?.length || 0;
    const critical = cases?.filter(c => c.risk_tier === 'CRITICAL').length || 0;
    const open = cases?.filter(c => c.status === 'OPEN').length || 0;
    const avgScore = total ? cases!.reduce((acc, c) => acc + c.overall_risk_score, 0) / total : 0;

    return (
        <PageContainer title="Dashboard">
            <div className="grid grid-cols-4 gap-4 mb-8">
                <div className="p-4 bg-slate-900 rounded-lg border border-slate-800 flex items-center gap-4">
                    <Shield className="w-8 h-8 text-blue-500" />
                    <div><div className="text-sm text-slate-400">Total Cases</div><div className="text-2xl font-bold">{total}</div></div>
                </div>
                <div className="p-4 bg-slate-900 rounded-lg border border-slate-800 flex items-center gap-4">
                    <AlertTriangle className="w-8 h-8 text-red-500" />
                    <div><div className="text-sm text-slate-400">Critical Cases</div><div className="text-2xl font-bold">{critical}</div></div>
                </div>
                <div className="p-4 bg-slate-900 rounded-lg border border-slate-800 flex items-center gap-4">
                    <Activity className="w-8 h-8 text-yellow-500" />
                    <div><div className="text-sm text-slate-400">Open Cases</div><div className="text-2xl font-bold">{open}</div></div>
                </div>
                <div className="p-4 bg-slate-900 rounded-lg border border-slate-800 flex items-center gap-4">
                    <BarChart3 className="w-8 h-8 text-green-500" />
                    <div><div className="text-sm text-slate-400">Avg Risk Score</div><div className="text-2xl font-bold">{Math.round(avgScore)}%</div></div>
                </div>
            </div>
            <div className="bg-slate-900 rounded-lg border border-slate-800">
                <div className="p-4 border-b border-slate-800 font-medium">Recent Cases</div>
                <table className="w-full text-left">
                    <thead className="bg-slate-950/50">
                        <tr>
                            <th className="p-4 font-medium text-slate-400 text-sm">Case ID</th>
                            <th className="p-4 font-medium text-slate-400 text-sm">Risk Tier</th>
                            <th className="p-4 font-medium text-slate-400 text-sm">Score</th>
                            <th className="p-4 font-medium text-slate-400 text-sm">Status</th>
                            <th className="p-4 font-medium text-slate-400 text-sm">Created</th>
                        </tr>
                    </thead>
                    <tbody>
                        {cases?.slice(0, 5).map(c => (
                            <tr key={c.case_id} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                                <td className="p-4"><Link href={`/cases/${c.case_id}`} className="text-primary hover:underline">{c.case_id.substring(0, 8)}...</Link></td>
                                <td className={`p-4 font-medium ${getRiskTierColor(c.risk_tier)}`}>{c.risk_tier}</td>
                                <td className="p-4">{formatRiskScore(c.overall_risk_score)}</td>
                                <td className="p-4"><span className="px-2 py-1 text-xs rounded bg-slate-800">{c.status}</span></td>
                                <td className="p-4 text-slate-400">{formatDate(c.created_at)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </PageContainer>
    );
}
