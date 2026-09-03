'use client';
import PageContainer from '@/components/layout/PageContainer';
import GraphPanel from '@/components/graph/GraphPanel';
import { useState } from 'react';

export default function GraphExplorerPage({ params }: { params: { entityType: string, entityId: string } }) {
    const [depth, setDepth] = useState(1);
    const [limit, setLimit] = useState(25);

    return (
        <PageContainer title={`Graph Explorer: ${params.entityType} ${params.entityId}`}>
            <div className="flex flex-col h-[calc(100vh-10rem)]">
                <div className="flex gap-4 p-4 bg-slate-900 border border-slate-800 rounded-t-lg items-center">
                    <span className="text-sm font-medium">Controls:</span>
                    <select className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-sm" value={depth} onChange={e => setDepth(Number(e.target.value))}>
                        <option value={1}>Depth: 1</option>
                        <option value={2}>Depth: 2</option>
                        <option value={3}>Depth: 3</option>
                    </select>
                    <select className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-sm" value={limit} onChange={e => setLimit(Number(e.target.value))}>
                        <option value={10}>Limit: 10</option>
                        <option value={25}>Limit: 25</option>
                        <option value={50}>Limit: 50</option>
                        <option value={100}>Limit: 100</option>
                    </select>
                </div>
                <div className="flex-1 bg-slate-950 border-x border-b border-slate-800 rounded-b-lg overflow-hidden relative">
                    <GraphPanel entityType={params.entityType} entityId={params.entityId} depth={depth} limit={limit} />
                </div>
            </div>
        </PageContainer>
    );
}
