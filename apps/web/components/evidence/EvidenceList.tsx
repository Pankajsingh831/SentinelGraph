'use client';

import EvidenceCard from './EvidenceCard';
import { useCaseEvidence } from '@/lib/hooks/use-cases';
import { CaseEvidenceResponse } from '@/lib/types';
import { Loader2 } from 'lucide-react';

export default function EvidenceList({ caseId }: { caseId: string }) {
    const { data: evidence, isLoading, isError } = useCaseEvidence(caseId);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center gap-2 py-8 text-slate-500 text-sm">
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                <span>Loading evidence records...</span>
            </div>
        );
    }

    if (isError) {
        return <div className="text-center text-slate-500 py-8 text-sm">Evidence unavailable.</div>;
    }

    const evidenceList = Array.isArray(evidence) ? evidence : [];
    if (evidenceList.length === 0) {
        return <div className="text-center text-slate-500 py-8 text-sm">No evidence records found.</div>;
    }
    
    return (
        <div className="space-y-3">
            {evidenceList.map((e: CaseEvidenceResponse) => (
                <EvidenceCard key={e.evidence_id} evidence={e} />
            ))}
        </div>
    );
}
