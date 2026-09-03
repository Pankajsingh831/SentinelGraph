'use client';
import EvidenceCard from './EvidenceCard';
import { useCaseEvidence } from '@/lib/hooks/use-cases';
import { CaseEvidenceResponse } from '@/lib/types';

export default function EvidenceList({ caseId }: { caseId: string }) {
    const { data: evidence, isLoading } = useCaseEvidence(caseId);

    if (isLoading) return <div className="text-center text-slate-500 py-8">Loading evidence...</div>;
    if (!evidence || evidence.length === 0) return <div className="text-center text-slate-500 py-8">No evidence found.</div>;
    
    return (
        <div>
            {evidence.map((e: CaseEvidenceResponse) => (
                <EvidenceCard key={e.evidence_id} evidence={e} />
            ))}
        </div>
    );
}
