'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useCase, useDecision } from '@/lib/hooks/use-cases';
import PageContainer from '@/components/layout/PageContainer';
import RiskGauge from '@/components/risk-score/RiskGauge';
import RiskBreakdown from '@/components/risk-score/RiskBreakdown';
import EvidenceList from '@/components/evidence/EvidenceList';
import GraphPanel from '@/components/graph/GraphPanel';
import CaseTimeline from '@/components/timeline/CaseTimeline';
import InvestigatorPanel from '@/components/ai-investigator/InvestigatorPanel';
import EntityResolutionPanel from '@/components/entity-resolution/EntityResolutionPanel';
import * as Tabs from '@radix-ui/react-tabs';
import { formatDate, getRiskTierColor } from '@/lib/utils';
import {
  ArrowLeft,
  AlertCircle,
  RefreshCw,
  FileQuestion,
  Loader2,
  CheckCircle2,
} from 'lucide-react';

function getStatusBadgeClass(status: string | null | undefined): string {
  switch (status?.toLowerCase()) {
    case 'open':
      return 'bg-amber-950/60 text-amber-300 border-amber-800/60';
    case 'escalated':
      return 'bg-red-950/60 text-red-300 border-red-800/60';
    case 'resolved':
      return 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60';
    case 'closed':
      return 'bg-slate-800/80 text-slate-300 border-slate-700/60';
    default:
      return 'bg-slate-800 text-slate-400 border-slate-700';
  }
}

