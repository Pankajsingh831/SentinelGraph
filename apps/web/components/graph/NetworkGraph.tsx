'use client';
import { ReactFlow, Background, Controls, MiniMap } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { CustomerNode, DeviceNode, IPNode, InstrumentNode, MerchantNode } from './CustomNodes';

const nodeTypes = {
    Customer: CustomerNode,
    Device: DeviceNode,
    IP: IPNode,
    IPAddress: IPNode,
    Instrument: InstrumentNode,
    PaymentInstrument: InstrumentNode,
    Merchant: MerchantNode,
};

export default function NetworkGraph({ nodes, edges }: { nodes: any[], edges: any[] }) {
    return (
        <div className="w-full h-full">
            <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView colorMode="dark">
                <Background color="#334155" gap={16} />
                <Controls className="bg-slate-900 border-slate-800 fill-white" />
                <MiniMap nodeColor="#475569" maskColor="rgba(15, 23, 42, 0.7)" />
            </ReactFlow>
        </div>
    );
}
