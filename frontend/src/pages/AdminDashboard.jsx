import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { Bar, Doughnut, Line } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Tooltip,
  Legend
);

function formatTs(iso) {
  if (!iso) return "—";
  return String(iso).replace("T", " ").slice(0, 19);
}

function verdictPillClass(v) {
  if (v === "FAKE NEWS") return "pill pillFake";
  if (v === "REAL NEWS") return "pill pillReal";
  if (v === "UNCERTAIN") return "pill pillUncertain";
  return "pill pillUser";
}

function VerdictMixBar({ fakePct, realPct, uncPct }) {
  const t = (fakePct || 0) + (realPct || 0) + (uncPct || 0);
  if (t <= 0) {
    return (
      <div className="muted small" style={{ minWidth: 120 }}>
        No scans
      </div>
    );
  }
  const f = (100 * (fakePct || 0)) / t;
  const r = (100 * (realPct || 0)) / t;
  const u = Math.max(0, 100 - f - r);
  return (
    <div>
      <div className="verdictBar" title={`Fake ${fakePct}% · Real ${realPct}% · Uncertain ${uncPct}%`}>
        <div className="seg segFake" style={{ width: `${f}%` }} />
        <div className="seg segReal" style={{ width: `${r}%` }} />
        <div className="seg segUnc" style={{ width: `${u}%` }} />
      </div>
      <div className="verdictBarLegend">
        F {fakePct ?? 0}% · R {realPct ?? 0}% · U {uncPct ?? 0}%
      </div>
    </div>
  );
}

