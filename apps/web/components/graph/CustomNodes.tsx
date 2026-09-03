'use client';
import { Handle, Position } from '@xyflow/react';
import { User, Smartphone, Globe, CreditCard, Store } from 'lucide-react';

const BaseNode = ({ data, icon: Icon, borderColor }: any) => (
    <div className={`px-4 py-2 shadow-md rounded-md bg-slate-900 border-2 ${data.risk === 'HIGH' ? 'border-red-500 shadow-[0_0_15px_rgba(239,68,68,0.5)]' : borderColor} flex items-center gap-2`}>
        <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-slate-500" />
        <Icon className="w-4 h-4 text-slate-300" />
        <div className="flex flex-col">
            <span className="text-xs font-bold text-white">{data.label}</span>
            {data.sublabel && <span className="text-[10px] text-slate-400">{data.sublabel}</span>}
        </div>
        <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-slate-500" />
    </div>
);

export const CustomerNode = ({ data }: any) => <BaseNode data={data} icon={User} borderColor="border-blue-500" />;
export const DeviceNode = ({ data }: any) => <BaseNode data={data} icon={Smartphone} borderColor="border-purple-500" />;
export const IPNode = ({ data }: any) => <BaseNode data={data} icon={Globe} borderColor="border-gray-500" />;
export const InstrumentNode = ({ data }: any) => <BaseNode data={data} icon={CreditCard} borderColor="border-green-500" />;
export const MerchantNode = ({ data }: any) => <BaseNode data={data} icon={Store} borderColor="border-yellow-500" />;
