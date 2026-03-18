import { useState } from 'react';

const CATEGORIES = [
  'Mortgage',
  'Insurance',
  'Subscription',
  'Loan',
  'Warranty',
  'Contract',
  'Membership',
  'Other',
];

function CommitmentForm({ commitment, onSubmit, onCancel }) {
  const [form, setForm] = useState({
    name: commitment?.name || '',
    category: commitment?.category || 'Insurance',
    provider: commitment?.provider || '',
    expiry_date: commitment?.expiry_date || '',
    amount: commitment?.amount || '',
    notes: commitment?.notes || '',
  });

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(form);
  };

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <form className="commitment-form" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>{commitment ? 'Edit Commitment' : 'Add Commitment'}</h2>

        <label>
          Name *
          <input name="name" value={form.name} onChange={handleChange} required placeholder="e.g. Home Insurance" />
        </label>

        <label>
          Category *
          <select name="category" value={form.category} onChange={handleChange}>
            {CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </label>

        <label>
          Provider
          <input name="provider" value={form.provider} onChange={handleChange} placeholder="e.g. Aviva, Nationwide" />
        </label>

        <label>
          Expiry Date *
          <input name="expiry_date" type="date" value={form.expiry_date} onChange={handleChange} required />
        </label>

        <label>
          Amount
          <input name="amount" value={form.amount} onChange={handleChange} placeholder="e.g. £1,200/year" />
        </label>

        <label>
          Notes
          <textarea name="notes" value={form.notes} onChange={handleChange} rows={3} placeholder="Any additional details..." />
        </label>

        <div className="form-actions">
          <button type="submit" className="btn btn-primary">
            {commitment ? 'Save Changes' : 'Add Commitment'}
          </button>
          <button type="button" className="btn" onClick={onCancel}>Cancel</button>
        </div>
      </form>
    </div>
  );
}

export default CommitmentForm;
