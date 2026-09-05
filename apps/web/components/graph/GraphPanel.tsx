'use client';

import React, { useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { useEntityNeighbors } from '@/lib/hooks/use-graph';
import {
  AlertTriangle,
  Loader2,
  RefreshCw,
  Network,
  Share2,
  SlidersHorizontal,
  X,
  Copy,
  Check,
  ShieldAlert,
  User,
  Receipt,
  Smartphone,
  Globe,
  CreditCard,
  Store,
  Info,
} from 'lucide-react';

const NetworkGraph = dynamic(() => import('./NetworkGraph'), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-slate-950 text-slate-400 text-sm gap-2">
      <Loader2 className="w-4 h-4 animate-spin text-primary" />
      <span>Loading network intelligence...</span>
    </div>
  ),
});

export interface GraphPanelProps {
  entityType: string;
  entityId: string;
  depth?: number;
  limit?: number;
  caseRiskScore?: number;
  caseRiskTier?: string;
  networkRiskScore?: number;
}

const FILTER_TYPES = [
  { label: 'All Entities', value: 'ALL' },
  { label: 'Devices', value: 'Device' },
  { label: 'IPs', value: 'IPAddress' },
  { label: 'Cards', value: 'PaymentInstrument' },
  { label: 'Transactions', value: 'Transaction' },
  { label: 'Customers', value: 'Customer' },
  { label: 'Merchants', value: 'Merchant' },
];

function normalizeType(type?: string): string {
  if (!type) return 'Customer';
  const lower = type.toLowerCase().replace(/[_\s-]/g, '');
  if (lower.includes('transaction') || lower.includes('tx')) return 'Transaction';
  if (lower.includes('customer') || lower.includes('user')) return 'Customer';
  if (lower.includes('device')) return 'Device';
  if (lower.includes('ip')) return 'IPAddress';
  if (lower.includes('instrument') || lower.includes('card') || lower.includes('payment'))
    return 'PaymentInstrument';
  if (lower.includes('merchant') || lower.includes('store')) return 'Merchant';
  return 'Customer';
}

