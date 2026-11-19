import { useState } from 'react';
import { api } from '../api/client';

/**
 * File browser for a running session: shows each node's running config,
 * captured on demand through the snapshot endpoint. Configs can be
 * downloaded for diffing against the intended config.
 */
export default function FileBrowser({ sessionId }: { sessionId: string }) {
  const [configs, setConfigs] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadSnapshot() {
    setLoading(true);
    setError(null);
    try {
      const snap = await api.snapshotSession(sessionId);
      setConfigs(snap.configs);
      const first = Object.keys(snap.configs)[0];
      setSelected(first ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'snapshot failed');
    } finally {
      setLoading(false);
    }
  }

  function download(name: string) {
    const blob = new Blob([configs[name]], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${name}-running-config.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const names = Object.keys(configs);
  return (
    <div className="card">
      <div className="row">
        <h3 style={{ margin: 0 }}>Running configs</h3>
        <button onClick={loadSnapshot} disabled={loading}>
          {loading ? 'Capturing…' : 'Capture snapshot'}
        </button>
      </div>
      {error && <p style={{ color: 'var(--fail)' }}>{error}</p>}
      {names.length === 0 && (
        <p className="muted">No snapshot yet. Capture one to view node configs.</p>
      )}
      <div className="row" style={{ marginTop: 12 }}>
        {names.map((name) => (
          <button
            key={name}
            className="secondary"
            onClick={() => setSelected(name)}
            style={selected === name ? { borderColor: 'var(--accent)' } : undefined}
          >
            {name}
          </button>
        ))}
        {selected && <button onClick={() => download(selected)}>Download</button>}
      </div>
      {selected && <pre className="config">{configs[selected]}</pre>}
    </div>
  );
}
