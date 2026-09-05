'use client';

import { useState, useEffect, useMemo } from 'react';
import PageContainer from '@/components/layout/PageContainer';
import GraphPanel from '@/components/graph/GraphPanel';
import { useCases } from '@/lib/hooks/use-cases';
import { Network, Search, Filter } from 'lucide-react';

const ENTITY_TYPES = [
  { label: 'Customer', value: 'customer' },
  { label: 'Device', value: 'device' },
  { label: 'IP Address', value: 'ip_address' },
  { label: 'Payment Instrument', value: 'payment_instrument' },
  { label: 'Merchant', value: 'merchant' },
];

export default function GraphExplorerPage() {
  const { data: casesResponse } = useCases({ limit: 10 });
  const cases = useMemo(() => casesResponse?.items || [], [casesResponse?.items]);

  const [selectedType, setSelectedType] = useState<string>('customer');
  const [selectedId, setSelectedId] = useState<string>('');
  const [inputQuery, setInputQuery] = useState<string>('');
  const [depth, setDepth] = useState<number>(1);
  const [limit, setLimit] = useState<number>(25);

  // Default to the first available entity from real cases once loaded if none is selected yet
  useEffect(() => {
    if (!selectedId && cases.length > 0) {
      const first = cases[0];
      setSelectedType(first.primary_entity_type || 'customer');
      setSelectedId(first.primary_entity_id);
      setInputQuery(first.primary_entity_id);
    }
  }, [cases, selectedId]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputQuery.trim()) {
      setSelectedId(inputQuery.trim());
    }
  };

  const handleSelectCaseEntity = (type: string, id: string) => {
    setSelectedType(type);
    setSelectedId(id);
    setInputQuery(id);
  };

  return (
    <PageContainer title="Graph Explorer">
      <div className="flex flex-col h-[calc(100vh-8.5rem)] space-y-4">
        {/* Controls & Search Bar */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-3 items-stretch md:items-center">
            {/* Entity Type Selector */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 shrink-0">Type:</span>
              <select
                value={selectedType}
                onChange={e => setSelectedType(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary"
              >
                {ENTITY_TYPES.map(t => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Entity ID Search Input */}
            <div className="flex-1 relative">
              <input
                type="text"
                value={inputQuery}
                onChange={e => setInputQuery(e.target.value)}
                placeholder="Enter entity ID (e.g. customer UUID, device hash, IP)..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-primary pr-10 font-mono"
              />
              <button
                type="submit"
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
                title="Search entity"
              >
                <Search className="w-4 h-4" />
              </button>
            </div>

            {/* Depth & Limit Selectors */}
            <div className="flex items-center gap-3 shrink-0">
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-slate-400">Depth:</span>
                <select
                  value={depth}
                  onChange={e => setDepth(Number(e.target.value))}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-2 text-sm text-white focus:outline-none focus:border-primary"
                >
                  <option value={1}>1 Hop</option>
                  <option value={2}>2 Hops</option>
                  <option value={3}>3 Hops</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="text-xs text-slate-400">Limit:</span>
                <select
                  value={limit}
                  onChange={e => setLimit(Number(e.target.value))}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-2 text-sm text-white focus:outline-none focus:border-primary"
                >
                  <option value={10}>10</option>
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
              </div>
            </div>
          </form>

          {/* Quick Select from Active Case Entities */}
          {cases.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/80 text-xs">
              <span className="text-slate-400 flex items-center gap-1 font-medium">
                <Filter className="w-3.5 h-3.5" />
                <span>Active Entities:</span>
              </span>
              {cases.slice(0, 4).map(c => {
                const isSelected = selectedId === c.primary_entity_id;
                return (
                  <button
                    key={c.case_id}
                    onClick={() => handleSelectCaseEntity(c.primary_entity_type, c.primary_entity_id)}
                    className={`px-2.5 py-1 rounded-md border font-mono transition-colors flex items-center gap-1.5 ${
                      isSelected
                        ? 'bg-primary/20 border-primary text-primary font-semibold'
                        : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700 hover:text-white'
                    }`}
                  >
                    <span>{c.primary_entity_type}:</span>
                    <span>{c.primary_entity_id.substring(0, 8)}...</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Graph Canvas Container */}
        <div className="flex-1 bg-slate-950 border border-slate-800 rounded-xl overflow-hidden relative shadow-inner">
          {selectedId ? (
            <GraphPanel
              entityType={selectedType}
              entityId={selectedId}
              depth={depth}
              limit={limit}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-slate-500 text-sm gap-2">
              <Network className="w-8 h-8 text-slate-600" />
              <span>Select or search for an entity to inspect network topology.</span>
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  );
}