export default function GraphPanel({
  entityType,
  entityId,
  depth: initialDepth = 1,
  limit: initialLimit = 50,
  caseRiskScore,
  caseRiskTier,
  networkRiskScore,
}: GraphPanelProps) {
  const [depth, setDepth] = useState<number>(initialDepth);
  const [limit, setLimit] = useState<number>(initialLimit);
  const [filterType, setFilterType] = useState<string>('ALL');
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [copiedId, setCopiedId] = useState(false);
  const [showLegend, setShowLegend] = useState(true);

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useEntityNeighbors(entityType, entityId, depth, limit);

  const allNodes = useMemo(() => data?.neighbors || [], [data?.neighbors]);
  const allEdges = useMemo(() => data?.edges || [], [data?.edges]);

  // Apply entity type filter while always preserving the primary entity node
  const { filteredNodes, filteredEdges } = useMemo(() => {
    if (filterType === 'ALL') {
      return { filteredNodes: allNodes, filteredEdges: allEdges };
    }

    const matchingNodes = allNodes.filter(
      n => normalizeType(n.type) === filterType || String(n.id) === String(entityId)
    );
    const validIds = new Set(matchingNodes.map(n => String(n.id)));
    const matchingEdges = allEdges.filter(
      e => validIds.has(String(e.source)) && validIds.has(String(e.target))
    );

    return { filteredNodes: matchingNodes, filteredEdges: matchingEdges };
  }, [allNodes, allEdges, filterType, entityId]);

  // Copy entity ID to clipboard
  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  // Format network risk score nicely (0.00 to 1.00)
  const formattedNetworkRisk = useMemo(() => {
    if (networkRiskScore != null && !isNaN(networkRiskScore)) {
      const val = networkRiskScore > 1 ? networkRiskScore / 100 : networkRiskScore;
      return val.toFixed(2);
    }
    return undefined;
  }, [networkRiskScore]);

  // Loading State
  if (isLoading) {
    return (
      <div className="flex flex-col h-full w-full items-center justify-center bg-slate-950 text-slate-400 p-6 gap-3">
        <div className="relative flex items-center justify-center">
          <Network className="w-10 h-10 text-primary/40 animate-pulse" />
          <Loader2 className="w-6 h-6 animate-spin text-primary absolute" />
        </div>
        <span className="text-sm font-medium text-slate-300">Loading network intelligence...</span>
        <span className="text-xs text-slate-500">Traversing Neo4j relationship graph...</span>
      </div>
    );
  }

  // Error State
  if (isError) {
    return (
      <div className="flex flex-col h-full w-full items-center justify-center bg-slate-950 text-slate-400 p-6 text-center">
        <div className="w-12 h-12 rounded-full bg-red-950/60 border border-red-900/60 flex items-center justify-center mb-3">
          <AlertTriangle className="w-6 h-6 text-red-500" />
        </div>
        <h3 className="text-sm font-semibold text-white mb-1">Unable to load network intelligence.</h3>
        <p className="text-xs text-red-400 max-w-sm mb-4">
          {error instanceof Error
            ? error.message
            : 'The graph service could not retrieve connected entities for this case.'}
        </p>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin text-primary' : ''}`} />
          <span>Retry Graph Query</span>
        </button>
      </div>
    );
  }

  return (
    <div className="w-full h-full relative bg-slate-950 flex flex-col overflow-hidden">
      {/* Degraded Fallback Banner */}
      {data?.degraded && (
        <div className="bg-yellow-950/80 border-b border-yellow-800/80 text-yellow-400 px-4 py-1.5 text-xs flex items-center justify-between z-20 shrink-0">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-yellow-500 shrink-0" />
            <span className="font-medium">
              PostgreSQL fallback mode: Neo4j is temporarily unreachable. Displaying local relational links.
            </span>
          </div>
          <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-yellow-900/60 border border-yellow-700/60">
            Degraded
          </span>
        </div>
      )}

      {/* Network Intelligence Summary Bar & Controls Toolbar */}
      <div className="bg-slate-900/90 border-b border-slate-800/80 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 z-10 shrink-0 text-xs">
        {/* Left: Summary Metrics */}
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-bold text-white tracking-tight uppercase text-[11px]">
              Network Intelligence
            </span>
          </div>

          <div className="flex items-center gap-3 text-slate-400">
            <div className="flex items-center gap-1 font-mono">
              <span className="text-slate-500 font-sans">Nodes:</span>
              <span className="text-white font-semibold">{filteredNodes.length}</span>
              {filterType !== 'ALL' && (
                <span className="text-[10px] text-slate-500">({allNodes.length})</span>
              )}
            </div>

            <span className="text-slate-700">â€¢</span>

            <div className="flex items-center gap-1 font-mono">
              <span className="text-slate-500 font-sans">Edges:</span>
              <span className="text-white font-semibold">{filteredEdges.length}</span>
            </div>

            {formattedNetworkRisk && (
              <>
                <span className="text-slate-700">â€¢</span>
                <div className="flex items-center gap-1 font-mono">
                  <span className="text-slate-500 font-sans">Network Risk:</span>
                  <span className={`font-semibold ${Number(formattedNetworkRisk) > 0.5 ? 'text-red-400' : 'text-slate-200'}`}>
                    {formattedNetworkRisk}
                  </span>
                </div>
              </>
            )}

            <span className="text-slate-700 hidden sm:inline">â€¢</span>

            {/* Live Data Source Indicator */}
            <div className="hidden sm:flex items-center gap-1 text-[11px]">
              <span className="text-slate-500">Source:</span>
              <span className={`font-medium ${data?.degraded ? 'text-amber-400' : 'text-emerald-400'}`}>
                {data?.degraded ? 'PostgreSQL Fallback' : 'Neo4j Live'}
              </span>
            </div>
          </div>
        </div>

        {/* Right: Controls (Depth, Limit, Filter, Refresh) */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Depth Selector (1, 2, 3 Hops) */}
          <div className="inline-flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5">
            <button
              onClick={() => setDepth(1)}
              className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                depth === 1
                  ? 'bg-slate-800 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="1 Hop: Direct connections only"
            >
              1 Hop
            </button>
            <button
              onClick={() => setDepth(2)}
              className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                depth === 2
                  ? 'bg-slate-800 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="2 Hops: Extended network topology"
            >
              2 Hops
            </button>
            <button
              onClick={() => setDepth(3)}
              className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                depth === 3
                  ? 'bg-slate-800 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="3 Hops: Full cluster depth"
            >
              3 Hops
            </button>
          </div>

          {/* Node Limit Selector */}
          <select
            value={limit}
            onChange={e => setLimit(Number(e.target.value))}
            className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-[11px] text-slate-300 focus:outline-none focus:border-slate-700"
            title="Max nodes limit"
          >
            <option value={25}>Limit 25</option>
            <option value={50}>Limit 50</option>
            <option value={100}>Limit 100</option>
          </select>

          {/* Filter Type Dropdown */}
          <select
            value={filterType}
            onChange={e => setFilterType(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-[11px] text-slate-300 focus:outline-none focus:border-slate-700"
            title="Filter visible entity types"
          >
            {FILTER_TYPES.map(ft => (
              <option key={ft.value} value={ft.value}>
                {ft.label}
              </option>
            ))}
          </select>

          {/* Refresh Graph Button */}
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors disabled:opacity-50"
            title="Refresh graph data"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin text-primary' : ''}`} />
          </button>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="flex-1 relative w-full h-full overflow-hidden">
        {filteredNodes.length === 0 ? (
          <div className="w-full h-full flex flex-col items-center justify-center bg-slate-950 text-slate-500 text-sm p-6 text-center">
            <span>No connected entities found for this case.</span>
          </div>
        ) : (
          <NetworkGraph
            nodes={filteredNodes}
            edges={filteredEdges}
            primaryEntityId={entityId}
            primaryEntityType={entityType}
            caseRiskScore={caseRiskScore}
            caseRiskTier={caseRiskTier}
            networkRiskScore={networkRiskScore}
            onSelectNode={setSelectedNode}
            selectedNodeId={selectedNode?.id}
          />
        )}

        {/* Selected Entity Inspector Floating Sheet */}
        {selectedNode && (
          <div className="absolute top-4 right-4 z-20 w-80 bg-slate-900/95 border border-slate-800 rounded-xl shadow-2xl p-4 backdrop-blur-sm text-xs">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-white uppercase text-[11px] tracking-wider">
                  Entity Inspector
                </span>
                {String(selectedNode.id) === String(entityId) && (
                  <span className="bg-blue-950 text-blue-400 border border-blue-800 text-[9px] font-bold px-1.5 py-0.5 rounded">
                    Primary
                  </span>
                )}
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition-colors"
                title="Close inspector"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="py-3 space-y-2.5">
              <div>
                <span className="text-slate-500 text-[10px] block uppercase font-medium">Entity Type</span>
                <span className="text-white font-semibold text-xs capitalize">{selectedNode.type}</span>
              </div>

              <div>
                <span className="text-slate-500 text-[10px] block uppercase font-medium">Entity ID</span>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="font-mono text-slate-300 text-[11px] truncate flex-1" title={selectedNode.id}>
                    {selectedNode.id}
                  </span>
                  <button
                    onClick={() => handleCopyId(selectedNode.id)}
                    className="text-slate-400 hover:text-white p-1 rounded bg-slate-950 border border-slate-800"
                    title="Copy ID"
                  >
                    {copiedId ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  </button>
                </div>
              </div>

              {selectedNode.properties?.amount != null && (
                <div>
                  <span className="text-slate-500 text-[10px] block uppercase font-medium">Transaction Amount</span>
                  <span className="text-emerald-400 font-bold text-sm">
                    ${Number(selectedNode.properties.amount).toFixed(2)}
                  </span>
                </div>
              )}

              {selectedNode.properties?.occurred_at && (
                <div>
                  <span className="text-slate-500 text-[10px] block uppercase font-medium">Occurred At</span>
                  <span className="text-slate-300 font-mono text-[11px]">
                    {new Date(selectedNode.properties.occurred_at).toLocaleString()}
                  </span>
                </div>
              )}

              {selectedNode.properties?.updated_at && (
                <div>
                  <span className="text-slate-500 text-[10px] block uppercase font-medium">Last Updated</span>
                  <span className="text-slate-300 font-mono text-[11px]">
                    {new Date(selectedNode.properties.updated_at).toLocaleString()}
                  </span>
                </div>
              )}

              {/* Connected edges summary */}
              <div>
                <span className="text-slate-500 text-[10px] block uppercase font-medium">
                  Incident Relationships
                </span>
                <div className="max-h-32 overflow-y-auto space-y-1 mt-1">
                  {allEdges
                    .filter(
                      e => String(e.source) === String(selectedNode.id) || String(e.target) === String(selectedNode.id)
                    )
                    .map((e, idx) => {
                      const isSource = String(e.source) === String(selectedNode.id);
                      const otherId = isSource ? String(e.target) : String(e.source);
                      return (
                        <div
                          key={idx}
                          className="p-1.5 rounded bg-slate-950 border border-slate-800/80 flex items-center justify-between text-[11px]"
                        >
                          <span className="font-mono text-purple-400 font-semibold">{e.type}</span>
                          <span className="font-mono text-slate-400 truncate max-w-[140px]" title={otherId}>
                            {otherId.substring(0, 8)}...
                          </span>
                        </div>
                      );
                    })}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Legend Drawer / Toggle Bar */}
        <div className="absolute bottom-3 left-3 z-10 flex flex-col items-start gap-1">
          {showLegend ? (
            <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-2.5 shadow-xl backdrop-blur-sm flex flex-col gap-1.5 text-[11px]">
              <div className="flex items-center justify-between gap-4 pb-1 border-b border-slate-800">
                <span className="font-semibold text-slate-400 text-[10px] uppercase tracking-wider">
                  Graph Legend
                </span>
                <button
                  onClick={() => setShowLegend(false)}
                  className="text-slate-500 hover:text-slate-300 text-[10px]"
                >
                  Hide
                </button>
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-500 ring-2 ring-blue-500/30" />
                  <span className="text-slate-300">Primary Entity</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-400" />
                  <span className="text-slate-300">Customer</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                  <span className="text-slate-300">Transaction</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-purple-400" />
                  <span className="text-slate-300">Device</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
                  <span className="text-slate-300">IP Address</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                  <span className="text-slate-300">Card / Instrument</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-400" />
                  <span className="text-slate-300">Merchant</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
                  <span className="text-slate-300">Shared Hub</span>
                </div>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowLegend(true)}
              className="bg-slate-900/90 border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-white px-2 py-1 rounded text-[10px] font-medium shadow"
            >
              Show Legend
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
