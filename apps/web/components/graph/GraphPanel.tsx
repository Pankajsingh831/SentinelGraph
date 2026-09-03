'use client';
import dynamic from 'next/dynamic';
import { useEntityNeighbors } from '@/lib/hooks/use-graph';

const NetworkGraph = dynamic(() => import('./NetworkGraph'), { ssr: false, loading: () => <div className="flex h-full items-center justify-center text-slate-400">Loading Graph...</div> });

export default function GraphPanel({ entityType, entityId, depth = 1, limit = 25 }: { entityType: string, entityId: string, depth?: number, limit?: number }) {
    const { data } = useEntityNeighbors(entityType, entityId, depth, limit);

    return (
        <div className="w-full h-full relative">
            {data?.degraded && (
                <div className="absolute top-0 left-0 right-0 z-10 bg-yellow-950/80 border-b border-yellow-900 text-yellow-500 p-2 text-xs text-center">
                    Some data sources are temporarily unavailable. Displayed information may be incomplete.
                </div>
            )}
            <NetworkGraph nodes={data?.neighbors || []} edges={data?.edges || []} />
        </div>
    );
}
