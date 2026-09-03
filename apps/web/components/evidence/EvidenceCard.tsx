'use client';
import { AlertCircle } from 'lucide-react';
import { getRiskTierColor } from '@/lib/utils';
import { CaseEvidenceResponse } from '@/lib/types';

export default function EvidenceCard({ evidence }: { evidence: CaseEvidenceResponse }) {
    return (
        <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg mb-3">
            <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-slate-400" />
                    <span className="font-medium text-sm text-slate-200">{evidence.evidence_type}</span>
                </div>
                <span className={`text-xs font-bold px-2 py-0.5 rounded bg-slate-900 ${getRiskTierColor(evidence.severity)}`}>{evidence.severity}</span>
            </div>
            <p className="text-sm text-slate-400">{evidence.description}</p>
        </div>
    );
}
