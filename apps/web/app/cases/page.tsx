'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useCases } from '@/lib/hooks/use-cases';
import PageContainer from '@/components/layout/PageContainer';
import { formatRiskScore, getRiskTierColor, formatDate } from '@/lib/utils';
import {
  AlertCircle,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Filter,
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

export default function CasesPage() {
  const [statusFilter, setStatusFilter] = useState('All');
  const [tierFilter, setTierFilter] = useState('All');
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);

  const {
    data: response,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useCases({
    status: statusFilter === 'All' ? undefined : statusFilter.toLowerCase(),
    risk_tier: tierFilter === 'All' ? undefined : tierFilter.toUpperCase(),
    page,
    limit,
  });

  const cases = response?.items || [];
  const total = response?.total || 0;
  const totalPages = Math.max(1, response?.pages || Math.ceil(total / limit) || 1);

  // Safety clamp if page exceeds totalPages due to filtering or deletions
  useEffect(() => {
    if (response?.pages && page > response.pages) {
      setPage(Math.max(1, response.pages));
    }
  }, [response?.pages, page]);

  const startItem = total === 0 ? 0 : (page - 1) * limit + 1;
  const endItem = Math.min(page * limit, total);
  const hasActiveFilters = statusFilter !== 'All' || tierFilter !== 'All';

  const resetFilters = () => {
    setStatusFilter('All');
    setTierFilter('All');
    setPage(1);
  };

  return (
    <PageContainer title="Cases">
      {/* Filters and Actions Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-slate-400" />
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Filters:
            </span>
          </div>

          <select
            aria-label="Filter by status"
            className="bg-slate-900 border border-slate-800 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-slate-700"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
          >
            <option value="All">All Statuses</option>
            <option value="open">Open</option>
            <option value="escalated">Escalated</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>

          <select
            aria-label="Filter by risk tier"
            className="bg-slate-900 border border-slate-800 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-slate-700"
            value={tierFilter}
            onChange={(e) => {
              setTierFilter(e.target.value);
              setPage(1);
            }}
          >
            <option value="All">All Risk Tiers</option>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
            <option value="CRITICAL">Critical</option>
          </select>

          {hasActiveFilters && (
            <button
              onClick={resetFilters}
              className="text-xs text-slate-400 hover:text-slate-200 underline px-1"
            >
              Clear filters
            </button>
          )}
        </div>

        <div className="flex items-center gap-3">
          <select
            aria-label="Rows per page"
            className="bg-slate-900 border border-slate-800 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-slate-700"
            value={limit}
            onChange={(e) => {
              setLimit(Number(e.target.value));
              setPage(1);
            }}
          >
            <option value={10}>10 per page</option>
            <option value={20}>20 per page</option>
            <option value={50}>50 per page</option>
          </select>

          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-1.5 bg-slate-900 border border-slate-800 hover:bg-slate-800 rounded px-3 py-2 text-sm text-slate-300 disabled:opacity-50 transition-colors"
            title="Refresh cases"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin text-primary' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      {/* 1. API Error State */}
      {isError && (
        <div className="rounded-lg border border-red-900/50 bg-red-950/20 p-8 text-center my-4">
          <AlertCircle className="mx-auto h-10 w-10 text-red-500 mb-3" />
          <h3 className="text-lg font-semibold text-red-200 mb-1">Failed to Load Cases</h3>
          <p className="text-sm text-red-400 max-w-md mx-auto mb-4">
            {error instanceof Error ? error.message : 'An unexpected error occurred while fetching cases from the server.'}
          </p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-md transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </button>
        </div>
      )}

      {/* 2. Loading State */}
      {isLoading && (
        <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-slate-950/60 border-b border-slate-800">
                <tr>
                  <th className="p-4 font-medium text-slate-400 text-xs uppercase tracking-wider">Case ID</th>
                  <th className="p-4 font-medium text-slate-400 text-xs uppercase tracking-wider">Entity</th>
                  <th className="p-4 font-medium text-slate-400 text-xs uppercase tracking-wider">Risk Tier</th>
                  <th className="p-4 font-medium text-slate-400 text-xs uppercase tracking-wider">Overall Score</th>
                  <th className="p-4 font-medium text-slate-400 text-xs uppercase tracking-wider">Status</th>
                  <th className="p-4 font-medium text-slate-400 text-xs uppercase tracking-wider">Reason</th>
                  <th className="p-4 font-medium text-slate-400 text-xs uppercase tracking-wider">Created At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {[...Array(Math.min(limit, 5))].map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="p-4"><div className="h-4 bg-slate-800 rounded w-20" /></td>
                    <td className="p-4"><div className="h-4 bg-slate-800 rounded w-28" /></td>
                    <td className="p-4"><div className="h-4 bg-slate-800 rounded w-16" /></td>
                    <td className="p-4"><div className="h-4 bg-slate-800 rounded w-24" /></td>
                    <td className="p-4"><div className="h-4 bg-slate-800 rounded w-14" /></td>
                    <td className="p-4"><div className="h-4 bg-slate-800 rounded w-44" /></td>
                    <td className="p-4"><div className="h-4 bg-slate-800 rounded w-28" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 3. Empty Result State */}
      {!isLoading && !isError && cases.length === 0 && (
        <div className="text-center p-12 bg-slate-900 rounded-lg border border-slate-800 text-slate-400 my-4">
          <p className="text-base font-medium text-slate-300 mb-1">No cases found</p>
          <p className="text-sm text-slate-500 mb-4">
            {hasActiveFilters
              ? 'No cases match your active filter criteria. Try adjusting or clearing your filters.'
              : 'No cases currently exist. Run the simulator to generate fraud events and trigger risk cases.'}
          </p>
          {hasActiveFilters && (
            <button
              onClick={resetFilters}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded transition-colors"
            >
              Reset Filters
            </button>
          )}
        </div>
      )}

      {/* 4. Normal Case List State */}
      {!isLoading && !isError && cases.length > 0 && (
        <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-slate-950/60 border-b border-slate-800">
                <tr>
                  <th className="p-4 font-medium text-slate-400 text-xs uppercase tracking-wider">Case ID</th>
                  <th className="p-4 font-medium text-slate-400 text-xs uppercase tracking-wider">Entity</th>
                  <th className="p-4 font-medium text-slate-400 text-xs uppercase tracking-wider">Risk Tier</th>
                  <th className="p-4 font-medium text-slate-400 text-xs uppercase tracking-wider">Overall Score</th>
                  <th className="p-4 font-medium text-slate-400 text-xs uppercase tracking-wider">Status</th>
                  <th className="p-4 font-medium text-slate-400 text-xs uppercase tracking-wider">Reason</th>
                  <th className="p-4 font-medium text-slate-400 text-xs uppercase tracking-wider">Created At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {cases.map((c) => (
                  <tr key={c.case_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="p-4 text-sm font-mono">
                      <Link
                        href={`/cases/${c.case_id}`}
                        className="text-primary hover:underline font-medium"
                      >
                        {c.case_id.substring(0, 8)}...
                      </Link>
                    </td>
                    <td className="p-4 text-sm text-slate-300 font-mono truncate max-w-[180px]" title={c.primary_entity_id}>
                      {c.primary_entity_id}
                    </td>
                    <td className={`p-4 text-sm font-semibold ${getRiskTierColor(c.risk_tier)}`}>
                      {c.risk_tier}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2 min-w-[120px]">
                        <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary rounded-full transition-all"
                            style={{ width: `${Math.min(100, Math.max(0, c.overall_risk_score * 100))}%` }}
                          />
                        </div>
                        <span className="text-xs font-mono text-slate-300 min-w-[32px] text-right">
                          {formatRiskScore(c.overall_risk_score)}
                        </span>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border uppercase tracking-wider ${getStatusBadgeClass(c.status)}`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="p-4 text-sm text-slate-300 max-w-[240px] truncate" title={c.case_reason}>
                      {c.case_reason}
                    </td>
                    <td className="p-4 text-slate-400 text-xs whitespace-nowrap">
                      {formatDate(c.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 border-t border-slate-800 text-sm text-slate-400 bg-slate-950/30">
            <div className="text-xs text-slate-400">
              Showing <span className="font-medium text-slate-200">{startItem}</span> to{' '}
              <span className="font-medium text-slate-200">{endItem}</span> of{' '}
              <span className="font-medium text-slate-200">{total}</span> cases
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1 || isFetching}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded border border-slate-800 bg-slate-900 text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                aria-label="Previous page"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                Previous
              </button>
              <span className="text-xs text-slate-400 px-2">
                Page <span className="font-medium text-slate-200">{page}</span> of{' '}
                <span className="font-medium text-slate-200">{totalPages}</span>
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages || isFetching}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded border border-slate-800 bg-slate-900 text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                aria-label="Next page"
              >
                Next
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </PageContainer>
  );
}
