import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, type Lab } from '../api/client';

export default function Labs() {
  const [labs, setLabs] = useState<Lab[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [deploying, setDeploying] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.listLabs().then(setLabs).catch((err: Error) => setError(err.message));
  }, []);

  async function deploy(slug: string) {
    setDeploying(slug);
    setError(null);
    try {
      const session = await api.deployLab(slug);
      navigate(`/sessions/${session.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'deploy failed');
    } finally {
      setDeploying(null);
    }
  }

  return (
    <div className="page">
      <div className="row">
        <h1 style={{ margin: 0 }}>netlab</h1>
        <span className="muted">browser network labs · real emulation</span>
        <Link to="/instructor" style={{ marginLeft: 'auto' }}>Instructor dashboard</Link>
      </div>
      {error && <p style={{ color: 'var(--fail)' }}>{error}</p>}
      <div className="grid" style={{ marginTop: 16 }}>
        {labs.map((lab) => (
          <div key={lab.id} className="card">
            <h2 style={{ marginTop: 0 }}>{lab.title}</h2>
            <p className="muted">{lab.description}</p>
            <p className="muted" style={{ fontSize: 13 }}>
              ~{lab.estimated_minutes} min · {lab.objectives.length} objectives
            </p>
            <button onClick={() => deploy(lab.id)} disabled={deploying === lab.id}>
              {deploying === lab.id ? 'Deploying…' : 'Deploy lab'}
            </button>
          </div>
        ))}
      </div>
      {labs.length === 0 && !error && <p className="muted">Loading labs…</p>}
    </div>
  );
}
