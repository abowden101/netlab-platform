import { useEffect, useState } from 'react';
import { api, type StudentSummary } from '../api/client';

export default function InstructorDashboard() {
  const [students, setStudents] = useState<StudentSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .instructorStudents()
      .then(setStudents)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <div className="page">
      <h1 style={{ marginTop: 0 }}>Instructor dashboard</h1>
      {error && <p style={{ color: 'var(--fail)' }}>{error}</p>}
      <div className="card">
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left' }}>
              <th>Student</th>
              <th>Role</th>
              <th>Sessions</th>
              <th>Objectives passed</th>
            </tr>
          </thead>
          <tbody>
            {students.map((s) => (
              <tr key={s.id}>
                <td>{s.name || s.email}</td>
                <td>{s.role}</td>
                <td>{s.sessions}</td>
                <td>{s.objectives_passed}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {students.length === 0 && !error && (
          <p className="muted">No students yet — or you lack the instructor role.</p>
        )}
      </div>
    </div>
  );
}
