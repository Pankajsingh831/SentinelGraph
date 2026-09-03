'use client';
import PageContainer from '@/components/layout/PageContainer';

export default function ReplayPage({ params }: { params: { scenarioId: string } }) {
    return (
        <PageContainer title="Detection Replay">
            <div className="p-8 text-center text-slate-400 bg-slate-900 rounded-lg border border-slate-800">
                <p>Replay Simulation for scenario: {params.scenarioId}</p>
                <p className="mt-4">This feature is currently using mock data or simple simulation.</p>
            </div>
        </PageContainer>
    );
}
