'use client';

import React from 'react';
import { Handle, Position } from '@xyflow/react';
import {
  User,
  Smartphone,
  Globe,
  CreditCard,
  Store,
  Receipt,
  ShieldAlert,
  Share2,
} from 'lucide-react';

interface CustomNodeData {
  id: string;
  label: string;
  sublabel?: string;
  entityType?: string;
  isPrimary?: boolean;
  isSharedHub?: boolean;
  degree?: number;
  risk?: string;
  riskScore?: number;
  amount?: number;
  occurred_at?: string;
  updated_at?: string;
  properties?: Record<string, unknown>;
  [key: string]: unknown;
}

interface BaseNodeProps {
  data: CustomNodeData;
  icon: React.ComponentType<{ className?: string }>;
  accentColor: string;
  borderColor: string;
  badgeBg: string;
}

const BaseNode = ({
  data,
  icon: Icon,
  accentColor,
  borderColor,
  badgeBg,
}: BaseNodeProps) => {
  const isPrimary = Boolean(data?.isPrimary);
  const isSharedHub = Boolean(data?.isSharedHub);
  const risk = data?.risk?.toUpperCase();
  const isHighRisk = risk === 'CRITICAL' || risk === 'HIGH';

  // Format label and sublabel
  const label = data?.label || data?.id || 'Entity';
  const sublabel = data?.sublabel;
  const degree = typeof data?.degree === 'number' ? data.degree : undefined;

  return (
    <div
      className={`relative px-3 py-2 rounded-lg bg-slate-900 shadow-xl transition-all duration-200 border-2 select-none min-w-[170px] max-w-[210px] ${
        isPrimary
          ? 'border-blue-500 ring-4 ring-blue-500/20 shadow-blue-500/30'
          : isHighRisk
          ? 'border-red-500 shadow-red-500/20'
          : borderColor
      }`}
    >
      {/* 4 Handles for clean multi-directional edge routing */}
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        className="!w-2 !h-2 !bg-slate-600 !border !border-slate-800"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom"
        className="!w-2 !h-2 !bg-slate-600 !border !border-slate-800"
      />
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        className="!w-2 !h-2 !bg-slate-600 !border !border-slate-800"
      />
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        className="!w-2 !h-2 !bg-slate-600 !border !border-slate-800"
      />

      {/* Top Banner for Primary Entity */}
      {isPrimary && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full shadow-md flex items-center gap-1 border border-blue-400 shrink-0 whitespace-nowrap">
          <ShieldAlert className="w-2.5 h-2.5" />
          <span>Primary Entity</span>
        </div>
      )}

      {/* Top Banner for Shared Hub (Multiple Users/Connections) */}
      {!isPrimary && isSharedHub && (
        <div className="absolute -top-2.5 right-2 bg-purple-950/90 text-purple-300 border border-purple-700/80 text-[9px] font-semibold px-1.5 py-0.5 rounded shadow flex items-center gap-1">
          <Share2 className="w-2.5 h-2.5 text-purple-400" />
          <span>Shared</span>
        </div>
      )}

      <div className="flex items-center gap-2.5">
        <div
          className={`w-8 h-8 rounded-md flex items-center justify-center shrink-0 border ${badgeBg}`}
        >
          <Icon className={`w-4 h-4 ${accentColor}`} />
        </div>
        <div className="flex flex-col min-w-0 flex-1">
          <div className="flex items-center justify-between gap-1">
            <span
              className="text-xs font-semibold text-white truncate"
              title={typeof label === 'string' ? label : String(label)}
            >
              {label}
            </span>
          </div>

          <div className="flex items-center gap-1.5 mt-0.5">
            {sublabel && (
              <span
                className="text-[10px] text-slate-400 truncate"
                title={sublabel}
              >
                {sublabel}
              </span>
            )}
            {degree != null && degree > 1 && (
              <span className="text-[9px] px-1 rounded bg-slate-800 text-slate-400 font-mono ml-auto">
                {degree} links
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Risk Indicator badge if present */}
      {risk && (
        <div className="mt-1.5 pt-1.5 border-t border-slate-800/80 flex items-center justify-between text-[10px]">
          <span className="text-slate-500 font-medium">Risk:</span>
          <span
            className={`px-1.5 py-0.5 rounded font-bold uppercase ${
              isHighRisk
                ? 'bg-red-950/80 text-red-400 border border-red-800/60'
                : 'bg-slate-800 text-slate-300'
            }`}
          >
            {risk}
          </span>
        </div>
      )}
    </div>
  );
};

export const CustomerNode = ({ data }: { data: CustomNodeData }) => (
  <BaseNode
    data={data}
    icon={User}
    accentColor="text-blue-400"
    borderColor="border-blue-500/50"
    badgeBg="bg-blue-950/70 border-blue-800/60"
  />
);

export const TransactionNode = ({ data }: { data: CustomNodeData }) => (
  <BaseNode
    data={data}
    icon={Receipt}
    accentColor="text-emerald-400"
    borderColor="border-emerald-500/50"
    badgeBg="bg-emerald-950/70 border-emerald-800/60"
  />
);

export const DeviceNode = ({ data }: { data: CustomNodeData }) => (
  <BaseNode
    data={data}
    icon={Smartphone}
    accentColor="text-purple-400"
    borderColor="border-purple-500/50"
    badgeBg="bg-purple-950/70 border-purple-800/60"
  />
);

export const IPNode = ({ data }: { data: CustomNodeData }) => (
  <BaseNode
    data={data}
    icon={Globe}
    accentColor="text-cyan-400"
    borderColor="border-cyan-500/50"
    badgeBg="bg-cyan-950/70 border-cyan-800/60"
  />
);

export const InstrumentNode = ({ data }: { data: CustomNodeData }) => (
  <BaseNode
    data={data}
    icon={CreditCard}
    accentColor="text-amber-400"
    borderColor="border-amber-500/50"
    badgeBg="bg-amber-950/70 border-amber-800/60"
  />
);

export const MerchantNode = ({ data }: { data: CustomNodeData }) => (
  <BaseNode
    data={data}
    icon={Store}
    accentColor="text-rose-400"
    borderColor="border-rose-500/50"
    badgeBg="bg-rose-950/70 border-rose-800/60"
  />
);
