'use client';

import React from 'react';
import Link from 'next/link';
import { useEntityResolution } from '@/lib/hooks/use-cases';
import { formatDate, getRiskTierColor } from '@/lib/utils';
import {
  Fingerprint,
  Smartphone,
  CreditCard,
  Globe,
  ShoppingBag,
  ArrowRight,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Layers,
  Users,
  ExternalLink,
  Share2,
  RefreshCw,
  Info,
  CheckCircle2,
} from 'lucide-react';

interface EntityResolutionPanelProps {
  caseId: string;
  onNavigateToGraph?: () => void;
}

export default function EntityResolutionPanel({
  caseId,
  onNavigateToGraph,
}: EntityResolutionPanelProps) {
  const { data, isLoading, isError, error, refetch, isFetching } = useEntityResolution(caseId);

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-24 bg-slate-900/60 rounded-lg border border-slate-800" />
        <div className="h-48 bg-slate-900/60 rounded-lg border border-slate-800" />
        <div className="h-32 bg-slate-900/60 rounded-lg border border-slate-800" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="bg-red-950/20 border border-red-900/40 rounded-lg p-6 text-center space-y-3">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto" />
        <h4 className="text-sm font-semibold text-red-200">Unable to Load Entity Resolution</h4>
        <p className="text-xs text-red-400/80 max-w-md mx-auto">
          {error instanceof Error ? error.message : 'An error occurred while resolving case identity entities.'}
        </p>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          Retry
        </button>
      </div>
    );
  }

  const { canonical_entity, resolved_identifiers, correlated_cases, summary, resolution_strategy, confidence_model } = data;
  const suspiciousCount = resolved_identifiers.filter((i) => i.status === 'SUSPICIOUS_SHARED').length;

  const getIdentifierIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'device':
        return <Smartphone className="w-4 h-4 text-emerald-400" />;
      case 'payment_instrument':
      case 'instrument':
        return <CreditCard className="w-4 h-4 text-purple-400" />;
      case 'ip_address':
      case 'ip':
        return <Globe className="w-4 h-4 text-cyan-400" />;
      case 'merchant':
        return <ShoppingBag className="w-4 h-4 text-amber-400" />;
      default:
        return <Fingerprint className="w-4 h-4 text-blue-400" />;
    }
  };

  return (
    <div className="space-y-6 text-xs text-slate-300">
      {/* 1. Header Banner & Summary */}
      <div className={`p-4 rounded-lg border ${
        suspiciousCount > 0
          ? 'bg-amber-950/20 border-amber-800/40'
          : 'bg-slate-900/60 border-slate-800'
      }`}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            {suspiciousCount > 0 ? (
              <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            ) : (
              <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            )}
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-semibold text-white">Identity Resolution Intelligence</h4>
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold tracking-wider uppercase border ${
                  suspiciousCount > 0
                    ? 'bg-amber-900/30 text-amber-300 border-amber-700/50'
                    : 'bg-emerald-900/30 text-emerald-300 border-emerald-700/50'
                }`}>
                  {suspiciousCount > 0 ? `${suspiciousCount} Shared Hubs Detected` : 'Ground Truth Match'}
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-1 leading-relaxed">{summary}</p>
            </div>
          </div>
          {onNavigateToGraph && (
            <button
              onClick={onNavigateToGraph}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 rounded text-xs font-medium transition-colors shrink-0"
              title="Inspect in Abuse Graph"
            >
              <Share2 className="w-3.5 h-3.5" />
              <span>View in Graph</span>
            </button>
          )}
        </div>
      </div>

      {/* 2. Canonical Resolved Entity Card */}
      <div className="bg-slate-900/80 rounded-lg border border-slate-800 p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-blue-400" />
            <span className="font-semibold text-slate-200">Canonical Entity Profile</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-950/60 text-blue-300 border border-blue-800/40 uppercase">
              {canonical_entity.entity_type}
            </span>
          </div>
          <div className="text-[11px] text-slate-400 font-mono">
            Status: <span className="text-emerald-400 font-medium capitalize">{canonical_entity.status}</span>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
          <div className="bg-slate-950/50 p-2.5 rounded border border-slate-800/60">
            <span className="text-slate-500 text-[10px] block mb-0.5 uppercase tracking-wider">Canonical ID</span>
            <span className="font-mono text-slate-200 truncate block select-all text-[11px]" title={canonical_entity.canonical_id}>
              {canonical_entity.canonical_id}
            </span>
          </div>
          <div className="bg-slate-950/50 p-2.5 rounded border border-slate-800/60">
            <span className="text-slate-500 text-[10px] block mb-0.5 uppercase tracking-wider">Origin Country</span>
            <span className="font-semibold text-slate-200 text-xs">
              {canonical_entity.country || 'Unknown'}
            </span>
          </div>
          <div className="bg-slate-950/50 p-2.5 rounded border border-slate-800/60">
            <span className="text-slate-500 text-[10px] block mb-0.5 uppercase tracking-wider">Total Transactions</span>
            <span className="font-semibold text-slate-200 text-xs">
              {canonical_entity.total_transactions} txs
            </span>
          </div>
          <div className="bg-slate-950/50 p-2.5 rounded border border-slate-800/60">
            <span className="text-slate-500 text-[10px] block mb-0.5 uppercase tracking-wider">Identity Footprint</span>
            <div className="flex items-center gap-2 text-slate-300 text-[11px] font-mono">
              <span title="Devices">{canonical_entity.correlated_devices_count} devs</span>
              <span>•</span>
              <span title="Instruments">{canonical_entity.correlated_instruments_count} cards</span>
              <span>•</span>
              <span title="IP Addresses">{canonical_entity.correlated_ips_count} IPs</span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Identifier-to-Entity Resolution Mapping */}
      <div className="bg-slate-900/80 rounded-lg border border-slate-800 overflow-hidden">
        <div className="p-3.5 border-b border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-emerald-400" />
            <h5 className="font-semibold text-slate-200 text-xs">Case Identifier Resolution Mapping</h5>
          </div>
          <span className="text-slate-500 text-[11px]">
            {resolved_identifiers.length} identifiers mapped
          </span>
        </div>

        <div className="divide-y divide-slate-800/60">
          {resolved_identifiers.map((item, idx) => {
            const isShared = item.status === 'SUSPICIOUS_SHARED';
            return (
              <div
                key={`${item.identifier_type}-${item.identifier_value}-${idx}`}
                className={`p-3.5 hover:bg-slate-800/40 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3 ${
                  isShared ? 'bg-amber-950/10' : ''
                }`}
              >
                <div className="flex items-start gap-3 min-w-0 flex-1">
                  <div className="p-2 rounded bg-slate-950 border border-slate-800 shrink-0 mt-0.5">
                    {getIdentifierIcon(item.identifier_type)}
                  </div>
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-slate-400 capitalize font-medium">
                        {item.role.replace(/_/g, ' ')}
                      </span>
                      <span className="text-slate-600 font-mono">•</span>
                      <code className="text-slate-200 font-mono text-[11px] bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800/80 truncate max-w-[280px] select-all" title={item.identifier_value}>
                        {item.identifier_value}
                      </code>
                      <span className={`px-2 py-0.2 rounded text-[10px] font-mono uppercase font-semibold border ${
                        isShared
                          ? 'bg-red-950/40 text-red-300 border-red-800/60'
                          : 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60'
                      }`}>
                        {item.status}
                      </span>
                    </div>

                    {/* Metadata attributes */}
                    <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400">
                      <span>Method: <span className="text-slate-300 font-mono">{item.resolution_method}</span></span>
                      <span>Confidence: <span className="text-emerald-400 font-mono font-semibold">100% (1.0)</span></span>
                      {Object.entries(item.details).map(([k, v]) => (
                        <span key={k} className="text-slate-400">
                          {k.replace(/_/g, ' ')}: <span className="text-slate-200 font-mono">{String(v)}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Right side: Shared customer count indicator */}
                <div className="flex items-center gap-3 shrink-0 self-end md:self-center">
                  {isShared ? (
                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-red-950/50 border border-red-800/60 text-red-300 text-[11px] font-medium" title="Cross-account entity collision detected">
                      <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                      <span>Used by {item.shared_with_customers_count} accounts</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1 text-slate-500 text-[11px]">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                      <span>Exclusive to Customer</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. Multi-Case Identity Correlation Card */}
      {correlated_cases && correlated_cases.length > 0 && (
        <div className="bg-slate-900/80 rounded-lg border border-slate-800 p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
            <div className="flex items-center gap-2">
              <Share2 className="w-4 h-4 text-purple-400" />
              <h5 className="font-semibold text-slate-200 text-xs">
                Correlated Cases for this Canonical Entity ({correlated_cases.length})
              </h5>
            </div>
            <span className="text-slate-500 text-[11px]">Same underlying customer</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
            {correlated_cases.map((c) => {
              const isCurrent = c.case_id === caseId;
              return (
                <div
                  key={c.case_id}
                  className={`p-2.5 rounded border transition-colors ${
                    isCurrent
                      ? 'bg-primary/10 border-primary/40'
                      : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono text-slate-300 text-[11px] truncate" title={c.case_id}>
                      {c.case_id.substring(0, 8)}... {isCurrent && '(This Case)'}
                    </span>
                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${getRiskTierColor(c.risk_tier)}`}>
                      {c.risk_tier}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span>Score: <span className="font-mono text-slate-200">{c.overall_risk_score.toFixed(2)}</span></span>
                    <span className="capitalize">{c.status}</span>
                  </div>
                  {!isCurrent && (
                    <Link
                      href={`/cases/${c.case_id}`}
                      className="inline-flex items-center gap-1 text-[10px] text-primary hover:text-primary/80 mt-2 font-medium"
                    >
                      <span>Open Case</span>
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 5. Governance & Provenance Disclosure */}
      <div className="p-3 bg-slate-950/40 rounded border border-slate-800/60 flex items-start gap-2.5 text-[11px] text-slate-400">
        <Info className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <div className="text-slate-300 font-medium">
            Resolution Model: <span className="font-mono text-slate-200">{resolution_strategy}</span> ({confidence_model})
          </div>
          <p className="text-slate-500 text-[10px] leading-relaxed">
            SentinelGraph resolves identifiers deterministically from direct payment events, SHA-256 IP telemetry, and hardware device fingerprints. In accordance with enterprise auditability, all confidence scores reflect verified ground truth linkages without probabilistic imputation.
          </p>
        </div>
      </div>
    </div>
  );
}
