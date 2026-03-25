import { startTransition, useEffect, useMemo, useState } from "react";

import MetricCard from "./components/MetricCard.jsx";
import StatusBadge from "./components/StatusBadge.jsx";
import ViolationFeed from "./components/ViolationFeed.jsx";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";
const POLL_INTERVAL_MS = 2500;


function formatTimestamp(value) {
  if (!value) {
    return "No data";
  }

  return new Date(value).toLocaleString();
}


function normalizeError(error) {
  if (error instanceof Error) {
    return error.message;
  }

  return "Unknown dashboard error";
}


export default function App() {
  const [violations, setViolations] = useState([]);
  const [health, setHealth] = useState({ status: "connecting", timestampUtc: null });
  const [lastRefresh, setLastRefresh] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function refreshData() {
      try {
        const [healthResponse, violationsResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/health`),
          fetch(`${API_BASE_URL}/api/violations?limit=25`),
        ]);

        if (!healthResponse.ok) {
          throw new Error(`Health check failed with ${healthResponse.status}`);
        }

        if (!violationsResponse.ok) {
          throw new Error(`Violation fetch failed with ${violationsResponse.status}`);
        }

        const [healthPayload, violationsPayload] = await Promise.all([
          healthResponse.json(),
          violationsResponse.json(),
        ]);

        if (cancelled) {
          return;
        }

        startTransition(() => {
          setHealth(healthPayload);
          setViolations(Array.isArray(violationsPayload) ? violationsPayload : []);
          setLastRefresh(new Date().toISOString());
          setError("");
        });
      } catch (refreshError) {
        if (cancelled) {
          return;
        }

        startTransition(() => {
          setError(normalizeError(refreshError));
          setHealth((currentHealth) => ({
            ...currentHealth,
            status: "degraded",
          }));
        });
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    refreshData();
    const intervalId = window.setInterval(refreshData, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  const metrics = useMemo(() => {
    const latestRecord = violations[0];
    const latestEvent = latestRecord?.event;
    const highestConfidence = violations.reduce((maxConfidence, currentRecord) => {
      const currentConfidence = currentRecord?.event?.confidence ?? 0;
      return Math.max(maxConfidence, currentConfidence);
    }, 0);

    return {
      activeFeedSize: violations.length,
      lastCamera: latestEvent?.cameraId ?? "No camera yet",
      lastModel: latestEvent?.model ?? "No model yet",
      highestConfidence,
      lastSeenAt: latestRecord?.receivedAtUtc ?? null,
    };
  }, [violations]);

  return (
    <div className="dashboard-shell">
      <div className="dashboard-noise" aria-hidden="true" />

      <main className="dashboard">
        <section className="hero-panel">
          <div className="hero-copy">
            <p className="eyebrow">Smart Building + Loss Prevention</p>
            <h1>OmniGuard AI Operator Console</h1>
            <p className="hero-text">
              Live event feed for line-crossing incidents, backend health, and model telemetry.
              This panel is tuned for demo visibility rather than admin clutter.
            </p>
          </div>

          <div className="hero-status">
            <StatusBadge status={health.status} />
            <p className="status-meta">API: {API_BASE_URL}</p>
            <p className="status-meta">Last refresh: {formatTimestamp(lastRefresh)}</p>
            <p className="status-meta">Health timestamp: {formatTimestamp(health.timestampUtc)}</p>
          </div>
        </section>

        <section className="metrics-grid">
          <MetricCard label="Feed Items" value={metrics.activeFeedSize} accent="amber" />
          <MetricCard label="Last Camera" value={metrics.lastCamera} accent="teal" />
          <MetricCard label="Model" value={metrics.lastModel} accent="sand" />
          <MetricCard
            label="Peak Confidence"
            value={`${(metrics.highestConfidence * 100).toFixed(1)}%`}
            accent="coral"
          />
        </section>

        <section className="content-grid">
          <div className="panel panel-brief">
            <div className="panel-header">
              <p className="eyebrow">System Brief</p>
              <h2>Demo Readiness</h2>
            </div>
            <p className="brief-copy">
              The dashboard polls the backend every 2.5 seconds. The latest incident stays at the
              top, and the panel is intentionally optimized for quick operator scanning in a live
              demo or control room walkthrough.
            </p>
            <div className="brief-list">
              <div>
                <span>Latest event time</span>
                <strong>{formatTimestamp(metrics.lastSeenAt)}</strong>
              </div>
              <div>
                <span>Feed mode</span>
                <strong>Polling /api/violations</strong>
              </div>
              <div>
                <span>Health route</span>
                <strong>/health</strong>
              </div>
            </div>
          </div>

          <ViolationFeed violations={violations} error={error} isLoading={isLoading} />
        </section>
      </main>
    </div>
  );
}
