'use client';
import { useCase, useDecision } from '@/lib/hooks/use-cases';
import PageContainer from '@/components/layout/PageContainer';
import RiskGauge from '@/components/risk-score/RiskGauge';
import RiskBreakdown from '@/components/risk-score/RiskBreakdown';
import EvidenceList from '@/components/evidence/EvidenceList';
import GraphPanel from '@/components/graph/GraphPanel';
import CaseTimeline from '@/components/timeline/CaseTimeline';
import InvestigatorPanel from '@/components/ai-investigator/InvestigatorPanel';
import * as Tabs from '@radix-ui/react-tabs';
import { useState } from 'react';

export default function CaseDetailPage({ params }: { params: { caseId: string } }) {
    const { data: caseData, isLoading } = useCase(params.caseId);
    const { mutate: decide, isPending, error } = useDecision(params.caseId);
    const [reason, setReason] = useState('');

    if (isLoading || !caseData) return <PageContainer title="Case Detail">Loading...</PageContainer>;

    const isResolved = caseData.status?.toUpperCase() === 'RESOLVED' || caseData.status?.toUpperCase() === 'CLOSED';
    const isDisabled = isResolved || isPending;

    const handleDecision = (decisionType: string) => {
        decide({
            decision: decisionType,
            reason: reason.trim() || undefined
        });
    };

    return (
        <PageContainer title={`Case ${caseData.case_id.substring(0, 8)}`}>
            <div className="grid grid-cols-12 gap-6 h-full">
                {/* Left Panel */}
                <div className="col-span-3 space-y-6 overflow-y-auto">
                    <div className="bg-slate-900 p-4 rounded-lg border border-slate-800">
                        <h3 className="font-medium mb-4">Risk Assessment</h3>
                        <RiskGauge score={caseData.overall_risk_score} tier={caseData.risk_tier} />
                        <RiskBreakdown tx={caseData.transaction_risk_score} nw={caseData.network_risk_score} tp={caseData.temporal_risk_score} />
                    </div>
                    <div className="bg-slate-900 p-4 rounded-lg border border-slate-800">
                        <h3 className="font-medium mb-4">Decision</h3>
                        <textarea 
                            className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm mb-4 disabled:opacity-50" 
                            placeholder="Reason for decision..."
                            value={reason}
                            onChange={e => setReason(e.target.value)}
                            disabled={isDisabled}
                        />
                        <div className="grid grid-cols-2 gap-2">
                            <button 
                                disabled={isDisabled} 
                                onClick={() => handleDecision('MONITOR')}
                                className="bg-blue-600/20 text-blue-500 py-2 rounded text-sm hover:bg-blue-600/30 disabled:opacity-50 transition-colors"
                            >
                                Monitor
                            </button>
                            <button 
                                disabled={isDisabled} 
                                onClick={() => handleDecision('ESCALATE')}
                                className="bg-orange-600/20 text-orange-500 py-2 rounded text-sm hover:bg-orange-600/30 disabled:opacity-50 transition-colors"
                            >
                                Escalate
                            </button>
                            <button 
                                disabled={isDisabled} 
                                onClick={() => handleDecision('CONFIRMED_ABUSE')}
                                className="bg-red-600/20 text-red-500 py-2 rounded text-sm hover:bg-red-600/30 disabled:opacity-50 transition-colors"
                            >
                                Confirmed
                            </button>
                            <button 
                                disabled={isDisabled} 
                                onClick={() => handleDecision('FALSE_POSITIVE')}
                                className="bg-green-600/20 text-green-500 py-2 rounded text-sm hover:bg-green-600/30 disabled:opacity-50 transition-colors"
                            >
                                False Pos
                            </button>
                        </div>
                        {isPending && (
                            <div className="text-xs text-slate-400 mt-2 text-center animate-pulse">Recording decision...</div>
                        )}
                        {error && (
                            <div className="text-xs text-red-400 mt-2 p-2 bg-red-950/50 border border-red-900/50 rounded">
                                {(error as any)?.message || 'Failed to submit decision'}
                            </div>
                        )}
                        {isResolved && (
                            <div className="text-xs text-slate-400 mt-2 p-2 bg-slate-950/50 border border-slate-800 rounded text-center">
                                Case is {caseData.status}. Decision recorded.
                            </div>
                        )}
                    </div>
                </div>

                {/* Center Panel */}
                <div className="col-span-6 bg-slate-900 rounded-lg border border-slate-800 flex flex-col">
                    <Tabs.Root defaultValue="evidence" className="flex flex-col h-full">
                        <Tabs.List className="flex border-b border-slate-800 p-2 gap-2">
                            <Tabs.Trigger value="evidence" className="px-4 py-2 text-sm rounded data-[state=active]:bg-slate-800 data-[state=active]:text-white text-slate-400">Evidence</Tabs.Trigger>
                            <Tabs.Trigger value="graph" className="px-4 py-2 text-sm rounded data-[state=active]:bg-slate-800 data-[state=active]:text-white text-slate-400">Graph</Tabs.Trigger>
                            <Tabs.Trigger value="timeline" className="px-4 py-2 text-sm rounded data-[state=active]:bg-slate-800 data-[state=active]:text-white text-slate-400">Timeline</Tabs.Trigger>
                        </Tabs.List>
                        <Tabs.Content value="evidence" className="flex-1 p-4 overflow-y-auto"><EvidenceList caseId={caseData.case_id} /></Tabs.Content>
                        <Tabs.Content value="graph" className="flex-1 overflow-hidden"><GraphPanel entityType={caseData.primary_entity_type} entityId={caseData.primary_entity_id} /></Tabs.Content>
                        <Tabs.Content value="timeline" className="flex-1 p-4 overflow-y-auto"><CaseTimeline caseId={caseData.case_id} /></Tabs.Content>
                    </Tabs.Root>
                </div>

                {/* Right Panel */}
                <div className="col-span-3 overflow-y-auto">
                    <InvestigatorPanel caseId={caseData.case_id} />
                </div>
            </div>
        </PageContainer>
    );
}