export default function CaseDetailPage({ params }: { params: { caseId: string } }) {
  const {
    data: caseData,
    isLoading,
    isError,
    error: caseError,
    refetch,
    isFetching,
  } = useCase(params.caseId);

  const {
    mutate: decide,
    isPending: isDeciding,
    error: decisionError,
    isSuccess: isDecisionSuccess,
  } = useDecision(params.caseId);

  const [reason, setReason] = useState('');
  const [activeTab, setActiveTab] = useState('evidence');

  // 1. Initial Loading State
  if (isLoading) {
    return (
      <PageContainer title="Case Detail">
        <div className="space-y-6">
          <div className="h-4 w-28 bg-slate-800 rounded animate-pulse" />
          <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 animate-pulse space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="h-6 w-48 bg-slate-800 rounded" />
              <div className="flex gap-2">
                <div className="h-6 w-16 bg-slate-800 rounded" />
                <div className="h-6 w-20 bg-slate-800 rounded" />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-2">
              <div className="h-4 w-36 bg-slate-800 rounded" />
              <div className="h-4 w-36 bg-slate-800 rounded" />
              <div className="h-4 w-36 bg-slate-800 rounded" />
              <div className="h-4 w-36 bg-slate-800 rounded" />
            </div>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-3 h-96 bg-slate-900 rounded-lg border border-slate-800 animate-pulse" />
            <div className="lg:col-span-6 h-96 bg-slate-900 rounded-lg border border-slate-800 animate-pulse" />
            <div className="lg:col-span-3 h-96 bg-slate-900 rounded-lg border border-slate-800 animate-pulse" />
          </div>
        </div>
      </PageContainer>
    );
  }

  // 2. Error / Not Found States
  const isNotFound =
    (caseError as any)?.status === 404 ||
    caseError?.message?.toLowerCase().includes('not found') ||
    caseError?.message?.toLowerCase().includes('case_not_found') ||
    (!isLoading && !isError && !caseData);

  if (isNotFound) {
    return (
      <PageContainer title="Case Not Found">
        <div className="max-w-xl mx-auto my-12 bg-slate-900 rounded-lg border border-slate-800 p-8 text-center">
          <FileQuestion className="w-12 h-12 text-slate-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-200 mb-2">Case Not Found</h3>
          <p className="text-sm text-slate-400 mb-6">
            The case with ID{' '}
            <code className="font-mono text-slate-300 bg-slate-950 px-1.5 py-0.5 rounded text-xs">
              {params.caseId}
            </code>{' '}
            does not exist or has been removed.
          </p>
          <Link
            href="/cases"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Cases
          </Link>
        </div>
      </PageContainer>
    );
  }

  if (isError || !caseData) {
    return (
      <PageContainer title="Error Loading Case">
        <div className="max-w-xl mx-auto my-12 bg-slate-900 rounded-lg border border-red-900/50 bg-red-950/20 p-8 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-red-200 mb-2">Failed to Load Case</h3>
          <p className="text-sm text-red-400 mb-6">
            {caseError instanceof Error ? caseError.message : 'An error occurred while fetching case details.'}
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 text-white rounded-md text-sm font-medium hover:bg-slate-700 border border-slate-700 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
              Retry
            </button>
            <Link
              href="/cases"
              className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 text-slate-300 rounded-md text-sm font-medium hover:bg-slate-800 border border-slate-800 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Cases
            </Link>
          </div>
        </div>
      </PageContainer>
    );
  }

  const isResolved =
    caseData.status?.toUpperCase() === 'RESOLVED' ||
    caseData.status?.toUpperCase() === 'CLOSED';
  const isDisabled = isResolved || isDeciding;

  const handleDecision = (decisionType: string) => {
    if (isDisabled) return;
    decide(
      {
        decision: decisionType,
        reason: reason.trim() || undefined,
      },
      {
        onSuccess: () => {
          setReason('');
        },
      }
    );
  };

  return (
    <PageContainer title={`Case ${caseData.case_id.substring(0, 8)}`}>
      <div className="space-y-6">
        {/* Navigation & Case Header Banner */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Link
              href="/cases"
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Cases
            </Link>
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800 rounded px-2.5 py-1 transition-colors disabled:opacity-50"
              title="Refresh case data"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin text-primary' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>

          <div className="bg-slate-900 rounded-lg border border-slate-800 p-5">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
              <div>
                <div className="flex flex-wrap items-center gap-2.5 mb-1.5">
                  <h2 className="text-lg font-bold text-white font-mono tracking-tight">
                    Case {caseData.case_id.substring(0, 8)}...
                  </h2>
                  <span className="text-xs text-slate-500 font-mono hidden sm:inline">
                    ({caseData.case_id})
                  </span>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border uppercase tracking-wider ${getStatusBadgeClass(
                      caseData.status
                    )}`}
                  >
                    {caseData.status}
                  </span>
                  <span
                    className={`text-xs font-semibold px-2 py-0.5 rounded bg-slate-950 border border-slate-800 ${getRiskTierColor(
                      caseData.risk_tier
                    )}`}
                  >
                    {caseData.risk_tier}
                  </span>
                </div>
                <p className="text-sm text-slate-300 leading-relaxed">
                  {caseData.case_reason}
                </p>
              </div>
            </div>

            {/* Detailed Case Metadata */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-4 text-xs">
              <div>
                <span className="text-slate-500 block mb-0.5">Primary Entity</span>
                <span
                  className="font-mono text-slate-300 truncate block"
                  title={`${caseData.primary_entity_type}: ${caseData.primary_entity_id}`}
                >
                  <span className="text-slate-400 capitalize">{caseData.primary_entity_type}:</span>{' '}
                  {caseData.primary_entity_id}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block mb-0.5">Created At</span>
                <span className="text-slate-300">{formatDate(caseData.created_at)}</span>
              </div>
              <div>
                <span className="text-slate-500 block mb-0.5">Last Updated</span>
                <span className="text-slate-300">{formatDate(caseData.updated_at)}</span>
              </div>
              <div>
                <span className="text-slate-500 block mb-0.5">Resolved At</span>
                <span className="text-slate-300">
                  {caseData.resolved_at ? formatDate(caseData.resolved_at) : 'Active / Unresolved'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* 3-Panel Main Layout (Responsive: 1 column on mobile, 3/6/3 on lg) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Panel: Risk Assessment & Analyst Decisions */}
          <div className="lg:col-span-3 space-y-6">
            <div className="bg-slate-900 p-4 rounded-lg border border-slate-800">
              <h3 className="font-medium text-white mb-4">Risk Assessment</h3>
              <RiskGauge score={caseData.overall_risk_score} tier={caseData.risk_tier} />
              <RiskBreakdown
                tx={caseData.transaction_risk_score}
                nw={caseData.network_risk_score}
                tp={caseData.temporal_risk_score}
              />
            </div>

            <div className="bg-slate-900 p-4 rounded-lg border border-slate-800">
              <h3 className="font-medium text-white mb-4">Analyst Decision</h3>
              <textarea
                className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm mb-4 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-slate-700 disabled:opacity-50"
                placeholder="Reason for decision..."
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                disabled={isDisabled}
                rows={3}
              />
              <div className="grid grid-cols-2 gap-2">
                <button
                  disabled={isDisabled}
                  onClick={() => handleDecision('MONITOR')}
                  className="bg-blue-600/20 text-blue-400 border border-blue-600/30 py-2 rounded text-xs font-medium hover:bg-blue-600/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Monitor
                </button>
                <button
                  disabled={isDisabled}
                  onClick={() => handleDecision('ESCALATE')}
                  className="bg-orange-600/20 text-orange-400 border border-orange-600/30 py-2 rounded text-xs font-medium hover:bg-orange-600/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Escalate
                </button>
                <button
                  disabled={isDisabled}
                  onClick={() => handleDecision('CONFIRMED_ABUSE')}
                  className="bg-red-600/20 text-red-400 border border-red-600/30 py-2 rounded text-xs font-medium hover:bg-red-600/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Confirmed
                </button>
                <button
                  disabled={isDisabled}
                  onClick={() => handleDecision('FALSE_POSITIVE')}
                  className="bg-emerald-600/20 text-emerald-400 border border-emerald-600/30 py-2 rounded text-xs font-medium hover:bg-emerald-600/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  False Pos
                </button>
              </div>

              {isDeciding && (
                <div className="text-xs text-slate-400 mt-3 text-center animate-pulse flex items-center justify-center gap-1.5">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
                  <span>Recording decision...</span>
                </div>
              )}

              {isDecisionSuccess && (
                <div className="text-xs text-emerald-400 mt-3 p-2 bg-emerald-950/40 border border-emerald-900/50 rounded flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                  <span>Decision recorded successfully.</span>
                </div>
              )}

              {decisionError && (
                <div className="text-xs text-red-400 mt-3 p-2 bg-red-950/50 border border-red-900/50 rounded flex flex-col gap-1">
                  <div className="flex items-center gap-1 font-medium">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    <span>Decision Submission Failed</span>
                  </div>
                  <span>
                    {(decisionError as any)?.message || 'Failed to submit decision.'}
                  </span>
                </div>
              )}

              {isResolved && (
                <div className="text-xs text-slate-400 mt-3 p-2 bg-slate-950/50 border border-slate-800 rounded text-center">
                  Case is <span className="text-slate-300 font-medium uppercase">{caseData.status}</span>. Decision recorded.
                </div>
              )}
            </div>
          </div>

          {/* Center Panel: Evidence, Graph, Timeline */}
          <div className="lg:col-span-6 bg-slate-900 rounded-lg border border-slate-800 flex flex-col min-h-[520px]">
            <Tabs.Root value={activeTab} onValueChange={setActiveTab} className="flex flex-col h-full">
              <Tabs.List className="flex border-b border-slate-800 p-2 gap-2 bg-slate-950/40">
                <Tabs.Trigger
                  value="evidence"
                  className="px-4 py-2 text-sm font-medium rounded data-[state=active]:bg-slate-800 data-[state=active]:text-white text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Evidence
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="resolution"
                  className="px-4 py-2 text-sm font-medium rounded data-[state=active]:bg-slate-800 data-[state=active]:text-white text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Resolution
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="graph"
                  className="px-4 py-2 text-sm font-medium rounded data-[state=active]:bg-slate-800 data-[state=active]:text-white text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Graph
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="timeline"
                  className="px-4 py-2 text-sm font-medium rounded data-[state=active]:bg-slate-800 data-[state=active]:text-white text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Timeline
                </Tabs.Trigger>
              </Tabs.List>
              <Tabs.Content value="evidence" className="flex-1 p-4 overflow-y-auto">
                <EvidenceList caseId={caseData.case_id} />
              </Tabs.Content>
              <Tabs.Content value="resolution" className="flex-1 p-4 overflow-y-auto">
                <EntityResolutionPanel
                  caseId={caseData.case_id}
                  onNavigateToGraph={() => setActiveTab('graph')}
                />
              </Tabs.Content>
              <Tabs.Content value="graph" className="flex-1 overflow-hidden min-h-[450px]">
                <GraphPanel
                  entityType={caseData.primary_entity_type}
                  entityId={caseData.primary_entity_id}
                  caseRiskScore={caseData.overall_risk_score}
                  caseRiskTier={caseData.risk_tier}
                  networkRiskScore={caseData.network_risk_score}
                />
              </Tabs.Content>
              <Tabs.Content value="timeline" className="flex-1 p-4 overflow-y-auto">
                <CaseTimeline caseId={caseData.case_id} />
              </Tabs.Content>
            </Tabs.Root>
          </div>

          {/* Right Panel: AI Investigator */}
          <div className="lg:col-span-3">
            <InvestigatorPanel caseId={caseData.case_id} />
          </div>
        </div>
      </div>
    </PageContainer>
  );
}
