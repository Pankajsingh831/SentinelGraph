'use client';

import React, { useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  CustomerNode,
  TransactionNode,
  DeviceNode,
  IPNode,
  InstrumentNode,
  MerchantNode,
} from './CustomNodes';

const nodeTypes = {
  Customer: CustomerNode,
  Transaction: TransactionNode,
  Device: DeviceNode,
  IP: IPNode,
  IPAddress: IPNode,
  Instrument: InstrumentNode,
  PaymentInstrument: InstrumentNode,
  Merchant: MerchantNode,
};

export interface NetworkGraphProps {
  nodes: any[];
  edges: any[];
  primaryEntityId?: string;
  primaryEntityType?: string;
  caseRiskScore?: number;
  caseRiskTier?: string;
  networkRiskScore?: number;
  onSelectNode?: (node: any | null) => void;
  selectedNodeId?: string | null;
}

function normalizeNodeType(type?: string): string {
  if (!type) return 'Customer';
  const lower = type.toLowerCase().replace(/[_\s-]/g, '');
  if (lower.includes('transaction') || lower.includes('tx')) return 'Transaction';
  if (lower.includes('customer') || lower.includes('user')) return 'Customer';
  if (lower.includes('device')) return 'Device';
  if (lower.includes('ip')) return 'IPAddress';
  if (lower.includes('instrument') || lower.includes('card') || lower.includes('payment'))
    return 'PaymentInstrument';
  if (lower.includes('merchant') || lower.includes('store')) return 'Merchant';
  return 'Customer';
}

