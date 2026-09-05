'use client';

import React, { useMemo } from 'react';
import Link from 'next/link';
import { useCases, useCase, useCaseEvidence } from '@/lib/hooks/use-cases';
import PageContainer from '@/components/layout/PageContainer';
import RiskGauge from '@/components/risk-score/RiskGauge';
import RiskBreakdown from '@/components/risk-score/RiskBreakdown';
import GraphPanel from '@/components/graph/GraphPanel';
import CaseTimeline from '@/components/timeline/CaseTimeline';
import { CaseListItem } from '@/lib/types';
import { formatDate } from '@/lib/utils';
import {
  Shield,
  AlertTriangle,
  Activity,
  BarChart3,
  ArrowRight,
  RefreshCw,
  Network,
  Clock,
  AlertCircle,
  PieChart,
  TrendingUp,
  Flame,
} from 'lucide-react';

/**
 * Select the most critical active case according to the preferred priority:
 * 1. CRITICAL case with highest overall_risk_score
 * 2. HIGH case with highest overall_risk_score
 * 3. OPEN case with highest overall_risk_score
 * 4. Otherwise latest case by created_at
 */
function selectFeaturedCase(cases: CaseListItem[]): CaseListItem | null {
  if (!cases || cases.length === 0) return null;

  // 1. CRITICAL case with highest overall_risk_score
  const criticalCases = cases.filter(c => c.risk_tier?.toUpperCase() === 'CRITICAL');
  if (criticalCases.length > 0) {
    return criticalCases.slice().sort((a, b) => b.overall_risk_score - a.overall_risk_score)[0];
  }

  // 2. HIGH case with highest overall_risk_score
  const highCases = cases.filter(c => c.risk_tier?.toUpperCase() === 'HIGH');
  if (highCases.length > 0) {
    return highCases.slice().sort((a, b) => b.overall_risk_score - a.overall_risk_score)[0];
  }

  // 3. OPEN case with highest overall_risk_score
  const openCases = cases.filter(c => c.status?.toUpperCase() === 'OPEN');
  if (openCases.length > 0) {
    return openCases.slice().sort((a, b) => b.overall_risk_score - a.overall_risk_score)[0];
  }

  // 4. Otherwise latest case
  return cases.slice().sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )[0];
}

/** Converts a 0.0-1.0 or 0-100 score safely to an integer 0-100 percentage. */
function toPercentage(score: number | undefined | null): number {
  if (score == null || isNaN(score)) return 0;
  return Math.round(score > 1 ? score : score * 100);
}

/** Get risk badge styling */
function getRiskBadgeClasses(tier: string | undefined): string {
  switch (tier?.toUpperCase()) {
    case 'CRITICAL':
      return 'bg-red-950/80 text-red-400 border-red-800/80';
    case 'HIGH':
      return 'bg-orange-950/80 text-orange-400 border-orange-800/80';
    case 'MEDIUM':
      return 'bg-yellow-950/80 text-yellow-400 border-yellow-800/80';
    case 'LOW':
      return 'bg-blue-950/80 text-blue-400 border-blue-800/80';
    default:
      return 'bg-slate-800 text-slate-400 border-slate-700';
  }
}

/** Get featured card accent container styling */
function getFeaturedCardClasses(tier: string | undefined): string {
  switch (tier?.toUpperCase()) {
    case 'CRITICAL':
      return 'border-red-500/50 bg-gradient-to-br from-red-950/20 via-slate-900 to-slate-900 shadow-xl shadow-red-950/20';
    case 'HIGH':
      return 'border-orange-500/50 bg-gradient-to-br from-orange-950/20 via-slate-900 to-slate-900 shadow-xl shadow-orange-950/20';
    case 'MEDIUM':
      return 'border-yellow-500/40 bg-gradient-to-br from-yellow-950/15 via-slate-900 to-slate-900 shadow-lg shadow-yellow-950/10';
    case 'LOW':
      return 'border-blue-500/30 bg-gradient-to-br from-blue-950/10 via-slate-900 to-slate-900';
    default:
      return 'border-slate-800 bg-slate-900';
  }
}

