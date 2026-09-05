'use client';

import { getRiskTierColor } from '@/lib/utils';

export default function RiskGauge({ score, tier }: { score: number | null | undefined; tier?: string }) {
    const normScore = score == null || isNaN(score) ? 0 : score <= 1 && score >= 0 ? Math.round(score * 100) : Math.round(score);
    const upperTier = tier?.toUpperCase() || 'UNKNOWN';
    const color = upperTier === 'CRITICAL' ? '#ef4444' : upperTier === 'HIGH' ? '#f97316' : upperTier === 'MEDIUM' ? '#eab308' : '#3b82f6';
    
    return (
        <div className="flex flex-col items-center justify-center py-4">
            <div className="relative w-32 h-32 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="40" fill="transparent" stroke="#1e293b" strokeWidth="8" />
                    <circle cx="50" cy="50" r="40" fill="transparent" stroke={color} strokeWidth="8" strokeDasharray={`${normScore * 2.51} 251`} className="transition-all duration-1000 ease-out" />
                </svg>
                <div className="absolute flex flex-col items-center">
                    <span className="text-3xl font-bold text-white">{normScore}</span>
                    <span className={`text-xs font-medium ${getRiskTierColor(upperTier)}`}>{upperTier}</span>
                </div>
            </div>
        </div>
    );
}
