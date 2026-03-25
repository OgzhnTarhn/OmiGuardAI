function formatTimestamp(value) {
  if (!value) {
    return "No timestamp";
  }

  return new Date(value).toLocaleString();
}


function formatConfidence(value) {
  return `${((value ?? 0) * 100).toFixed(1)}%`;
}


export default function ViolationFeed({ violations, error, isLoading }) {
  return (
    <section className="panel panel-feed">
      <div className="panel-header">
        <p className="eyebrow">Live Feed</p>
        <h2>Recent Violations</h2>
      </div>

      {error ? <div className="feed-banner feed-banner-error">{error}</div> : null}
      {!error && isLoading ? <div className="feed-banner">Loading live incidents...</div> : null}
      {!error && !isLoading && violations.length === 0 ? (
        <div className="feed-banner">No incidents yet. Trigger the AI engine to populate the feed.</div>
      ) : null}

      <div className="violation-list">
        {violations.map((record, index) => {
          const event = record.event ?? {};
          const isLatest = index === 0;

          return (
            <article
              key={record.id ?? `${event.trackId}-${record.receivedAtUtc}`}
              className={`violation-card ${isLatest ? "violation-card-latest" : ""}`}
            >
              <div className="violation-topline">
                <span className={`violation-priority ${isLatest ? "violation-priority-hot" : ""}`}>
                  {isLatest ? "Latest" : "Queued"}
                </span>
                <span className="violation-time">{formatTimestamp(record.receivedAtUtc)}</span>
              </div>

              <div className="violation-title-row">
                <h3>{event.eventType ?? "Unknown event"}</h3>
                <strong>{formatConfidence(event.confidence)}</strong>
              </div>

              <div className="violation-meta-grid">
                <div>
                  <span>Camera</span>
                  <strong>{event.cameraId ?? "-"}</strong>
                </div>
                <div>
                  <span>Site</span>
                  <strong>{event.siteId ?? "-"}</strong>
                </div>
                <div>
                  <span>Track ID</span>
                  <strong>{event.trackId ?? "-"}</strong>
                </div>
                <div>
                  <span>Model</span>
                  <strong>{event.model ?? "-"}</strong>
                </div>
              </div>

              <div className="violation-footline">
                <span>Snapshot</span>
                <code className={event.snapshotPath ? "snapshot-ready" : "snapshot-empty"}>
                  {event.snapshotPath ?? "No snapshot yet"}
                </code>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
