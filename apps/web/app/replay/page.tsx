'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import PageContainer from '@/components/layout/PageContainer';
import CaseTimeline from '@/components/timeline/CaseTimeline';
import { useCases, useCase, useCaseTimeline } from '@/lib/hooks/use-cases';
import { formatDate, formatRiskScore, getRiskTierColor } from '@/lib/utils';
import {
  Play,
  Pause,
  RotateCcw,
  FastForward,
  Shield,
  Clock,
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
} from 'lucide-react';

export default function DetectionReplayPage() {
  const { data: casesResponse, isLoading: isCasesLoading } = useCases({ limit: 10 });
  const cases = useMemo(() => casesResponse?.items || [], [casesResponse?.items]);

  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Auto-select first case if none selected
  useEffect(() => {
    if (!selectedCaseId && cases.length > 0) {
      setSelectedCaseId(cases[0].case_id);
    }
  }, [cases, selectedCaseId]);

  const { data: caseDetail } = useCase(selectedCaseId);
  const { data: timelineData } = useCaseTimeline(selectedCaseId);

  const rawEvents = Array.isArray(timelineData?.events) ? timelineData.events : [];
  // Sort events chronologically
  const events = [...rawEvents].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  // Reset playback when selected case changes
  useEffect(() => {
    setIsPlaying(false);
    setCurrentStep(events.length > 0 ? events.length - 1 : 0);
    if (timerRef.current) clearInterval(timerRef.current);
  }, [selectedCaseId, events.length]);

  // Handle playback interval
  useEffect(() => {
    if (isPlaying) {
      const intervalMs = Math.max(200, 1500 / playbackSpeed);
      timerRef.current = setInterval(() => {
        setCurrentStep(prev => {
          if (prev >= events.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, intervalMs);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, events.length, playbackSpeed]);

  const handlePlayPause = () => {
    if (events.length === 0) return;
    if (currentStep >= events.length - 1) {
      // If at the end, restart from beginning
      setCurrentStep(0);
      setIsPlaying(true);
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  const handleReset = () => {
    setIsPlaying(false);
    setCurrentStep(0);
  };

  const visibleEvents = events.slice(0, currentStep + 1);

  return (
    <PageContainer title="Detection Replay">
      <div className="flex flex-col space-y-6 max-w-7xl mx-auto">
        {/* Header Summary */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Detection Replay Simulation</h1>
            <p className="text-sm text-slate-400 mt-1">
              Step-by-step playback of ingested events, temporal velocity checks, and heuristic triggers.
            </p>
          </div>

          {/* Scenario / Case Picker */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 shrink-0">Case:</span>
            <select
              value={selectedCaseId}
              onChange={e => setSelectedCaseId(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary font-mono"
            >
              {cases.map(c => (
                <option key={c.case_id} value={c.case_id}>
                  {c.case_id.substring(0, 8)}... — {c.risk_tier} ({formatRiskScore(c.overall_risk_score)})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Playback Controls & Status */}
        <div className="p-5 bg-slate-900 rounded-xl border border-slate-800 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            {/* Playback Buttons */}
            <div className="flex items-center gap-2">
              <button
                onClick={handlePlayPause}
                disabled={events.length === 0}
                className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-white font-medium text-sm transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                <span>{isPlaying ? 'Pause' : currentStep >= events.length - 1 ? 'Replay' : 'Play'}</span>
              </button>

              <button
                onClick={handleReset}
                disabled={events.length === 0}
                className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm transition-colors flex items-center gap-1.5 disabled:opacity-50"
                title="Reset to beginning"
              >
                <RotateCcw className="w-4 h-4" />
                <span>Reset</span>
              </button>

              {/* Speed Toggles */}
              <div className="flex items-center gap-1 ml-2 bg-slate-950 p-1 rounded-lg border border-slate-800">
                {[1, 2, 5].map(spd => (
                  <button
                    key={spd}
                    onClick={() => setPlaybackSpeed(spd)}
                    className={`px-2 py-1 rounded text-xs font-semibold transition-colors ${
                      playbackSpeed === spd
                        ? 'bg-primary text-white'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    {spd}x
                  </button>
                ))}
              </div>
            </div>

            {/* Step Counter */}
            <div className="text-xs text-slate-400 flex items-center gap-2">
              <span className="font-medium text-slate-300">
                Step {events.length > 0 ? currentStep + 1 : 0} of {events.length}
              </span>
              <span>•</span>
              <span>
                Status:{' '}
                <strong className={isPlaying ? 'text-emerald-400' : 'text-slate-300'}>
                  {isPlaying ? 'Streaming playback' : currentStep >= events.length - 1 && events.length > 0 ? 'Completed' : 'Paused'}
                </strong>
              </span>
            </div>
          </div>

          {/* Progress Timeline Scrubber */}
          <div className="space-y-1.5">
            <div className="w-full bg-slate-950 h-2.5 rounded-full overflow-hidden border border-slate-800">
              <div
                className="bg-primary h-full transition-all duration-300 ease-out rounded-full"
                style={{
                  width: `${events.length > 0 ? ((currentStep + 1) / events.length) * 100 : 0}%`,
                }}
              />
            </div>
          </div>
        </div>

        {/* Selected Case Quick Intelligence */}
        {caseDetail && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 bg-slate-900 rounded-xl border border-slate-800">
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Risk Tier</span>
              <div className={`text-xl font-bold mt-1 ${getRiskTierColor(caseDetail.risk_tier)}`}>
                {caseDetail.risk_tier} RISK
              </div>
              <span className="text-xs text-slate-500">Overall: {formatRiskScore(caseDetail.overall_risk_score)}</span>
            </div>

            <div className="p-4 bg-slate-900 rounded-xl border border-slate-800">
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Primary Entity</span>
              <div className="text-sm font-mono font-bold text-white mt-1 truncate" title={caseDetail.primary_entity_id}>
                {caseDetail.primary_entity_id}
              </div>
              <span className="text-xs text-slate-500 capitalize">{caseDetail.primary_entity_type}</span>
            </div>

            <div className="p-4 bg-slate-900 rounded-xl border border-slate-800">
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Detection Reason</span>
              <div className="text-xs text-slate-300 mt-1 line-clamp-2" title={caseDetail.case_reason}>
                {caseDetail.case_reason || 'Automated rule engine detection'}
              </div>
            </div>

            <div className="p-4 bg-slate-900 rounded-xl border border-slate-800">
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Case Status</span>
              <div className="text-base font-bold text-white mt-1">
                {caseDetail.status}
              </div>
              <span className="text-xs text-slate-500">Created {formatDate(caseDetail.created_at)}</span>
            </div>
          </div>
        )}

        {/* Live Replay Event Stream */}
        <div className="p-6 bg-slate-900 rounded-xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" />
              <h3 className="font-semibold text-white text-base">Replay Stream</h3>
            </div>
            <span className="text-xs text-slate-400">
              Showing {visibleEvents.length} of {events.length} events
            </span>
          </div>

          {events.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-sm bg-slate-950 rounded-lg border border-slate-800">
              No timeline events recorded for this case.
            </div>
          ) : (
            <div className="space-y-3">
              {visibleEvents.map((e, idx) => {
                const isLatest = idx === visibleEvents.length - 1;
                return (
                  <div
                    key={idx}
                    className={`p-4 rounded-lg border transition-all ${
                      isLatest
                        ? 'bg-primary/10 border-primary/50 shadow-md shadow-primary/10'
                        : 'bg-slate-950 border-slate-800/80'
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-300 text-xs font-mono flex items-center justify-center shrink-0">
                          {idx + 1}
                        </span>
                        <span className="font-bold text-sm text-slate-200">
                          {e.event_type}
                        </span>
                        {isLatest && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-primary text-white animate-pulse">
                            ACTIVE STEP
                          </span>
                        )}
                      </div>
                      <time className="text-xs text-slate-500 font-mono">
                        {formatDate(e.timestamp)}
                      </time>
                    </div>
                    <p className="text-xs text-slate-300 pl-7 leading-relaxed">
                      {e.description}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  );
}
