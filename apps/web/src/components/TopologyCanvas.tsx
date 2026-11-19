import { useMemo } from 'react';
import ReactFlow, { Background, Controls, Handle, Position } from 'reactflow';
import 'reactflow/dist/style.css';
import type { LabNode } from '../api/client';

export interface CanvasLink {
  from: string;
  to: string;
}

function NodeLabel({ data }: { data: { label: string; kind: string; status: string } }) {
  return (
    <div className="card" style={{ padding: '10px 14px', minWidth: 140 }}>
      <Handle type="target" position={Position.Top} />
      <strong>{data.label}</strong>
      <div className="muted" style={{ fontSize: 12 }}>{data.kind}</div>
      <span className={`badge ${data.status === 'running' ? 'ok' : 'pending'}`}>
        {data.status}
      </span>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

const nodeTypes = { labNode: NodeLabel };

export default function TopologyCanvas({
  nodes,
  links,
  onSelect,
}: {
  nodes: LabNode[];
  links: CanvasLink[];
  onSelect?: (name: string) => void;
}) {
  const flowNodes = useMemo(
    () =>
      nodes.map((n, i) => ({
        id: n.name,
        type: 'labNode',
        position: { x: (i % 3) * 240, y: Math.floor(i / 3) * 140 },
        data: { label: n.name, kind: n.kind, status: n.status },
      })),
    [nodes],
  );
  const flowEdges = useMemo(
    () =>
      links.map((l, i) => ({
        id: `e${i}`,
        source: l.from,
        target: l.to,
        animated: true,
      })),
    [links],
  );

  return (
    <div style={{ height: 320 }}>
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onSelect?.(node.id)}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