function UserFullScreenDetail({ user, open, onClose }) {
  const [subs, setSubs] = useState([]);
  const [subMeta, setSubMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const loadSubs = useCallback(async () => {
    if (!user?.id) return;
    setLoading(true);
    setErr("");
    try {
      const res = await api.get(`/api/admin/users/${user.id}/submissions`, {
        params: { limit: 10000 },
      });
      setSubs(res.data.submissions || []);
      setSubMeta(res.data.submission_meta || null);
    } catch (e) {
      setErr(e?.response?.data?.error || "Could not load user activity");
      setSubs([]);
      setSubMeta(null);
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    if (open && user?.id) loadSubs();
  }, [open, user?.id, loadSubs]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  const a = user?.analytics || {};
  const isLightTheme =
    typeof document !== "undefined" && document.body.getAttribute("data-theme") === "light";
  const chartLegendColor = isLightTheme ? "#14081f" : "#cbd5e1";
  const breakdown = a.verdict_breakdown || {};
  const doughnut = useMemo(() => {
    const labels = [];
    const data = [];
    const colors = [];
    const add = (label, val, color) => {
      if (val > 0) {
        labels.push(label);
        data.push(val);
        colors.push(color);
      }
    };
    add("Fake", breakdown["FAKE NEWS"] || 0, "rgba(239, 68, 68, 0.85)");
    add("Real", breakdown["REAL NEWS"] || 0, "rgba(16, 185, 129, 0.85)");
    add("Uncertain", breakdown["UNCERTAIN"] || 0, "rgba(245, 158, 11, 0.85)");
    Object.keys(breakdown).forEach((k) => {
      if (!["FAKE NEWS", "REAL NEWS", "UNCERTAIN"].includes(k)) {
        add(k || "Other", breakdown[k], "rgba(148, 163, 184, 0.75)");
      }
    });
    if (!data.length) {
      labels.push("No activity");
      data.push(1);
      colors.push("rgba(148, 163, 184, 0.35)");
    }
    return {
      labels,
      datasets: [
        {
          data,
          backgroundColor: colors,
          borderWidth: 0,
        },
      ],
    };
  }, [breakdown]);

  if (!open || !user) return null;

  return (
    <div className="adminUserFullscreen" role="dialog" aria-modal="true" aria-labelledby="admin-user-fs-title">
      <header className="adminUserFullscreenHeader">
        <div className="adminUserFullscreenTitleBlock">
          <h2 id="admin-user-fs-title" className="adminUserFullscreenTitle">
            {user.username}
          </h2>
          <div className="adminUserFullscreenSub">
            <span className={user.role === "admin" ? "pill pillAdmin" : "pill pillUser"}>{user.role}</span>
            <span className="userCellId">ID {user.id}</span>
            <span className="muted">Registered {formatTs(user.created_at)}</span>
          </div>
        </div>
        <div className="adminUserFullscreenActions">
          <button type="button" className="adminUserFullscreenBack" onClick={onClose}>
            ← Back to directory
          </button>
        </div>
      </header>

      <div className="adminUserFullscreenBody">
        <div className="adminUserFullscreenInner">
          <div className="adminUserStatGrid">
            <div className="adminUserStatTile">
              <div className="lbl">Total scans</div>
              <div className="val">{a.total_submissions ?? 0}</div>
            </div>
            <div className="adminUserStatTile">
              <div className="lbl">Fake</div>
              <div className="val" style={{ color: "#fca5a5" }}>
                {a.fake_count ?? 0}
              </div>
            </div>
            <div className="adminUserStatTile">
              <div className="lbl">Real</div>
              <div className="val" style={{ color: "#6ee7b7" }}>
                {a.real_count ?? 0}
              </div>
            </div>
            <div className="adminUserStatTile">
              <div className="lbl">Uncertain</div>
              <div className="val" style={{ color: "#fcd34d" }}>
                {a.uncertain_count ?? 0}
              </div>
            </div>
            <div className="adminUserStatTile">
              <div className="lbl">Last 7 days</div>
              <div className="val">{a.submissions_last_7d ?? 0}</div>
            </div>
            <div className="adminUserStatTile">
              <div className="lbl">Avg confidence</div>
              <div className="val" style={{ fontSize: 20 }}>
                {a.avg_confidence != null ? `${a.avg_confidence}%` : "—"}
              </div>
            </div>
            <div className="adminUserStatTile">
              <div className="lbl">First activity</div>
              <div className="val" style={{ fontSize: 15, fontWeight: 700 }}>
                {formatTs(a.first_activity_at)}
              </div>
            </div>
            <div className="adminUserStatTile">
              <div className="lbl">Last activity</div>
              <div className="val" style={{ fontSize: 15, fontWeight: 700 }}>
                {formatTs(a.last_activity_at)}
              </div>
            </div>
          </div>

          <div className="adminUserSplit">
            <div className="adminUserChartBox">
              <div className="adminDrawerSectionTitle" style={{ marginTop: 0 }}>
                Verdict distribution
              </div>
              <div className="chartRingWrap">
                <Doughnut
                  data={doughnut}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: { position: "bottom", labels: { color: chartLegendColor, boxWidth: 10 } },
                    },
                  }}
                />
              </div>
              <div className="adminDrawerSectionTitle">Fact-check mode</div>
              <div className="muted small" style={{ lineHeight: 1.6 }}>
                {Object.keys(a.fact_check_mode_breakdown || {}).length ? (
                  Object.entries(a.fact_check_mode_breakdown).map(([k, v]) => (
                    <div key={k}>
                      <strong>{k}</strong>: {v}
                    </div>
                  ))
                ) : (
                  <span>—</span>
                )}
              </div>
            </div>

            <div>
              <h3 className="adminUserArticlesHead">
                Complete submitted text
                {!loading && subs.length ? (
                  <span className="muted" style={{ fontWeight: 600, textTransform: "none", letterSpacing: 0 }}>
                    {subs.length} article{subs.length === 1 ? "" : "s"} (#1 = most recent)
                    {subMeta?.total_in_database != null && subMeta.total_in_database !== subs.length
                      ? ` · ${subMeta.total_in_database} total in database`
                      : ""}
                  </span>
                ) : null}
              </h3>

              {loading ? <div className="muted">Loading all submissions…</div> : null}
              {err ? <div className="errorBox">{err}</div> : null}

              {subMeta?.truncated ? (
                <div className="adminUserTruncationNote">
                  Showing {subMeta.returned} of {subMeta.total_in_database} submissions (server limit{" "}
                  {subMeta.limit_applied}). Increase limit in the API if you need the rest.
                </div>
              ) : null}

              {!loading && !subs.length && !err ? (
                <div className="muted">No submissions for this user.</div>
              ) : null}

              {subs.map((s, idx) => (
                <article className="adminUserArticleCard" key={s.id}>
                  <div className="adminUserArticleMeta">
                    <div className="adminUserArticleMetaLeft">
                      <span className="muted small" style={{ fontWeight: 700 }}>
                        #{idx + 1}
                      </span>
                      <span className={verdictPillClass(s.verdict)}>{s.verdict || "—"}</span>
                      {typeof s.confidence === "number" ? (
                        <span className="muted small">Confidence {s.confidence}%</span>
                      ) : null}
                      {s.ml_confidence != null && s.ml_confidence !== s.confidence ? (
                        <span className="muted small">ML {s.ml_confidence}%</span>
                      ) : null}
                      {s.fact_check_mode ? (
                        <span className="pill pillUser" style={{ fontSize: 11 }}>
                          {s.fact_check_mode}
                        </span>
                      ) : null}
                      {s.decision_type ? (
                        <span className="muted small" title={s.decision_type}>
                          {s.decision_type.length > 40 ? `${s.decision_type.slice(0, 40)}…` : s.decision_type}
                        </span>
                      ) : null}
                    </div>
                    <span className="muted small">{formatTs(s.created_at)}</span>
                  </div>
                  <div className="adminUserArticleBody">{s.text || "(No text stored)"}</div>
                </article>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AdminDashboard() {
  const [section, setSection] = useState("operations");
  const [overview, setOverview] = useState(null);
  const [userRows, setUserRows] = useState([]);
  const [subs, setSubs] = useState([]);
  const [modelMetrics, setModelMetrics] = useState(null);
  const [calibrationModel, setCalibrationModel] = useState("ensemble");
  const [search, setSearch] = useState("");
  const [selectedUser, setSelectedUser] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const isLightTheme =
    typeof document !== "undefined" && document.body.getAttribute("data-theme") === "light";
  const chartTextColor = isLightTheme ? "#14081f" : "#cbd5e1";
  const chartMutedColor = isLightTheme ? "#3e2860" : "#94a3b8";
  const chartGridColor = isLightTheme ? "rgba(20,8,31,0.16)" : "rgba(255,255,255,0.06)";

  const load = async () => {
    setError("");
    setLoading(true);
    try {
      const [o, ua, s, m] = await Promise.all([
        api.get("/api/admin/overview"),
        api.get("/api/admin/user-analytics"),
        api.get("/api/admin/submissions"),
        api.get("/api/admin/model-metrics").catch(() => null),
      ]);
      setOverview(o.data.overview);
      setUserRows(ua.data.users || []);
      setSubs(s.data.submissions || []);
      setModelMetrics(m?.data?.metrics || null);
    } catch (e) {
      setError(e?.response?.data?.error || "Failed to load admin data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const phase3 = modelMetrics?.phase3;

  const kpis = useMemo(() => {
    const totalSub = overview?.totalSubmissions ?? 0;
    const active = userRows.filter((u) => (u.analytics?.total_submissions || 0) > 0).length;
    const sumUnc = userRows.reduce((acc, u) => acc + (u.analytics?.uncertain_count || 0), 0);
    const sumAll = userRows.reduce((acc, u) => acc + (u.analytics?.total_submissions || 0), 0);
    const uncRate = sumAll > 0 ? Math.round((1000 * sumUnc) / sumAll) / 10 : 0;
    const avgPerActive = active > 0 ? Math.round((10 * totalSub) / active) / 10 : 0;
    return {
      totalSub,
      userAccounts: userRows.length,
      active,
      avgPerActive,
      uncRate,
    };
  }, [overview, userRows]);

  const filteredUsers = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return userRows;
    return userRows.filter(
      (u) =>
        (u.username || "").toLowerCase().includes(q) ||
        (u.id || "").toLowerCase().includes(q) ||
        (u.role || "").toLowerCase().includes(q)
    );
  }, [userRows, search]);

  const calibrationChart = useMemo(() => {
    const curves = phase3?.calibration_curves;
    if (!curves) return null;
    let meanPred = [];
    let fracPos = [];
    if (calibrationModel === "ensemble") {
      meanPred = curves.ensemble_weighted_fake_prob?.mean_predicted ?? [];
      fracPos = curves.ensemble_weighted_fake_prob?.fraction_positive ?? [];
    } else {
      const m = curves.per_model_fake_prob?.[calibrationModel];
      meanPred = m?.mean_predicted ?? [];
      fracPos = m?.fraction_positive ?? [];
    }
    if (!meanPred.length) return null;
    const observed = meanPred.map((x, i) => ({ x, y: fracPos[i] ?? 0 }));
    const lo = Math.min(...meanPred, 0);
    const hi = Math.max(...meanPred, 1);
    const diag = [
      { x: lo, y: lo },
      { x: hi, y: hi },
    ];
    return {
      datasets: [
        {
          label: "Observed frequency (fake)",
          data: observed,
          borderColor: "rgba(56, 189, 248, 1)",
          backgroundColor: "rgba(56, 189, 248, 0.2)",
          pointRadius: 4,
          tension: 0.15,
          showLine: true,
          parsing: false,
        },
        {
          label: "Perfect calibration",
          data: diag,
          borderColor: "rgba(148, 163, 184, 0.9)",
          borderDash: [6, 4],
          pointRadius: 0,
          fill: false,
          showLine: true,
          parsing: false,
        },
      ],
    };
  }, [phase3, calibrationModel]);

  const topicChart = useMemo(() => {
    const rows = phase3?.topic_error_analysis;
    if (!rows?.length) return null;
    const labels = rows.map((r) => r.topic);
    const acc = rows.map((r) => Math.round((r.accuracy ?? 0) * 1000) / 10);
    const fnr = rows.map((r) => Math.round((r.fnr ?? 0) * 1000) / 10);
    return {
      labels,
      datasets: [
        { label: "Accuracy %", data: acc, backgroundColor: "rgba(16, 185, 129, 0.55)" },
        { label: "False negative rate %", data: fnr, backgroundColor: "rgba(248, 113, 113, 0.55)" },
      ],
    };
  }, [phase3]);

  const calOptions = useMemo(() => {
    const names = phase3?.calibration_curves?.per_model_fake_prob
      ? Object.keys(phase3.calibration_curves.per_model_fake_prob)
      : [];
    return ["ensemble", ...names];
  }, [phase3]);

  const openUser = (u) => {
    setSelectedUser(u);
    setDrawerOpen(true);
  };

  const handleSignOut = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    window.location.href = "/login";
  };

  return (
    <div className="adminApp">
      <aside className="adminSidebar">
        <div className="adminBrand">
          <div className="adminLogo">NV</div>
          <div className="adminBrandText">
            <div className="adminProduct">NewsVeritas</div>
            <div className="adminEnv">Admin console</div>
          </div>
        </div>
        <nav className="adminNav" aria-label="Primary">
          <button
            type="button"
            className={`adminNavBtn ${section === "operations" ? "active" : ""}`}
            onClick={() => setSection("operations")}
          >
            <span className="adminNavIcon">◎</span>
            Operations
          </button>
          <button
            type="button"
            className={`adminNavBtn ${section === "models" ? "active" : ""}`}
            onClick={() => setSection("models")}
          >
            <span className="adminNavIcon">◇</span>
            Model quality
          </button>
        </nav>
        <div className="adminSidebarFoot">
          <Link
            to="/home"
            className="adminBtnGhost"
            style={{ textDecoration: "none", textAlign: "center", display: "block" }}
          >
            Home
          </Link>
          <button type="button" className="adminBtnGhost" onClick={() => load()} disabled={loading}>
            Refresh data
          </button>
          <button
            type="button"
            className="adminBtnGhost"
            onClick={() => {
              localStorage.removeItem("token");
              localStorage.removeItem("role");
              window.location.href = "/login";
            }}
          >
            Sign out
          </button>
        </div>
      </aside>

      <main className="adminMain">
        {error ? <div className="errorBox" style={{ marginBottom: 16 }}>{error}</div> : null}

        {section === "operations" ? (
          <>
            <div className="adminTopRow">
              <div>
                <h1 className="adminPageTitle">User intelligence</h1>
                <p className="adminPageSub">
                  Monitor each account’s verification activity, verdict mix, and recency. Open a row to audit
                  individual submissions and usage patterns—similar to an enterprise trust &amp; safety console.
                </p>
              </div>
              <div className="adminTopActions">
                <button type="button" className="adminBtnGhost" onClick={handleSignOut}>
                  Sign out
                </button>
              </div>
            </div>

            <div className="adminKpiGrid">
              <div className="adminKpi">
                <div className="adminKpiLabel">Total scans</div>
                <div className="adminKpiValue">{kpis.totalSub}</div>
                <div className="adminKpiHint">Across all users</div>
              </div>
              <div className="adminKpi">
                <div className="adminKpiLabel">Active analysts</div>
                <div className="adminKpiValue">
                  {kpis.active}
                  <span className="muted small" style={{ fontWeight: 600, marginLeft: 6 }}>
                    / {kpis.userAccounts}
                  </span>
                </div>
                <div className="adminKpiHint">Users with ≥1 submission</div>
              </div>
              <div className="adminKpi">
                <div className="adminKpiLabel">Avg scans / active user</div>
                <div className="adminKpiValue">{kpis.avgPerActive}</div>
                <div className="adminKpiHint">Workload signal</div>
              </div>
              <div className="adminKpi">
                <div className="adminKpiLabel">Uncertain share</div>
                <div className="adminKpiValue">{kpis.uncRate}%</div>
                <div className="adminKpiHint">Of all stored verdicts</div>
              </div>
            </div>

            <div className="adminPanel" style={{ marginBottom: 20 }}>
              <div className="adminPanelHead">
                <h2 className="adminPanelTitle">Directory</h2>
                <input
                  className="adminSearch"
                  placeholder="Search name, id, or role…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  aria-label="Filter users"
                />
              </div>
              <div className="adminTableWrap">
                <table className="adminTable">
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Role</th>
                      <th>Scans</th>
                      <th>Verdict mix</th>
                      <th>Avg conf.</th>
                      <th>7d</th>
                      <th>Last active</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredUsers.map((u) => {
                      const a = u.analytics || {};
                      const active = (a.total_submissions || 0) > 0;
                      return (
                        <tr
                          key={u.id}
                          className={`userRow ${selectedUser?.id === u.id ? "selected" : ""}`}
                          onClick={() => openUser(u)}
                        >
                          <td>
                            <div className="userCellMain">
                              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                <span className={active ? "statusDot live" : "statusDot idle"} aria-hidden />
                                <span className="userCellName">{u.username}</span>
                              </div>
                              <span className="userCellId">{u.id}</span>
                            </div>
                          </td>
                          <td>
                            <span className={u.role === "admin" ? "pill pillAdmin" : "pill pillUser"}>{u.role}</span>
                          </td>
                          <td>
                            <strong>{a.total_submissions ?? 0}</strong>
                          </td>
                          <td>
                            <VerdictMixBar
                              fakePct={a.fake_share_pct}
                              realPct={a.real_share_pct}
                              uncPct={a.uncertain_share_pct}
                            />
                          </td>
                          <td>{a.avg_confidence != null ? `${a.avg_confidence}%` : "—"}</td>
                          <td>{a.submissions_last_7d ?? 0}</td>
                          <td className="muted small">{formatTs(a.last_activity_at)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {!filteredUsers.length ? (
                  <div className="muted" style={{ padding: 20 }}>
                    {loading ? "Loading…" : "No users match your filter."}
                  </div>
                ) : null}
              </div>
            </div>

            <div className="adminPanel">
              <div className="adminPanelHead">
                <h2 className="adminPanelTitle">Live activity stream</h2>
                <span className="muted small">Latest across the organization</span>
              </div>
              <div style={{ padding: 16 }}>
                {subs.length ? (
                  <div className="table">
                    {subs.slice(0, 25).map((s) => (
                      <div className="tableRow" key={s.id}>
                        <div className="tableCell">
                          <div className="muted">Verdict</div>
                          <div className={verdictPillClass(s.verdict)}>{s.verdict}</div>
                        </div>
                        <div className="tableCell">
                          <div className="muted">Confidence</div>
                          <div>{typeof s.confidence === "number" ? `${s.confidence}%` : "—"}</div>
                        </div>
                        <div className="tableCell">
                          <div className="muted">When</div>
                          <div>{formatTs(s.created_at)}</div>
                        </div>
                        <div className="tableCell wide">
                          <div className="muted">Preview</div>
                          <div className="truncate">
                            {s.text ? s.text.slice(0, 120) : ""}
                            {s.text?.length > 120 ? "…" : ""}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="muted">No submissions yet.</div>
                )}
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="adminTopRow">
              <div>
                <h1 className="adminPageTitle">Model quality</h1>
                <p className="adminPageSub">
                  Calibration, topic error analysis, and validation metrics from training. Use this alongside
                  per-user activity to explain divergent behavior in production.
                </p>
              </div>
              <div className="adminTopActions">
                <button type="button" className="adminBtnGhost" onClick={handleSignOut}>
                  Sign out
                </button>
              </div>
            </div>

            <div className="modelsSplit">
              <div className="adminPanel">
                <div className="adminPanelHead">
                  <h2 className="adminPanelTitle">Phase 3 — Calibration &amp; topics</h2>
                </div>
                <div style={{ padding: 18 }}>
                  {!phase3 ? (
                    <div className="muted">
                      Phase 3 metrics are not available in <code>model_metrics.json</code>.
                    </div>
                  ) : (
                    <>
                      {phase3.threshold_tuning_validation ? (
                        <div className="muted small" style={{ marginBottom: 12 }}>
                          Tuned uncertainty: confidence ≥{" "}
                          <strong>{phase3.threshold_tuning_validation.uncertainty_confidence_threshold}</strong>, gap ≥{" "}
                          <strong>{phase3.threshold_tuning_validation.uncertainty_gap_threshold}</strong>
                          {" — "}
                          macro-F1 (non-uncertain):{" "}
                          <strong>{phase3.threshold_tuning_validation.val_macro_f1_non_uncertain}</strong>
                        </div>
                      ) : null}
                      <div className="muted small" style={{ marginBottom: 8 }}>
                        Model:
                      </div>
                      <select
                        className="adminSearch"
                        style={{ width: "100%", marginBottom: 12 }}
                        value={calibrationModel}
                        onChange={(e) => setCalibrationModel(e.target.value)}
                      >
                        {calOptions.map((k) => (
                          <option key={k} value={k}>
                            {k === "ensemble" ? "Ensemble (weighted)" : k}
                          </option>
                        ))}
                      </select>
                      {calibrationChart ? (
                        <div style={{ height: 280 }}>
                          <Line
                            data={calibrationChart}
                            options={{
                              responsive: true,
                              maintainAspectRatio: false,
                              parsing: false,
                              scales: {
                                y: {
                                  type: "linear",
                                  min: 0,
                                  max: 1,
                                  title: { display: true, text: "Fraction positive (fake)", color: chartMutedColor },
                                  ticks: { color: chartMutedColor },
                                  grid: { color: chartGridColor },
                                },
                                x: {
                                  type: "linear",
                                  min: 0,
                                  max: 1,
                                  title: { display: true, text: "Mean predicted P(fake)", color: chartMutedColor },
                                  ticks: { color: chartMutedColor },
                                  grid: { color: chartGridColor },
                                },
                              },
                              plugins: {
                                legend: { position: "bottom", labels: { color: chartTextColor } },
                              },
                            }}
                          />
                        </div>
                      ) : (
                        <div className="muted small">No calibration bins.</div>
                      )}
                      <div className="adminDrawerSectionTitle" style={{ marginTop: 16 }}>
                        Per-topic accuracy
                      </div>
                      {topicChart ? (
                        <div style={{ height: 300 }}>
                          <Bar
                            data={topicChart}
                            options={{
                              responsive: true,
                              maintainAspectRatio: false,
                              scales: {
                                x: { stacked: false, ticks: { color: chartMutedColor }, grid: { color: chartGridColor } },
                                y: {
                                  min: 0,
                                  max: 100,
                                  title: { display: true, text: "%", color: chartMutedColor },
                                  ticks: { color: chartMutedColor },
                                  grid: { color: chartGridColor },
                                },
                              },
                              plugins: { legend: { position: "bottom", labels: { color: chartTextColor } } },
                            }}
                          />
                        </div>
                      ) : (
                        <div className="muted small">No topic breakdown.</div>
                      )}
                    </>
                  )}
                </div>
              </div>

              <div className="adminPanel">
                <div className="adminPanelHead">
                  <h2 className="adminPanelTitle">Validation metrics</h2>
                </div>
                <div style={{ padding: 16 }}>
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
                            Val LogLoss: {m?.validation?.log_loss ?? "—"} | Test:{" "}
                            {m?.test_calibrated?.log_loss ?? "—"}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="muted">Run retraining to generate model_metrics.json.</div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </main>

      <UserFullScreenDetail user={selectedUser} open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  );
}
