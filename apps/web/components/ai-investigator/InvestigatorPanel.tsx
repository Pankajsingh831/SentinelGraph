'use client';
import { Bot, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import InvestigationReport from './InvestigationReport';
import { useInvestigate } from '@/lib/hooks/use-ai';

export default function InvestigatorPanel({ caseId }: { caseId: string }) {
    const { mutate: investigate, data, isPending, isError, error } = useInvestigate(caseId);

    const report = data?.report;
    const fallbackMessage = data?.fallback_message;

    return (
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 h-full flex flex-col">
            <div className="flex items-center gap-2 mb-6">
                <Bot className="w-5 h-5 text-purple-500" />
                <h3 className="font-medium text-white">AI Investigator</h3>
            </div>
            
            {!report && !isPending && !fallbackMessage && !isError && (
                <div className="flex-1 flex flex-col items-center justify-center text-center">
                    <p className="text-sm text-slate-400 mb-6">Run deep AI analysis on this case to synthesize evidence and recommend actions.</p>
                    <button onClick={() => investigate()} className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded font-medium text-sm transition-colors">
                        Investigate with AI
                    </button>
                </div>
            )}

            {isPending && (
                <div className="flex-1 flex flex-col items-center justify-center text-purple-500 gap-4">
                    <Loader2 className="w-8 h-8 animate-spin" />
                    <span className="text-sm text-white">AI is analyzing the case...</span>
                </div>
            )}

            {isError && (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-4">
                    <AlertCircle className="w-8 h-8 text-red-500 mb-2" />
                    <p className="text-sm font-semibold text-red-300 mb-1">Investigation Failed</p>
                    <p className="text-xs text-red-400 mb-4 max-w-[220px]">
                        {(error as any)?.message || 'Unable to complete AI investigation.'}
                    </p>
                    <button
                        onClick={() => investigate()}
                        className="inline-flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-white px-3 py-1.5 rounded font-medium text-xs transition-colors border border-slate-700"
                    >
                        <RefreshCw className="w-3.5 h-3.5" />
                        Retry Investigation
                    </button>
                </div>
            )}

            {fallbackMessage && !report && !isError && (
                <div className="flex-1 flex flex-col items-center justify-center text-center">
                    <p className="text-sm text-orange-400 mb-4">{fallbackMessage}</p>
                    <button onClick={() => investigate()} className="bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded font-medium text-sm transition-colors">
                        Retry Analysis
                    </button>
                </div>
            )}

            {report && <InvestigationReport report={report} onReRun={() => investigate()} />}
        </div>
    );
}
