export default function MetricCard({ label, value, accent }) {
  return (
    <article className={`metric-card metric-card-${accent}`}>
      <span className="metric-label">{label}</span>
      <strong className="metric-value">{value}</strong>
    </article>
  );
}
