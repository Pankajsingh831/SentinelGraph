'use client';
export default function RiskBreakdown({ tx, nw, tp }: { tx: number, nw: number, tp: number }) {
    return (
        <div className="space-y-3 mt-4">
            <div>
                <div className="flex justify-between text-xs mb-1"><span className="text-slate-400">Transaction</span><span className="text-slate-200">{tx}</span></div>
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden"><div className="h-full bg-blue-500" style={{width: `${tx}%`}}></div></div>
            </div>
            <div>
                <div className="flex justify-between text-xs mb-1"><span className="text-slate-400">Network</span><span className="text-slate-200">{nw}</span></div>
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden"><div className="h-full bg-purple-500" style={{width: `${nw}%`}}></div></div>
            </div>
            <div>
                <div className="flex justify-between text-xs mb-1"><span className="text-slate-400">Temporal</span><span className="text-slate-200">{tp}</span></div>
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden"><div className="h-full bg-green-500" style={{width: `${tp}%`}}></div></div>
            </div>
        </div>
    );
}
