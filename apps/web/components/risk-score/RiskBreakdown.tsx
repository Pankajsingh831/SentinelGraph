'use client';

function normalizeScore(score: number | null | undefined): number {
    if (score == null || isNaN(score)) return 0;
    return score <= 1 && score >= 0 ? Math.round(score * 100) : Math.round(score);
}

export default function RiskBreakdown({ tx, nw, tp }: { tx: number | null | undefined; nw: number | null | undefined; tp: number | null | undefined }) {
    const nTx = normalizeScore(tx);
    const nNw = normalizeScore(nw);
    const nTp = normalizeScore(tp);

    return (
        <div className="space-y-3 mt-4">
            <div>
                <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Transaction</span>
                    <span className="text-slate-200 font-semibold">{nTx}%</span>
                </div>
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full transition-all duration-500" style={{ width: `${nTx}%` }}></div>
                </div>
            </div>
            <div>
                <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Network</span>
                    <span className="text-slate-200 font-semibold">{nNw}%</span>
                </div>
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-purple-500 rounded-full transition-all duration-500" style={{ width: `${nNw}%` }}></div>
                </div>
            </div>
            <div>
                <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Temporal</span>
                    <span className="text-slate-200 font-semibold">{nTp}%</span>
                </div>
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-500 rounded-full transition-all duration-500" style={{ width: `${nTp}%` }}></div>
                </div>
            </div>
        </div>
    );
}
