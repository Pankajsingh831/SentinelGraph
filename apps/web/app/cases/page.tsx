'use client';
import { useCases } from '@/lib/hooks/use-cases';
import PageContainer from '@/components/layout/PageContainer';
import Link from 'next/link';
import { useState } from 'react';
import { formatRiskScore, getRiskTierColor, formatDate } from '@/lib/utils';

export default function CasesPage() {
    const [statusFilter, setStatusFilter] = useState('All');
    const [tierFilter, setTierFilter] = useState('All');
    const { data: response, isLoading } = useCases({
        status: statusFilter === 'All' ? undefined : statusFilter,
        risk_tier: tierFilter === 'All' ? undefined : tierFilter
    });

    if (isLoading) return <PageContainer title="Cases"><div className="animate-pulse space-y-4">{[1,2,3].map(i => <div key={i} className="h-12 bg-slate-800 rounded"></div>)}</div></PageContainer>;

    const filtered = response?.items || [];

    return (
        <PageContainer title="Cases">
            <div className="flex gap-4 mb-6">
                <select className="bg-slate-900 border border-slate-800 rounded px-3 py-2 text-sm" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                    <option>All</option><option>OPEN</option><option>ESCALATED</option><option>RESOLVED</option><option>CLOSED</option>
                </select>
                <select className="bg-slate-900 border border-slate-800 rounded px-3 py-2 text-sm" value={tierFilter} onChange={e => setTierFilter(e.target.value)}>
                    <option>All</option><option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>CRITICAL</option>
                </select>
            </div>
            
            {filtered.length === 0 ? (
                <div className="text-center p-12 bg-slate-900 rounded-lg border border-slate-800 text-slate-400">No cases found. Run the simulator to generate data.</div>
            ) : (
                <div className="bg-slate-900 rounded-lg border border-slate-800">
                    <table className="w-full text-left">
                        <thead className="bg-slate-950/50">
                            <tr>
                                <th className="p-4 font-medium text-slate-400 text-sm">Case ID</th>
                                <th className="p-4 font-medium text-slate-400 text-sm">Entity</th>
                                <th className="p-4 font-medium text-slate-400 text-sm">Risk Tier</th>
                                <th className="p-4 font-medium text-slate-400 text-sm">Overall Score</th>
                                <th className="p-4 font-medium text-slate-400 text-sm">Status</th>
                                <th className="p-4 font-medium text-slate-400 text-sm">Reason</th>
                                <th className="p-4 font-medium text-slate-400 text-sm">Created At</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map(c => (
                                <tr key={c.case_id} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                                    <td className="p-4"><Link href={`/cases/${c.case_id}`} className="text-primary hover:underline">{c.case_id.substring(0, 8)}...</Link></td>
                                    <td className="p-4">{c.primary_entity_id}</td>
                                    <td className={`p-4 font-medium ${getRiskTierColor(c.risk_tier)}`}>{c.risk_tier}</td>
                                    <td className="p-4">
                                        <div className="flex items-center gap-2">
                                            <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden"><div className="h-full bg-primary" style={{width: `${c.overall_risk_score * 100}%`}}></div></div>
                                            <span className="text-xs">{formatRiskScore(c.overall_risk_score)}</span>
                                        </div>
                                    </td>
                                    <td className="p-4"><span className="px-2 py-1 text-xs rounded bg-slate-800">{c.status}</span></td>
                                    <td className="p-4 text-sm truncate max-w-[200px]">{c.case_reason}</td>
                                    <td className="p-4 text-slate-400 text-sm">{formatDate(c.created_at)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </PageContainer>
    );
}
