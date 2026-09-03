'use client';
import { getRiskTierColor } from '@/lib/utils';

export default function RiskGauge({ score, tier }: { score: number, tier: string }) {
    const color = tier === 'CRITICAL' ? '#ef4444' : tier === 'HIGH' ? '#f97316' : tier === 'MEDIUM' ? '#eab308' : '#3b82f6';
    
    return (
        <div className="flex flex-col items-center justify-center py-4">
            <div className="relative w-32 h-32 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="40" fill="transparent" stroke="#1e293b" strokeWidth="8" />
                    <circle cx="50" cy="50" r="40" fill="transparent" stroke={color} strokeWidth="8" strokeDasharray={`${score * 2.51} 251`} className="transition-all duration-1000 ease-out" />
                </svg>
                <div className="absolute flex flex-col items-center">
                    <span className="text-3xl font-bold text-white">{score}</span>
                    <span className={`text-xs font-medium ${getRiskTierColor(tier)}`}>{tier}</span>
                </div>
            </div>
        </div>
    );
}
