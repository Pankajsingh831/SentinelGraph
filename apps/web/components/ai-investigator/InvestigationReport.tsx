'use client';
export default function InvestigationReport({ report, onReRun }: { report: any, onReRun: () => void }) {
    return (
        <div className="flex-1 space-y-4">
            <div className="bg-slate-950 p-3 rounded border border-slate-800 text-sm leading-relaxed text-slate-300">
                {report.summary}
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                    <div className="text-slate-500 text-xs mb-1">Confidence</div>
                    <div className="font-bold text-green-500">{report.confidence}%</div>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                    <div className="text-slate-500 text-xs mb-1">Recommendation</div>
                    <div className="font-bold text-orange-500">{report.recommended_action}</div>
                </div>
            </div>
            <button onClick={onReRun} className="w-full bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded text-sm transition-colors mt-4">
                Re-run Analysis
            </button>
        </div>
    );
}
