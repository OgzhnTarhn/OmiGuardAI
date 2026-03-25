const STATUS_LABELS = {
  ok: "API Healthy",
  degraded: "API Degraded",
  connecting: "Connecting",
};


export default function StatusBadge({ status }) {
  const resolvedStatus = STATUS_LABELS[status] ? status : "degraded";

  return (
    <div className={`status-badge status-${resolvedStatus}`}>
      <span className="status-dot" />
      <strong>{STATUS_LABELS[resolvedStatus]}</strong>
    </div>
  );
}