/** Skeleton for overview metrics */
function MetricCardSkeleton() {
  return (
    <div className="p-4 bg-slate-900/60 rounded-xl border border-slate-800 animate-pulse">
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 rounded-lg bg-slate-800 shrink-0"></div>
        <div className="space-y-2 flex-1">
          <div className="h-3 w-20 bg-slate-800 rounded"></div>
          <div className="h-6 w-12 bg-slate-800 rounded"></div>
          <div className="h-2 w-28 bg-slate-800/60 rounded"></div>
        </div>
      </div>
    </div>
  );
}

/** Featured Investigation Section */
function FeaturedInvestigationSection({ featuredCase }: { featuredCase: CaseListItem }) {
  const { data: caseDetail, isLoading: isDetailLoading, isError: isDetailError } = useCase(
    featuredCase.case_id
  );
  const { data: evidenceList, isLoading: isEvidenceLoading, isError: isEvidenceError } = useCaseEvidence(
    featuredCase.case_id
  );

  const overallScore = toPercentage(caseDetail?.overall_risk_score ?? featuredCase.overall_risk_score);
  const txScore = toPercentage(caseDetail?.transaction_risk_score ?? 0);
  const nwScore = toPercentage(caseDetail?.network_risk_score ?? 0);
  const tpScore = toPercentage(caseDetail?.temporal_risk_score ?? 0);

  // Sort evidence by severity rank (CRITICAL > HIGH > MEDIUM > LOW) and pick top 4
  const severityRank: Record<string, number> = {
    CRITICAL: 4,
    HIGH: 3,
    MEDIUM: 2,
    LOW: 1,
  };
  const rawEvidence = Array.isArray(evidenceList) ? evidenceList : [];
  const topEvidence = rawEvidence
    .slice()
    .sort((a, b) => {
      const sa = severityRank[a?.severity?.toUpperCase()] || 0;
      const sb = severityRank[b?.severity?.toUpperCase()] || 0;
      return sb - sa;
    })
    .slice(0, 4);

  return (
    <div className="space-y-6">
      {/* Visual Centerpiece: Featured Investigation Card */}
      <div className={`p-6 rounded-xl border transition-all ${getFeaturedCardClasses(featuredCase.risk_tier)}`}>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-slate-800/80">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
                Featured Investigation
              </span>
              <span className={`text-xs font-bold px-2.5 py-1 rounded border ${getRiskBadgeClasses(featuredCase.risk_tier)}`}>
                {featuredCase.risk_tier} RISK
              </span>
              <span className="text-xs font-medium px-2.5 py-1 rounded bg-slate-800/80 text-slate-300 border border-slate-700">
                {featuredCase.status}
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              <span>Case</span>
              <span className="font-mono text-primary">{featuredCase.case_id}</span>
            </h2>
            <p className="text-sm text-slate-300 max-w-2xl">
              {featuredCase.case_reason || 'Automated risk detection triggered investigation.'}
            </p>
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-400 pt-1">
              <span>Primary Entity: <strong className="text-slate-200">{featuredCase.primary_entity_type}</strong> ({featuredCase.primary_entity_id})</span>
              <span>Detected: <strong className="text-slate-200">{formatDate(featuredCase.created_at)}</strong></span>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-6 shrink-0">
            <div className="flex flex-col items-center">
              <RiskGauge score={overallScore} tier={featuredCase.risk_tier} />
              <span className="text-xs font-medium text-slate-400 mt-1">Overall Threat Index</span>
            </div>
            <Link
              href={`/cases/${featuredCase.case_id}`}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-primary hover:bg-primary/90 text-white font-medium text-sm transition-all shadow-lg hover:shadow-primary/25"
            >
              <span>Open Investigation</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>

        {/* Section: Why was this flagged? */}
        <div className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-semibold text-white">Why Was This Flagged?</h3>
              <p className="text-xs text-slate-400">
                Tri-factor threat assessment combining transaction intelligence, network topology, and temporal velocity.
              </p>
            </div>
          </div>

          {isDetailLoading ? (
            <div className="p-4 bg-slate-950/50 rounded-lg border border-slate-800 text-slate-400 text-sm animate-pulse text-center">
              Loading signal breakdown...
            </div>
          ) : isDetailError ? (
            <div className="p-4 bg-slate-950/50 rounded-lg border border-red-900/40 text-red-400 text-sm text-center">
              Risk details unavailable.
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
              {/* Left Column: Human Explanations */}
              <div className="lg:col-span-5 space-y-3">
                <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
                  <div className="text-xs font-semibold text-blue-400 flex items-center justify-between">
                    <span>Transaction Risk</span>
                    <span>{txScore}%</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Transaction risk â€” ML-derived transaction-level risk. Evaluates micro-features, amounts, and historical baseline patterns.
                  </p>
                </div>
                <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
                  <div className="text-xs font-semibold text-purple-400 flex items-center justify-between">
                    <span>Network Risk</span>
                    <span>{nwScore}%</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Network risk â€” risk associated with the entity network. Uncovers shared devices, IP clusters, and synthetic rings.
                  </p>
                </div>
                <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
                  <div className="text-xs font-semibold text-emerald-400 flex items-center justify-between">
                    <span>Temporal Risk</span>
                    <span>{tpScore}%</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Temporal risk â€” suspicious behavior over time. Tracks velocity spikes, rapid bursts, and anomalous timing windows.
                  </p>
                </div>
              </div>

              {/* Right Column: Visual Breakdown & Formula Box */}
              <div className="lg:col-span-7 space-y-4">
                <div className="p-4 bg-slate-950/70 rounded-lg border border-slate-800">
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Signal Contribution Bars
                  </span>
                  <RiskBreakdown tx={txScore} nw={nwScore} tp={tpScore} />
                </div>

                {/* Mathematical Aggregation Formula Display */}
                <div className="p-3.5 bg-slate-950/80 rounded-lg border border-slate-800/90 font-mono text-xs">
                  <div className="flex items-center justify-between text-slate-300 mb-1">
                    <span className="font-semibold text-white">Risk Aggregation Formula</span>
                    <span className="text-slate-400 font-sans text-[11px]">Backend weights confirmed (0.50 / 0.30 / 0.20)</span>
                  </div>
                  <div className="text-slate-400 mb-1.5 font-sans text-xs">
                    Overall Risk = (0.50 Ã— Transaction Risk) + (0.30 Ã— Network Risk) + (0.20 Ã— Temporal Risk)
                  </div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-200">
                    <span className="font-bold text-primary">{overallScore}%</span>
                    <span className="text-slate-400"> = </span>
                    <span className="text-blue-400">(0.50 Ã— {txScore}%)</span>
                    <span className="text-slate-500"> + </span>
                    <span className="text-purple-400">(0.30 Ã— {nwScore}%)</span>
                    <span className="text-slate-500"> + </span>
                    <span className="text-emerald-400">(0.20 Ã— {tpScore}%)</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Grid: Detection Signals & Network Context */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Detection Signals Section */}
        <div className="p-5 bg-slate-900 rounded-xl border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-amber-500" />
                <h3 className="text-base font-semibold text-white">Detection Signals</h3>
              </div>
              <span className="text-xs text-slate-400">
                {topEvidence.length} {topEvidence.length === 1 ? 'record' : 'records'}
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Real-time heuristic & statistical evidence records corroborating this threat.
            </p>

            {isEvidenceLoading ? (
              <div className="p-6 text-center text-slate-500 text-sm animate-pulse">
                Loading evidence signals...
              </div>
            ) : isEvidenceError ? (
              <div className="p-4 bg-slate-950/60 rounded-lg border border-red-900/40 text-red-400 text-sm text-center">
                Evidence unavailable.
              </div>
            ) : topEvidence.length === 0 ? (
              <div className="p-8 text-center bg-slate-950/50 rounded-lg border border-slate-800/80 text-slate-500 text-sm">
                No evidence records available for this case.
              </div>
            ) : (
              <div className="space-y-3">
                {topEvidence.map(ev => (
                  <div
                    key={ev.evidence_id}
                    className="p-3.5 bg-slate-950 rounded-lg border border-slate-800 hover:border-slate-700 transition-colors"
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="font-semibold text-sm text-slate-200 uppercase tracking-wide">
                        {ev.evidence_type}
                      </span>
                      <span className={`text-[11px] font-bold px-2 py-0.5 rounded border ${getRiskBadgeClasses(ev.severity)}`}>
                        {ev.severity}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 mb-2 leading-relaxed">
                      {ev.description}
                    </p>
                    {ev.created_at && (
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                        <Clock className="w-3 h-3" />
                        <span>Detected {formatDate(ev.created_at)}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Network Context Section */}
        <div className="p-5 bg-slate-900 rounded-xl border border-slate-800 flex flex-col">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <Network className="w-5 h-5 text-purple-400" />
              <h3 className="text-base font-semibold text-white">Network Context</h3>
            </div>
            <span className="text-xs text-slate-400 font-mono">
              {featuredCase.primary_entity_type || 'entity'}: {(featuredCase.primary_entity_id || '').substring(0, 8)}...
            </span>
          </div>
          <p className="text-xs text-slate-400 mb-4">
            Entity network associated with this investigation. Visualizes interconnected devices, IP addresses, and instruments.
          </p>

          <div className="h-80 w-full rounded-lg overflow-hidden bg-slate-950 border border-slate-800 relative">
            <GraphPanel
              entityType={featuredCase.primary_entity_type || 'customer'}
              entityId={featuredCase.primary_entity_id || ''}
              depth={1}
              limit={25}
            />
          </div>
        </div>
      </div>

      {/* Investigation Timeline Section */}
      <div className="p-5 bg-slate-900 rounded-xl border border-slate-800">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-blue-400" />
            <h3 className="text-base font-semibold text-white">Investigation Timeline</h3>
          </div>
          <span className="text-xs text-slate-400">Sequential event progression</span>
        </div>
        <p className="text-xs text-slate-400 mb-6">
          Chronological sequence: event ingestion â†’ suspicious activity detection â†’ aggregate threat scoring â†’ case creation.
        </p>

        <div className="p-4 bg-slate-950/60 rounded-lg border border-slate-800/80">
          <CaseTimeline caseId={featuredCase.case_id} />
        </div>
      </div>
    </div>
  );
}

interface ActivityBucket {
  dateKey: string;
  displayDate: string;
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export default function DashboardPage() {
  const { data: response, isLoading, error, refetch, isFetching } = useCases({ limit: 100 });
  const cases = response?.items || [];

  // 1. KPI Calculations (Exact data from API)
  const total = response?.total ?? cases.length;
  const criticalCount = useMemo(
    () => cases.filter(c => c.risk_tier?.toUpperCase() === 'CRITICAL').length,
    [cases]
  );
  const highCount = useMemo(
    () => cases.filter(c => c.risk_tier?.toUpperCase() === 'HIGH').length,
    [cases]
  );
  const openCount = useMemo(
    () => cases.filter(c => c.status?.toUpperCase() === 'OPEN').length,
    [cases]
  );
  const avgScore = useMemo(() => {
    if (cases.length === 0) return 0;
    const rawAvg = cases.reduce((acc, c) => acc + c.overall_risk_score, 0) / cases.length;
    return toPercentage(rawAvg);
  }, [cases]);

  // 2. Risk Distribution Data
  const tierDistribution = useMemo(() => {
    const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    for (const c of cases) {
      const tier = c.risk_tier?.toUpperCase();
      if (tier === 'CRITICAL') counts.CRITICAL++;
      else if (tier === 'HIGH') counts.HIGH++;
      else if (tier === 'MEDIUM') counts.MEDIUM++;
      else if (tier === 'LOW') counts.LOW++;
    }
    const totalLoaded = cases.length;
    return {
      counts,
      percentages: {
        CRITICAL: totalLoaded > 0 ? Math.round((counts.CRITICAL / totalLoaded) * 100) : 0,
        HIGH: totalLoaded > 0 ? Math.round((counts.HIGH / totalLoaded) * 100) : 0,
        MEDIUM: totalLoaded > 0 ? Math.round((counts.MEDIUM / totalLoaded) * 100) : 0,
        LOW: totalLoaded > 0 ? Math.round((counts.LOW / totalLoaded) * 100) : 0,
      },
    };
  }, [cases]);

  // 3. Real Detection Trend Data (Grouped by event creation dates)
  const activityTimeline = useMemo(() => {
    if (cases.length === 0) return [];
    const buckets: Record<string, ActivityBucket> = {};

    for (const c of cases) {
      if (!c.created_at) continue;
      const d = new Date(c.created_at);
      if (isNaN(d.getTime())) continue;

      const dateKey = d.toISOString().split('T')[0];
      const displayDate = d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
      });

      if (!buckets[dateKey]) {
        buckets[dateKey] = {
          dateKey,
          displayDate,
          total: 0,
          critical: 0,
          high: 0,
          medium: 0,
          low: 0,
        };
      }

      buckets[dateKey].total++;
      const tier = c.risk_tier?.toUpperCase();
      if (tier === 'CRITICAL') buckets[dateKey].critical++;
      else if (tier === 'HIGH') buckets[dateKey].high++;
      else if (tier === 'MEDIUM') buckets[dateKey].medium++;
      else if (tier === 'LOW') buckets[dateKey].low++;
    }

    return Object.values(buckets).sort((a, b) => a.dateKey.localeCompare(b.dateKey));
  }, [cases]);

  const maxBucketCount = useMemo(() => {
    if (activityTimeline.length === 0) return 1;
    return Math.max(...activityTimeline.map(b => b.total), 1);
  }, [activityTimeline]);

  // 4. Priority Cases (CRITICAL first, then HIGH, then newest)
  const priorityCases = useMemo(() => {
    const tierRank: Record<string, number> = {
      CRITICAL: 4,
      HIGH: 3,
      MEDIUM: 2,
      LOW: 1,
    };
    return cases.slice().sort((a, b) => {
      const ra = tierRank[a.risk_tier?.toUpperCase()] || 0;
      const rb = tierRank[b.risk_tier?.toUpperCase()] || 0;
      if (rb !== ra) return rb - ra;
      const ta = new Date(a.created_at).getTime() || 0;
      const tb = new Date(b.created_at).getTime() || 0;
      return tb - ta;
    });
  }, [cases]);

  return (
    <PageContainer title="Fraud Intelligence">
      <div className="space-y-8 max-w-7xl mx-auto">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-800/80">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              Fraud Intelligence Dashboard
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Real-time threat analytics, network behavior, and case investigation signals.
            </p>
          </div>
          <div className="flex items-center gap-3 self-start sm:self-auto">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs text-slate-300 shadow-inner">
              <Activity className="w-3.5 h-3.5 text-primary" />
              <span className="font-medium">Live Case Intelligence</span>
            </div>
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="inline-flex items-center gap-1.5 bg-slate-900 border border-slate-800 hover:bg-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300 disabled:opacity-50 transition-colors shadow-sm"
              title="Refresh dashboard intelligence"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin text-primary' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>

        {/* Global Loading State */}
        {isLoading && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              <MetricCardSkeleton />
              <MetricCardSkeleton />
              <MetricCardSkeleton />
              <MetricCardSkeleton />
              <MetricCardSkeleton />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="h-64 bg-slate-900/60 rounded-xl border border-slate-800 animate-pulse" />
              <div className="h-64 bg-slate-900/60 rounded-xl border border-slate-800 animate-pulse" />
            </div>
            <div className="h-96 bg-slate-900/60 rounded-xl border border-slate-800 animate-pulse flex items-center justify-center text-slate-500 text-sm">
              Loading threat intelligence...
            </div>
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <div className="p-12 text-center bg-slate-900 rounded-xl border border-red-900/40">
            <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white mb-2">Unable to load dashboard intelligence.</h3>
            <p className="text-sm text-red-400 max-w-md mx-auto mb-6">
              {error instanceof Error ? error.message : 'The detection API service could not be reached or returned an authorization error.'}
            </p>
            <button
              onClick={() => refetch()}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium border border-slate-700 transition-colors shadow-sm"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Retry</span>
            </button>
          </div>
        )}

        {/* Loaded Content */}
        {!isLoading && !error && (
          <>
            {/* Overview KPI Metrics (5 Responsive Cards) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              <div className="p-4 bg-slate-900 rounded-xl border border-slate-800 flex items-center gap-4 hover:border-slate-700 transition-colors">
                <div className="w-12 h-12 rounded-lg bg-blue-950/60 border border-blue-900/60 flex items-center justify-center shrink-0">
                  <Shield className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Cases</div>
                  <div className="text-2xl font-bold text-white">{total}</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">Global repository count</div>
                </div>
              </div>

              <div className="p-4 bg-slate-900 rounded-xl border border-slate-800 flex items-center gap-4 hover:border-slate-700 transition-colors">
                <div className="w-12 h-12 rounded-lg bg-red-950/60 border border-red-900/60 flex items-center justify-center shrink-0">
                  <Flame className="w-6 h-6 text-red-400" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Critical</div>
                  <div className="text-2xl font-bold text-red-400">{criticalCount}</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">Critical tier threat alerts</div>
                </div>
              </div>

              <div className="p-4 bg-slate-900 rounded-xl border border-slate-800 flex items-center gap-4 hover:border-slate-700 transition-colors">
                <div className="w-12 h-12 rounded-lg bg-orange-950/60 border border-orange-900/60 flex items-center justify-center shrink-0">
                  <AlertTriangle className="w-6 h-6 text-orange-400" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">High Risk</div>
                  <div className="text-2xl font-bold text-orange-400">{highCount}</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">High severity cases</div>
                </div>
              </div>

              <div className="p-4 bg-slate-900 rounded-xl border border-slate-800 flex items-center gap-4 hover:border-slate-700 transition-colors">
                <div className="w-12 h-12 rounded-lg bg-amber-950/60 border border-amber-900/60 flex items-center justify-center shrink-0">
                  <Activity className="w-6 h-6 text-amber-400" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Open Queue</div>
                  <div className="text-2xl font-bold text-amber-400">{openCount}</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">Awaiting analyst review</div>
                </div>
              </div>

              <div className="p-4 bg-slate-900 rounded-xl border border-slate-800 flex items-center gap-4 hover:border-slate-700 transition-colors">
                <div className="w-12 h-12 rounded-lg bg-emerald-950/60 border border-emerald-900/60 flex items-center justify-center shrink-0">
                  <BarChart3 className="w-6 h-6 text-emerald-400" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Avg Threat</div>
                  <div className="text-2xl font-bold text-emerald-400">{avgScore}%</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">Mean threat index (loaded)</div>
                </div>
              </div>
            </div>

            {/* Empty State vs Active Analytics */}
            {cases.length === 0 ? (
              <div className="p-16 text-center bg-slate-900 rounded-xl border border-slate-800">
                <Shield className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">No investigations yet</h3>
                <p className="text-sm text-slate-400 max-w-md mx-auto">
                  Run the SentinelGraph simulator or process payment events to generate investigation data.
                </p>
              </div>
            ) : (
              <>
                {/* Visual Analytics Grid: Risk Distribution & Detection Trend */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* B. Risk Distribution Panel */}
                  <div className="p-5 bg-slate-900 rounded-xl border border-slate-800 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <PieChart className="w-5 h-5 text-primary" />
                          <h3 className="text-base font-semibold text-white">Risk Tier Distribution</h3>
                        </div>
                        <span className="text-xs text-slate-400 font-mono">
                          {cases.length} cases evaluated
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mb-5">
                        Categorization of active threats based on multi-factor aggregate scoring.
                      </p>

                      {/* Segmented Stacked Distribution Bar */}
                      <div className="w-full h-3 rounded-full bg-slate-800 overflow-hidden flex mb-6">
                        {tierDistribution.percentages.CRITICAL > 0 && (
                          <div
                            style={{ width: `${tierDistribution.percentages.CRITICAL}%` }}
                            className="bg-red-500 transition-all duration-500"
                            title={`Critical: ${tierDistribution.counts.CRITICAL} (${tierDistribution.percentages.CRITICAL}%)`}
                          />
                        )}
                        {tierDistribution.percentages.HIGH > 0 && (
                          <div
                            style={{ width: `${tierDistribution.percentages.HIGH}%` }}
                            className="bg-orange-500 transition-all duration-500"
                            title={`High: ${tierDistribution.counts.HIGH} (${tierDistribution.percentages.HIGH}%)`}
                          />
                        )}
                        {tierDistribution.percentages.MEDIUM > 0 && (
                          <div
                            style={{ width: `${tierDistribution.percentages.MEDIUM}%` }}
                            className="bg-yellow-500 transition-all duration-500"
                            title={`Medium: ${tierDistribution.counts.MEDIUM} (${tierDistribution.percentages.MEDIUM}%)`}
                          />
                        )}
                        {tierDistribution.percentages.LOW > 0 && (
                          <div
                            style={{ width: `${tierDistribution.percentages.LOW}%` }}
                            className="bg-blue-500 transition-all duration-500"
                            title={`Low: ${tierDistribution.counts.LOW} (${tierDistribution.percentages.LOW}%)`}
                          />
                        )}
                      </div>

                      {/* Tier Breakdown Legend */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
                          <div className="flex items-center gap-1.5 mb-1">
                            <span className="w-2 h-2 rounded-full bg-red-500" />
                            <span className="text-xs font-semibold text-red-400 uppercase">Critical</span>
                          </div>
                          <div className="text-lg font-bold text-white">{tierDistribution.counts.CRITICAL}</div>
                          <div className="text-[11px] text-slate-500">{tierDistribution.percentages.CRITICAL}% of total</div>
                        </div>

                        <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
                          <div className="flex items-center gap-1.5 mb-1">
                            <span className="w-2 h-2 rounded-full bg-orange-500" />
                            <span className="text-xs font-semibold text-orange-400 uppercase">High</span>
                          </div>
                          <div className="text-lg font-bold text-white">{tierDistribution.counts.HIGH}</div>
                          <div className="text-[11px] text-slate-500">{tierDistribution.percentages.HIGH}% of total</div>
                        </div>

                        <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
                          <div className="flex items-center gap-1.5 mb-1">
                            <span className="w-2 h-2 rounded-full bg-yellow-500" />
                            <span className="text-xs font-semibold text-yellow-400 uppercase">Medium</span>
                          </div>
                          <div className="text-lg font-bold text-white">{tierDistribution.counts.MEDIUM}</div>
                          <div className="text-[11px] text-slate-500">{tierDistribution.percentages.MEDIUM}% of total</div>
                        </div>

                        <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
                          <div className="flex items-center gap-1.5 mb-1">
                            <span className="w-2 h-2 rounded-full bg-blue-500" />
                            <span className="text-xs font-semibold text-blue-400 uppercase">Low</span>
                          </div>
                          <div className="text-lg font-bold text-white">{tierDistribution.counts.LOW}</div>
                          <div className="text-[11px] text-slate-500">{tierDistribution.percentages.LOW}% of total</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* C. Detection Trend Panel */}
                  <div className="p-5 bg-slate-900 rounded-xl border border-slate-800 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <TrendingUp className="w-5 h-5 text-emerald-400" />
                          <h3 className="text-base font-semibold text-white">Detection Activity Trend</h3>
                        </div>
                        <span className="text-xs text-slate-400">
                          {activityTimeline.length} {activityTimeline.length === 1 ? 'day recorded' : 'days recorded'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mb-5">
                        Volume of automated case detections aggregated by actual occurrence timestamps.
                      </p>

                      {activityTimeline.length === 0 ? (
                        <div className="p-8 text-center bg-slate-950/50 rounded-lg border border-slate-800/80 text-slate-500 text-xs">
                          No detection trend timestamps available.
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {activityTimeline.slice(-5).map(bucket => {
                            const barPct = Math.max(10, Math.round((bucket.total / maxBucketCount) * 100));
                            return (
                              <div key={bucket.dateKey} className="space-y-1">
                                <div className="flex items-center justify-between text-xs">
                                  <span className="text-slate-300 font-medium">{bucket.displayDate}</span>
                                  <div className="flex items-center gap-2">
                                    {bucket.critical > 0 && (
                                      <span className="text-[11px] text-red-400">{bucket.critical} crit</span>
                                    )}
                                    {bucket.high > 0 && (
                                      <span className="text-[11px] text-orange-400">{bucket.high} high</span>
                                    )}
                                    <span className="font-bold text-white font-mono">{bucket.total} cases</span>
                                  </div>
                                </div>
                                <div className="h-2 w-full bg-slate-950 rounded-full overflow-hidden border border-slate-800/80">
                                  <div
                                    style={{ width: `${barPct}%` }}
                                    className="h-full bg-gradient-to-r from-emerald-500 to-primary rounded-full transition-all duration-500"
                                  />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Featured Active Threat Story Centerpiece */}
                {(() => {
                  const featured = selectFeaturedCase(cases);
                  if (!featured) return null;
                  return <FeaturedInvestigationSection featuredCase={featured} />;
                })()}

                {/* D. Recent Critical & Important Cases Section */}
                <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
                  <div className="p-5 border-b border-slate-800 flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-white text-base">Prioritized Triage Queue</h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        High-severity cases ranked by threat tier (CRITICAL then HIGH) and occurrence timestamp.
                      </p>
                    </div>
                    <Link
                      href="/cases"
                      className="text-xs font-medium text-primary hover:text-primary/80 inline-flex items-center gap-1 transition-colors"
                    >
                      <span>View all cases</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead className="bg-slate-950/60 border-b border-slate-800">
                        <tr>
                          <th className="py-3 px-4 font-semibold text-slate-400 text-xs uppercase tracking-wider">Case</th>
                          <th className="py-3 px-4 font-semibold text-slate-400 text-xs uppercase tracking-wider">Entity</th>
                          <th className="py-3 px-4 font-semibold text-slate-400 text-xs uppercase tracking-wider">Risk Tier</th>
                          <th className="py-3 px-4 font-semibold text-slate-400 text-xs uppercase tracking-wider">Score</th>
                          <th className="py-3 px-4 font-semibold text-slate-400 text-xs uppercase tracking-wider">Status</th>
                          <th className="py-3 px-4 font-semibold text-slate-400 text-xs uppercase tracking-wider">Reason</th>
                          <th className="py-3 px-4 font-semibold text-slate-400 text-xs uppercase tracking-wider">Detected</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 text-sm">
                        {priorityCases.slice(0, 5).map(c => {
                          const pct = toPercentage(c.overall_risk_score);
                          return (
                            <tr
                              key={c.case_id}
                              className="hover:bg-slate-800/40 transition-colors group cursor-pointer"
                            >
                              <td className="py-3.5 px-4 font-mono font-medium">
                                <Link
                                  href={`/cases/${c.case_id}`}
                                  className="text-primary hover:underline group-hover:text-primary/90 flex items-center gap-1.5"
                                >
                                  <span>{c.case_id.substring(0, 8)}...</span>
                                </Link>
                              </td>
                              <td className="py-3.5 px-4 text-xs font-mono text-slate-300 truncate max-w-[140px]" title={c.primary_entity_id}>
                                {c.primary_entity_id}
                              </td>
                              <td className="py-3.5 px-4">
                                <span className={`inline-block text-xs font-bold px-2 py-0.5 rounded border ${getRiskBadgeClasses(c.risk_tier)}`}>
                                  {c.risk_tier}
                                </span>
                              </td>
                              <td className="py-3.5 px-4 font-bold text-slate-200">
                                {pct}%
                              </td>
                              <td className="py-3.5 px-4">
                                <span className="px-2 py-0.5 text-xs rounded bg-slate-800 text-slate-300 font-medium border border-slate-700 uppercase">
                                  {c.status}
                                </span>
                              </td>
                              <td className="py-3.5 px-4 text-slate-300 text-xs max-w-xs truncate" title={c.case_reason}>
                                {c.case_reason || 'N/A'}
                              </td>
                              <td className="py-3.5 px-4 text-slate-400 text-xs whitespace-nowrap">
                                {formatDate(c.created_at)}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  <div className="p-3 bg-slate-950/40 border-t border-slate-800 text-center">
                    <Link
                      href="/cases"
                      className="text-xs text-slate-400 hover:text-white transition-colors"
                    >
                      Showing top {Math.min(5, priorityCases.length)} of {cases.length} cases â€¢ Click any case to open full triage view
                    </Link>
                  </div>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </PageContainer>
  );
}
