const BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (res.status === 204) return null;
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export const api = {
  listCommitments: (archived = false) =>
    request(`/commitments?archived=${archived}`),

  getCommitment: (id) =>
    request(`/commitments/${id}`),

  createCommitment: (data) =>
    request('/commitments', { method: 'POST', body: JSON.stringify(data) }),

  updateCommitment: (id, data) =>
    request(`/commitments/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  deleteCommitment: (id) =>
    request(`/commitments/${id}`, { method: 'DELETE' }),

  renewCommitment: (id, newExpiryDate) =>
    request(`/commitments/${id}/renew`, {
      method: 'POST',
      body: JSON.stringify({ new_expiry_date: newExpiryDate }),
    }),

  getStatus: () => request('/status'),

  getCategories: () => request('/categories'),
};
