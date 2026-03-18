function Dashboard({ status }) {
  const cards = [
    { label: 'Total', value: status.total, className: 'card-total' },
    { label: 'All Clear', value: status.ok, className: 'card-ok' },
    { label: 'Upcoming', value: status.upcoming, className: 'card-upcoming' },
    { label: 'Soon', value: status.soon, className: 'card-soon' },
    { label: 'Urgent', value: status.urgent, className: 'card-urgent' },
    { label: 'Expired', value: status.expired, className: 'card-expired' },
  ];

  return (
    <div className="dashboard">
      {cards.map((c) => (
        <div key={c.label} className={`dashboard-card ${c.className}`}>
          <div className="card-value">{c.value}</div>
          <div className="card-label">{c.label}</div>
        </div>
      ))}
    </div>
  );
}

export default Dashboard;