function formatNodeLabel(node: any, normalizedType: string): { label: string; sublabel: string } {
  const props = node.properties || {};
  const idStr = String(node.id || props.id || '');
  const shortId = idStr.length > 10 ? `${idStr.substring(0, 8)}...` : idStr;

  switch (normalizedType) {
    case 'Transaction': {
      const amount = props.amount != null ? Number(props.amount) : undefined;
      const amountStr = amount != null ? `$${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : shortId;
      return {
        label: `Tx: ${amountStr}`,
        sublabel: props.occurred_at ? new Date(props.occurred_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Transaction',
      };
    }
    case 'Customer':
      return {
        label: `Customer: ${shortId}`,
        sublabel: props.updated_at ? 'Active Account' : 'Customer Account',
      };
    case 'Device':
      return {
        label: `Device: ${shortId}`,
        sublabel: props.device_type ? String(props.device_type) : 'Hardware Entity',
      };
    case 'IPAddress':
    case 'IP':
      return {
        label: `IP: ${shortId}`,
        sublabel: 'Network IP',
      };
    case 'PaymentInstrument':
    case 'Instrument':
      return {
        label: `Card: ${shortId}`,
        sublabel: props.card_type ? String(props.card_type) : 'Payment Method',
      };
    case 'Merchant':
      return {
        label: `Merchant: ${shortId}`,
        sublabel: props.category ? String(props.category) : 'Merchant Outlet',
      };
    default:
      return {
        label: `${normalizedType}: ${shortId}`,
        sublabel: normalizedType,
      };
  }
}

export default function NetworkGraph({
  nodes,
  edges,
  primaryEntityId,
  primaryEntityType,
  caseRiskScore,
  caseRiskTier,
  networkRiskScore,
  onSelectNode,
  selectedNodeId,
}: NetworkGraphProps) {
  // 1. Compute graph adjacency, degrees, and shared hub statuses
  const { degreeMap, sharedHubSet, adjMap } = useMemo(() => {
    const degMap = new Map<string, number>();
    const aMap = new Map<string, Set<string>>();
    const customerConnections = new Map<string, Set<string>>();

    const nodeTypeMap = new Map<string, string>();
    nodes.forEach(n => {
      nodeTypeMap.set(String(n.id), normalizeNodeType(n.type));
    });

    edges.forEach(e => {
      const s = String(e.source);
      const t = String(e.target);

      degMap.set(s, (degMap.get(s) || 0) + 1);
      degMap.set(t, (degMap.get(t) || 0) + 1);

      if (!aMap.has(s)) aMap.set(s, new Set());
      if (!aMap.has(t)) aMap.set(t, new Set());
      aMap.get(s)!.add(t);
      aMap.get(t)!.add(s);

      // Track multi-customer infrastructure (Devices, IPs, Cards connected to > 1 Customer)
      const sType = nodeTypeMap.get(s);
      const tType = nodeTypeMap.get(t);
      if (sType === 'Customer') {
        if (!customerConnections.has(t)) customerConnections.set(t, new Set());
        customerConnections.get(t)!.add(s);
      }
      if (tType === 'Customer') {
        if (!customerConnections.has(s)) customerConnections.set(s, new Set());
        customerConnections.get(s)!.add(t);
      }
    });

    const sharedSet = new Set<string>();
    customerConnections.forEach((customers, hubId) => {
      if (customers.size > 1) {
        sharedSet.add(hubId);
      }
    });

    return { degreeMap: degMap, sharedHubSet: sharedSet, adjMap: aMap };
  }, [nodes, edges]);

  // 2. Structured Concentric/Radial Tree Layout
  const flowNodes: Node[] = useMemo(() => {
    if (!Array.isArray(nodes) || nodes.length === 0) return [];

    const total = nodes.length;
    const centerX = 400;
    const centerY = 300;

    // Identify primary node ID (from prop, or fallback to first node)
    const effectivePrimaryId = primaryEntityId
      ? String(primaryEntityId)
      : nodes.length > 0
      ? String(nodes[0].id)
      : '';

    // Calculate BFS distance (hops) from primary entity
    const hops = new Map<string, number>();
    const parentInHop = new Map<string, string>();
    hops.set(effectivePrimaryId, 0);

    const queue = [effectivePrimaryId];
    while (queue.length > 0) {
      const curr = queue.shift()!;
      const currHop = hops.get(curr)!;
      const neighbors = adjMap.get(curr) || new Set();

      neighbors.forEach(nbr => {
        if (!hops.has(nbr)) {
          hops.set(nbr, currHop + 1);
          parentInHop.set(nbr, curr);
          queue.push(nbr);
        }
      });
    }

    // Nodes grouped by hop
    const hop0Nodes: any[] = [];
    const hop1Nodes: any[] = [];
    const hop2Nodes: any[] = [];
    const otherNodes: any[] = [];

    nodes.forEach(n => {
      const id = String(n.id);
      const dist = hops.get(id);
      if (dist === 0) hop0Nodes.push(n);
      else if (dist === 1) hop1Nodes.push(n);
      else if (dist === 2) hop2Nodes.push(n);
      else otherNodes.push(n);
    });

    // Positions map
    const positions = new Map<string, { x: number; y: number }>();

    // Position Primary Node at center
    if (hop0Nodes.length > 0) {
      positions.set(String(hop0Nodes[0].id), { x: centerX, y: centerY });
    }

    // Sort Hop 1 nodes by entity type to cluster related entities together
    const typeOrder: Record<string, number> = {
      Device: 1,
      IPAddress: 2,
      IP: 2,
      PaymentInstrument: 3,
      Instrument: 3,
      Transaction: 4,
      Customer: 5,
      Merchant: 6,
    };

    hop1Nodes.sort((a, b) => {
      const ta = typeOrder[normalizeNodeType(a.type)] || 99;
      const tb = typeOrder[normalizeNodeType(b.type)] || 99;
      return ta - tb;
    });

    // Position Hop 1 nodes on Inner Orbit
    const r1 = Math.min(280, Math.max(180, 24 * Math.sqrt(Math.max(1, hop1Nodes.length))));
    hop1Nodes.forEach((n, idx) => {
      const angle = (2 * Math.PI * idx) / Math.max(1, hop1Nodes.length) - Math.PI / 2;
      positions.set(String(n.id), {
        x: Math.round(centerX + r1 * Math.cos(angle)),
        y: Math.round(centerY + r1 * Math.sin(angle)),
      });
    });

    // Position Hop 2 nodes on Outer Orbit, biased toward parent direction
    const r2 = r1 + 180;
    hop2Nodes.forEach((n, idx) => {
      const parentId = parentInHop.get(String(n.id));
      let baseAngle = (2 * Math.PI * idx) / Math.max(1, hop2Nodes.length) - Math.PI / 2;
      if (parentId && positions.has(parentId)) {
        const pPos = positions.get(parentId)!;
        baseAngle = Math.atan2(pPos.y - centerY, pPos.x - centerX) + ((idx % 3) - 1) * 0.25;
      }
      positions.set(String(n.id), {
        x: Math.round(centerX + r2 * Math.cos(baseAngle)),
        y: Math.round(centerY + r2 * Math.sin(baseAngle)),
      });
    });

    // Position any unreached nodes in an offset grid
    otherNodes.forEach((n, idx) => {
      positions.set(String(n.id), {
        x: centerX + 400 + (idx % 3) * 200,
        y: centerY - 200 + Math.floor(idx / 3) * 100,
      });
    });

    // Build Flow Node objects
    return nodes.map(n => {
      const nid = String(n.id);
      const normalizedType = normalizeNodeType(n.type);
      const isPrimary = nid === effectivePrimaryId;
      const isShared = sharedHubSet.has(nid);
      const degree = degreeMap.get(nid) || 0;
      const { label, sublabel } = formatNodeLabel(n, normalizedType);

      // Determine risk display: if primary, use caseRiskTier; if transaction, check amount or props
      let risk: string | undefined = undefined;
      if (isPrimary && caseRiskTier) {
        risk = caseRiskTier;
      } else if (n.properties?.risk_level) {
        risk = String(n.properties.risk_level);
      } else if (n.properties?.risk_score != null) {
        const sc = Number(n.properties.risk_score);
        risk = sc > 0.7 ? 'HIGH' : sc > 0.4 ? 'MEDIUM' : 'LOW';
      }

      const position = positions.get(nid) || { x: centerX, y: centerY };

      return {
        id: nid,
        type: normalizedType,
        position,
        data: {
          id: nid,
          label,
          sublabel,
          entityType: normalizedType,
          isPrimary,
          isSharedHub: isShared,
          degree,
          risk,
          amount: n.properties?.amount,
          occurred_at: n.properties?.occurred_at,
          updated_at: n.properties?.updated_at,
          properties: n.properties || {},
          rawNode: n,
        },
      };
    });
  }, [
    nodes,
    primaryEntityId,
    caseRiskTier,
    adjMap,
    degreeMap,
    sharedHubSet,
  ]);

  // 3. Build Flow Edge objects with clear labels, directional arrows, and highlight
  const flowEdges: Edge[] = useMemo(() => {
    if (!Array.isArray(edges) || edges.length === 0) return [];

    return edges.map((e, idx) => {
      const s = String(e.source);
      const t = String(e.target);
      const relType = e.type || 'LINKED';
      const connectsShared = sharedHubSet.has(s) || sharedHubSet.has(t);
      const connectsPrimary = Boolean(primaryEntityId && (s === primaryEntityId || t === primaryEntityId));

      let strokeColor = '#475569';
      let strokeWidth = 1.5;

      if (connectsPrimary) {
        strokeColor = '#3b82f6';
        strokeWidth = 2;
      } else if (connectsShared) {
        strokeColor = '#a855f7';
        strokeWidth = 2;
      }

      return {
        id: e.id || `edge-${s}-${t}-${relType}-${idx}`,
        source: s,
        target: t,
        label: relType,
        type: 'smoothstep',
        animated: Boolean(connectsPrimary && networkRiskScore && networkRiskScore > 0.5),
        style: {
          stroke: strokeColor,
          strokeWidth,
        },
        labelStyle: {
          fill: '#cbd5e1',
          fontSize: 9,
          fontWeight: 600,
          fontFamily: 'monospace',
        },
        labelBgStyle: {
          fill: '#0f172a',
          fillOpacity: 0.9,
          stroke: strokeColor,
          strokeWidth: 1,
          rx: 4,
          ry: 4,
        },
        labelBgPadding: [4, 2] as [number, number],
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 12,
          height: 12,
          color: strokeColor,
        },
      };
    });
  }, [edges, primaryEntityId, networkRiskScore, sharedHubSet]);

  if (flowNodes.length === 0) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-slate-950 text-slate-500 text-sm p-6 text-center">
        <span>No connected entities found for this case.</span>
      </div>
    );
  }

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        fitView
        colorMode="dark"
        minZoom={0.1}
        maxZoom={2.5}
        onNodeClick={(_event, node) => {
          onSelectNode?.(node.data?.rawNode || node);
        }}
        onPaneClick={() => {
          onSelectNode?.(null);
        }}
      >
        <Background color="#1e293b" gap={20} size={1} />
        <Controls className="bg-slate-900 border-slate-800 fill-slate-300" />
        <MiniMap
          nodeColor={n => {
            if (n.data?.isPrimary) return '#3b82f6';
            if (n.data?.isSharedHub) return '#a855f7';
            switch (n.type) {
              case 'Customer':
                return '#60a5fa';
              case 'Transaction':
                return '#34d399';
              case 'Device':
                return '#c084fc';
              case 'IPAddress':
              case 'IP':
                return '#22d3ee';
              case 'PaymentInstrument':
              case 'Instrument':
                return '#fbbf24';
              case 'Merchant':
                return '#fb7185';
              default:
                return '#64748b';
            }
          }}
          maskColor="rgba(15, 23, 42, 0.8)"
          className="bg-slate-950 border border-slate-800 rounded-lg overflow-hidden"
        />
      </ReactFlow>
    </div>
  );
}
