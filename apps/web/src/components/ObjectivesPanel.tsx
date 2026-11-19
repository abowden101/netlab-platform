import type { GradeResult, Objective } from '../api/client';

export default function ObjectivesPanel({
  objectives,
  results,
  grading,
  onGrade,
}: {
  objectives: Objective[];
  results: GradeResult[];
  grading: boolean;
  onGrade: () => void;
}) {
  const byId = new Map(results.map((r) => [r.objective_id, r]));
  const passed = results.filter((r) => r.passed).length;
  return (
    <div className="card">
      <div className="row">
        <h3 style={{ margin: 0 }}>Objectives</h3>
        {results.length > 0 && (
          <span className="muted">
            {passed}/{objectives.length} passed
          </span>
        )}
        <button onClick={onGrade} disabled={grading}>
          {grading ? 'Running checks…' : 'Run checks'}
        </button>
      </div>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {objectives.map((o) => {
          const result = byId.get(o.id);
          return (
            <li key={o.id} style={{ margin: '12px 0' }}>
              <span
                className={`badge ${result ? (result.passed ? 'ok' : 'fail') : 'pending'}`}
              >
                {result ? (result.passed ? 'passed' : 'failed') : 'pending'}
              </span>{' '}
              <strong>{o.title}</strong>
              <div className="muted" style={{ fontSize: 13 }}>{o.description}</div>
              <div className="muted" style={{ fontSize: 12 }}>
                {o.engine} · node {o.node}
              </div>
              {result && (
                <div style={{ fontSize: 12, marginTop: 4 }}>{result.evidence}</div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
