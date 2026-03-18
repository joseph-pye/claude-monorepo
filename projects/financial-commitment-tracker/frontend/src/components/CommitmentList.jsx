import { useState } from 'react';

const STATUS_LABELS = {
  ok: '✅ All Clear',
  upcoming: '📋 Upcoming',
  soon: '⚠️ Soon',
  urgent: '🚨 Urgent',
  expired: '❌ Expired',
};

function CommitmentCard({ commitment, onEdit, onDelete, onRenew, onArchive }) {
  const [showRenew, setShowRenew] = useState(false);
  const [newDate, setNewDate] = useState('');

  const c = commitment;

  const handleRenew = () => {
    if (!newDate) return;
    onRenew(c.id, newDate);
    setShowRenew(false);
    setNewDate('');
  };

  // Suggest next year from current expiry
  const suggestedDate = new Date(c.expiry_date);
  suggestedDate.setFullYear(suggestedDate.getFullYear() + 1);
  const suggestedStr = suggestedDate.toISOString().split('T')[0];

  return (
    <div className={`commitment-card status-${c.status}`}>
      <div className="card-header">
        <div>
          <h3>{c.name}</h3>
          <span className="category-badge">{c.category}</span>
        </div>
        <span className={`status-badge status-${c.status}`}>
          {STATUS_LABELS[c.status]}
        </span>
      </div>

      <div className="card-details">
        {c.provider && <p><strong>Provider:</strong> {c.provider}</p>}
        {c.amount && <p><strong>Amount:</strong> {c.amount}</p>}
        <p><strong>Expires:</strong> {c.expiry_date}</p>
        <p className="days-display">
          {c.days_until_expiry >= 0
            ? `${c.days_until_expiry} days remaining`
            : `${Math.abs(c.days_until_expiry)} days overdue`}
        </p>
        {c.notes && <p className="notes">{c.notes}</p>}
      </div>

      <div className="card-actions">
        {!c.is_archived && (
          <>
            <button className="btn btn-small btn-renew" onClick={() => { setShowRenew(!showRenew); setNewDate(suggestedStr); }}>
              Renew
            </button>
            <button className="btn btn-small" onClick={() => onEdit(c)}>Edit</button>
            <button className="btn btn-small btn-archive" onClick={() => onArchive(c.id)}>Archive</button>
          </>
        )}
        <button className="btn btn-small btn-danger" onClick={() => onDelete(c.id)}>Delete</button>
      </div>

      {showRenew && (
        <div className="renew-panel">
          <p>Set new expiry date:</p>
          <input type="date" value={newDate} onChange={(e) => setNewDate(e.target.value)} />
          <button className="btn btn-primary btn-small" onClick={handleRenew}>Confirm Renewal</button>
          <button className="btn btn-small" onClick={() => setShowRenew(false)}>Cancel</button>
        </div>
      )}
    </div>
  );
}

function CommitmentList({ commitments, onEdit, onDelete, onRenew, onArchive }) {
  if (!commitments.length) {
    return (
      <div className="empty-state">
        <p>No commitments yet. Add your first one!</p>
      </div>
    );
  }

  return (
    <div className="commitment-list">
      {commitments.map((c) => (
        <CommitmentCard
          key={c.id}
          commitment={c}
          onEdit={onEdit}
          onDelete={onDelete}
          onRenew={onRenew}
          onArchive={onArchive}
        />
      ))}
    </div>
  );
}

export default CommitmentList;
