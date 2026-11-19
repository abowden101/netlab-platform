import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api, type GradeResult, type Lab, type Session } from '../api/client';
import TopologyCanvas, { type CanvasLink } from '../components/TopologyCanvas';
import TerminalPane from '../components/TerminalPane';
import FileBrowser from '../components/FileBrowser';
import ObjectivesPanel from '../components/ObjectivesPanel';

export default function LabSession() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [session, setSession] = useState<Session | null>(null);
  const [lab, setLab] = useState<Lab | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [results, setResults] = useState<GradeResult[]>([]);
  const [grading, setGrading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    api
      .getSession(sessionId)
      .then((s) => {
        setSession(s);
        setSelectedNode(s.nodes?.[0]?.name ?? null);
        return api.getLab(s.lab_slug);
      })
      .then(setLab)
      .catch((err: Error) => setError(err.message));
  }, [sessionId]);

  async function grade() {
    if (!sessionId) return;
    setGrading(true);
    try {
      const res = await api.gradeSession(sessionId);
      setResults(res.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'grading failed');
    } finally {
      setGrading(false);
    }
  }

  async function destroy() {
    if (!sessionId) return;
    await api.destroySession(sessionId);
    setSession((s) => (s ? { ...s, status: 'destroyed' } : s));
  }

  if (error) return <div className="page"><p style={{ color: 'var(--fail)' }}>{error}</p></div>;
  if (!session || !lab) return <div className="page"><p className="muted">Loading session…</p></div>;

  const links: CanvasLink[] = (session.links ?? []).map((l) => ({
    from: l.from_node,
    to: l.to_node,
  }));
  const nodes = session.nodes ?? [];

  return (
    <div className="page">
      <div className="row">
        <h1 style={{ margin: 0 }}>{lab.title}</h1>
        <span className={`badge ${session.status === 'running' ? 'ok' : 'pending'}`}>
          {session.status}
        </span>
        <button className="secondary" onClick={destroy} style={{ marginLeft: 'auto' }}>
          Destroy lab
        </button>
      </div>
      <p className="muted">{lab.description}</p>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Topology</h3>
        <TopologyCanvas nodes={nodes} links={links} onSelect={setSelectedNode} />
        <p className="muted" style={{ fontSize: 13 }}>
          Click a node to open its console below.
        </p>
      </div>

      {selectedNode && session.status === 'running' && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Console — {selectedNode}</h3>
          <TerminalPane sessionId={session.id} node={selectedNode} />
        </div>
      )}

      <div style={{ display: 'grid', gap: 16, gridTemplateColumns: '1fr 1fr' }}>
        <ObjectivesPanel
          objectives={lab.objectives}
          results={results}
          grading={grading}
          onGrade={grade}
        />
        <FileBrowser sessionId={session.id} />
      </div>

      {lab.guide && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3 style={{ marginTop: 0 }}>Guide</h3>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{lab.guide}</pre>
        </div>
      )}
    </div>
  );
}
