import { useState, useEffect, useCallback } from 'react';
import { api } from './api';
import Dashboard from './components/Dashboard';
import CommitmentList from './components/CommitmentList';
import CommitmentForm from './components/CommitmentForm';
import './App.css';

function App() {
  const [commitments, setCommitments] = useState([]);
  const [status, setStatus] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingCommitment, setEditingCommitment] = useState(null);
  const [showArchived, setShowArchived] = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [items, summary] = await Promise.all([
        api.listCommitments(showArchived),
        api.getStatus(),
      ]);
      setCommitments(items);
      setStatus(summary);
    } catch (err) {
      console.error('Failed to load:', err);
    } finally {
      setLoading(false);
    }
  }, [showArchived]);

  useEffect(() => { refresh(); }, [refresh]);

  const handleCreate = async (data) => {
    await api.createCommitment(data);
    setShowForm(false);
    refresh();
  };

  const handleUpdate = async (id, data) => {
    await api.updateCommitment(id, data);
    setEditingCommitment(null);
    refresh();
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this commitment? This cannot be undone.')) return;
    await api.deleteCommitment(id);
    refresh();
  };

  const handleRenew = async (id, newDate) => {
    await api.renewCommitment(id, newDate);
    refresh();
  };

  const handleArchive = async (id) => {
    await api.updateCommitment(id, { is_archived: true });
    refresh();
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Financial Commitments</h1>
        <p className="subtitle">Track renewals, never miss a deadline</p>
      </header>

      <main>
        {status && <Dashboard status={status} />}

        <div className="toolbar">
          <button className="btn btn-primary" onClick={() => { setEditingCommitment(null); setShowForm(true); }}>
            + Add Commitment
          </button>
          <label className="toggle">
            <input
              type="checkbox"
              checked={showArchived}
              onChange={(e) => setShowArchived(e.target.checked)}
            />
            Show archived
          </label>
        </div>

        {showForm && (
          <CommitmentForm
            onSubmit={handleCreate}
            onCancel={() => setShowForm(false)}
          />
        )}

        {editingCommitment && (
          <CommitmentForm
            commitment={editingCommitment}
            onSubmit={(data) => handleUpdate(editingCommitment.id, data)}
            onCancel={() => setEditingCommitment(null)}
          />
        )}

        {loading ? (
          <p className="loading">Loading...</p>
        ) : (
          <CommitmentList
            commitments={commitments}
            onEdit={setEditingCommitment}
            onDelete={handleDelete}
            onRenew={handleRenew}
            onArchive={handleArchive}
          />
        )}
      </main>
    </div>
  );
}

export default App;
