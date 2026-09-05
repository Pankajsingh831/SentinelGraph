'use client';

import { Clock, Loader2 } from 'lucide-react';
import { useCaseTimeline } from '@/lib/hooks/use-cases';
import { formatDate } from '@/lib/utils';
import { TimelineEvent } from '@/lib/types';

export default function CaseTimeline({ caseId }: { caseId: string }) {
    const { data: timelineData, isLoading, isError } = useCaseTimeline(caseId);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center gap-2 py-8 text-slate-500 text-sm">
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                <span>Loading timeline events...</span>
            </div>
        );
    }

    if (isError) {
        return <div className="text-center text-slate-500 py-8 text-sm">Timeline data unavailable.</div>;
    }

    const events = Array.isArray(timelineData?.events) ? timelineData.events : [];
    if (events.length === 0) {
        return <div className="text-center text-slate-500 py-8 text-sm">No timeline events found.</div>;
    }

    return (
        <div className="space-y-4 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-800 before:to-transparent">
            {events.map((e: TimelineEvent, idx: number) => (
                <div key={idx} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                    <div className="flex items-center justify-center w-10 h-10 rounded-full border border-slate-800 bg-slate-900 text-slate-400 group-[.is-active]:text-primary shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
                        <Clock className="w-4 h-4" />
                    </div>
                    <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded bg-slate-950 border border-slate-800">
                        <div className="flex items-center justify-between mb-1 gap-2">
                            <div className="font-bold text-slate-200 text-sm">{e.event_type || 'Event'}</div>
                            <time className="text-xs font-medium text-slate-500 shrink-0">{formatDate(e.timestamp)}</time>
                        </div>
                        <div className="text-sm text-slate-400">{e.description || 'No description provided.'}</div>
                    </div>
                </div>
            ))}
        </div>
    );
}
