import React, { useEffect, useState } from "react";
import { api } from "../api/client";

function StatCard({ title, value, tone }) {
  return (
    <div className={`statCard ${tone || ""}`}>
      <div className="statTitle">{title}</div>
      <div className="statValue">{value ?? 0}</div>
    </div>
  );
}

export default function AdminDashboard() {
  const [overview, setOverview] = useState(null);
  const [users, setUsers] = useState([]);
  const [subs, setSubs] = useState([]);
  const [modelMetrics, setModelMetrics] = useState(null);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    const o = await api.get("/api/admin/overview");
    setOverview(o.data.overview);
    const u = await api.get("/api/admin/users");
    setUsers(u.data.users || []);
    const s = await api.get("/api/admin/submissions");
    setSubs(s.data.submissions || []);
    const m = await api.get("/api/admin/model-metrics").catch(() => null);
    setModelMetrics(m?.data?.metrics || null);
  };

  useEffect(() => {
    load().catch((e) => setError(e?.response?.data?.error || "Failed to load admin data"));
  }, []);

  return (
    <div className="container">
      <header className="topbar">
        <div className="brand">
          <div className="logoMark">N</div>
          <div>
            <div className="brandName">NewsVeritas</div>
            <div className="brandSub">Admin Panel</div>
          </div>
        </div>
        <div className="topActions">
          <button
            className="btnSecondary"
            onClick={() => {
              localStorage.removeItem("token");
              localStorage.removeItem("role");
              window.location.href = "/login";
            }}
          >
            Logout
          </button>
        </div>
      </header>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="gridStats">
        <StatCard title="Total submissions" value={overview?.totalSubmissions} />
        <StatCard title="Real" value={overview?.realCount} tone="toneReal" />
        <StatCard title="Fake" value={overview?.fakeCount} tone="toneFake" />
      </div>

      <div className="layout">
        <div className="mainCol">
          <div className="card">
            <div className="cardTitle">Recent submissions</div>
            {subs.length ? (
              <div className="table">
                {subs.map((s) => (
                  <div className="tableRow" key={s.id}>
                    <div className="tableCell">
                      <div className="muted">Verdict</div>
                      <div className={s.verdict === "FAKE NEWS" ? "pill pillFake" : "pill pillReal"}>
                        {s.verdict}
                      </div>
                    </div>
                    <div className="tableCell">
                      <div className="muted">Confidence</div>
                      <div>
                        {typeof s.confidence === "number" ? `${s.confidence}%` : "—"}
                      </div>
                    </div>
                    <div className="tableCell">
                      <div className="muted">When</div>
                      <div>{s.created_at ? s.created_at.replace("T", " ").slice(0, 19) : ""}</div>
                    </div>
                    <div className="tableCell wide">
                      <div className="muted">Preview</div>
                      <div className="truncate">{s.text ? s.text.slice(0, 110) : ""}{s.text?.length > 110 ? "…" : ""}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="muted">No submissions yet.</div>
            )}
          </div>
        </div>

        <aside className="sideCol">
          <div className="card">
            <div className="cardTitle">Users</div>
            {users.length ? (
              <div className="userList">
                {users.slice(0, 20).map((u) => (
                  <div className="userItem" key={u.id}>
                    <div className="userTop">
                      <div className="userName">{u.username}</div>
                      <div className={u.role === "admin" ? "pill pillAdmin" : "pill pillUser"}>
                        {u.role}
                      </div>
                    </div>
                    <div className="muted small">
                      {u.created_at ? u.created_at.replace("T", " ").slice(0, 19) : ""}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="muted">No users found.</div>
            )}
          </div>

          <div className="card">
            <div className="cardTitle">How admin analytics help</div>
            <div className="muted">
              The app stores each user’s article, the ensemble result, and a human-readable explanation.
              This makes it easy to review patterns and improve trust.
            </div>
          </div>

          <div className="card">
            <div className="cardTitle">Validation and calibration metrics</div>
            {modelMetrics?.models ? (
              <div className="userList">
                {Object.entries(modelMetrics.models).map(([name, m]) => (
                  <div className="userItem" key={name}>
                    <div className="userTop">
                      <div className="userName">{name}</div>
                      <div className="pill pillAdmin">calibrated</div>
                    </div>
                    <div className="muted small">
                      Val F1: {m?.validation?.f1 ?? "—"} | Test F1: {m?.test_calibrated?.f1 ?? "—"}
                    </div>
                    <div className="muted small">
                      Val LogLoss: {m?.validation?.log_loss ?? "—"} | Test LogLoss: {m?.test_calibrated?.log_loss ?? "—"}
                    </div>
                    <div className="muted small">
                      Brier gain: {m?.calibration_gain?.brier_delta ?? "—"} | LogLoss gain: {m?.calibration_gain?.log_loss_delta ?? "—"}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="muted">
                Metrics not available yet. Run retraining to generate `model_metrics.json`.
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

