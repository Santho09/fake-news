import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from "chart.js";
import { Bar, Doughnut } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend);

function VerdictBadge({ verdict, color }) {
  const cls =
    verdict === "FAKE NEWS"
      ? "badge badgeFake"
      : verdict === "UNCERTAIN"
      ? "badge badgeWarn"
      : "badge badgeReal";
  return (
    <span className={cls} title={color || ""}>
      {verdict || "—"}
    </span>
  );
}

function ExplanationBlock({ explanation }) {
  if (!explanation) return null;

  const summary = explanation.summary || {};
  const humanReasons = explanation.human_reasons || [];
  const style = explanation.writing_style_signals?.signals || [];
  const factWarnings = explanation.fact_check?.warnings || [];

  const fakeDrivers = explanation.model_keyword_evidence?.fake_drivers || [];
  const realDrivers = explanation.model_keyword_evidence?.real_drivers || [];
  const verdict = summary?.verdict || "UNKNOWN";
  const confidence = summary?.confidence;
  const narrative = summary?.narrative;
  const fakeKeywordCount = fakeDrivers.length;
  const realKeywordCount = realDrivers.length;
  const modelLeansReal = realKeywordCount >= fakeKeywordCount;

  return (
    <div className="card">
      <div className="cardTitle">Why this verdict was given</div>

      <div className="section">
        <div className="sectionLabel">Simple explanation</div>
        <div className="plainExplain">
          {narrative ? (
            narrative
          ) : (
            <>
              This article is currently judged as <b>{verdict}</b>
              {typeof confidence === "number" ? (
                <>
                  {" "}
                  with <b>{confidence}%</b> confidence.
                </>
              ) : (
                "."
              )}
            </>
          )}
        </div>
      </div>

      <div className="section">
        <div className="sectionLabel">Top reasons in plain language</div>
        <ul className="list">
          {humanReasons.slice(0, 3).map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      </div>

      <div className="section">
        <div className="sectionLabel">Writing style check</div>
        <ul className="list">
          {style.length ? (
            style.map((s, i) => <li key={i}>{s}</li>)
          ) : (
            <li>No style red-flags detected.</li>
          )}
        </ul>
      </div>

      {factWarnings.length ? (
        <div className="section">
          <div className="sectionLabel">Fact-check findings</div>
          <ul className="list">
            {factWarnings.slice(0, 4).map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="section">
        <div className="sectionLabel">Model language pattern summary</div>
        <div className="plainExplain">
          {modelLeansReal ? (
            <>
              The model saw more language patterns associated with <b>REAL</b> news
              ({realKeywordCount} real-leaning cues vs {fakeKeywordCount} fake-leaning cues).
            </>
          ) : (
            <>
              The model saw more language patterns associated with <b>FAKE</b> news
              ({fakeKeywordCount} fake-leaning cues vs {realKeywordCount} real-leaning cues).
            </>
          )}
        </div>

        <details className="techDetails">
          <summary>Show technical keyword details</summary>
          <div className="grid2" style={{ marginTop: "10px" }}>
            <div className="miniCard">
              <div className="miniTitle">Toward FAKE (technical)</div>
              {fakeDrivers.length ? (
                <ul className="list">
                  {fakeDrivers.slice(0, 6).map((d, i) => (
                    <li key={i}>
                      <b>{d.keyword}</b> (score {d.score})
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="muted">Not available.</div>
              )}
            </div>

            <div className="miniCard">
              <div className="miniTitle">Toward REAL (technical)</div>
              {realDrivers.length ? (
                <ul className="list">
                  {realDrivers.slice(0, 6).map((d, i) => (
                    <li key={i}>
                      <b>{d.keyword}</b> (score {d.score})
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="muted">Not available.</div>
              )}
            </div>
          </div>
        </details>
        <div className="smallNote">
          Note: technical keywords are stemmed machine features and may look shortened.
        </div>
      </div>
    </div>
  );
}

function ExplainabilityCharts({ result, explanation }) {
  if (!result) return null;

  const individual = result?.individual_results || {};
  const modelNames = Object.keys(individual);

  const fakeProbs = modelNames.map((name) => Number(individual[name]?.fake_probability || 0));
  const realProbs = modelNames.map((name) => Number(individual[name]?.real_probability || 0));

  const voteData = {
    labels: ["Fake votes", "Real votes"],
    datasets: [
      {
        data: [Number(result?.fake_votes || 0), Number(result?.real_votes || 0)],
        backgroundColor: ["rgba(239, 68, 68, 0.75)", "rgba(16, 185, 129, 0.75)"],
        borderColor: ["rgba(239, 68, 68, 1)", "rgba(16, 185, 129, 1)"],
        borderWidth: 1,
      },
    ],
  };

  const modelProbData = {
    labels: modelNames,
    datasets: [
      {
        label: "Fake probability (%)",
        data: fakeProbs,
        backgroundColor: "rgba(239, 68, 68, 0.6)",
      },
      {
        label: "Real probability (%)",
        data: realProbs,
        backgroundColor: "rgba(16, 185, 129, 0.6)",
      },
    ],
  };

  const breakdown = explanation?.evidence_breakdown || {};
  const agreementPct = Number(breakdown?.model_agreement_percent ?? 0);
  const voteMarginPct = Number(breakdown?.vote_margin_percent ?? 0);
  const finalConfidencePct = Number(
    breakdown?.final_confidence_percent ??
      result?.adjusted_confidence ??
      result?.confidence ??
      0
  );
  const styleSignalCount = Number(
    breakdown?.style_signal_count ??
      explanation?.writing_style_signals?.clickbait_hits?.length ??
      explanation?.writing_style_signals?.signals?.length ??
      0
  );
  const factIssueCount = Number(
    breakdown?.fact_check_issue_count ??
      explanation?.fact_check?.warnings?.length ??
      result?.fact_check?.warnings?.length ??
      0
  );
  const fakeKeywordCount = Number(
    breakdown?.fake_keyword_count ??
      explanation?.model_keyword_evidence?.fake_drivers?.length ??
      0
  );
  const realKeywordCount = Number(
    breakdown?.real_keyword_count ??
      explanation?.model_keyword_evidence?.real_drivers?.length ??
      0
  );

  const insightScoreData = {
    labels: ["Model agreement %", "Final confidence %", "Vote margin %"],
    datasets: [
      {
        label: "Insight score",
        data: [agreementPct, finalConfidencePct, voteMarginPct],
        backgroundColor: [
          "rgba(99, 102, 241, 0.65)",
          "rgba(16, 185, 129, 0.65)",
          "rgba(245, 158, 11, 0.65)",
        ],
      },
    ],
  };

  const evidenceData = {
    labels: ["Style signals", "Fact-check issues", "Fake keywords", "Real keywords"],
    datasets: [
      {
        label: "Evidence count",
        data: [
          styleSignalCount,
          factIssueCount,
          fakeKeywordCount,
          realKeywordCount,
        ],
        backgroundColor: [
          "rgba(99, 102, 241, 0.65)",
          "rgba(245, 158, 11, 0.65)",
          "rgba(239, 68, 68, 0.65)",
          "rgba(16, 185, 129, 0.65)",
        ],
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: "rgba(255,255,255,0.85)" },
      },
    },
    scales: {
      x: {
        ticks: { color: "rgba(255,255,255,0.75)" },
        grid: { color: "rgba(255,255,255,0.08)" },
      },
      y: {
        beginAtZero: true,
        ticks: { color: "rgba(255,255,255,0.75)" },
        grid: { color: "rgba(255,255,255,0.08)" },
      },
    },
  };

  return (
    <div className="card">
      <div className="cardTitle">Model insights graph</div>
      <div className="chartsGrid">
        <div className="chartPanel">
          <div className="sectionLabel">Per-model probability comparison</div>
          <div className="chartWrap">
            <Bar data={modelProbData} options={chartOptions} />
          </div>
        </div>

        <div className="chartPanel">
          <div className="sectionLabel">Ensemble vote split</div>
          <div className="chartWrap">
            <Doughnut
              data={voteData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { labels: { color: "rgba(255,255,255,0.85)" } },
                },
              }}
            />
          </div>
        </div>
      </div>

      <div className="chartPanel" style={{ marginTop: "12px" }}>
        <div className="sectionLabel">Decision strength (always available)</div>
        <div className="chartWrap">
          <Bar data={insightScoreData} options={chartOptions} />
        </div>
      </div>

      <div className="chartPanel" style={{ marginTop: "12px" }}>
        <div className="sectionLabel">Evidence balance used by explainability</div>
        <div className="chartWrap">
          <Bar data={evidenceData} options={chartOptions} />
        </div>
      </div>
    </div>
  );
}

export default function UserDashboard() {
  const [text, setText] = useState("");
  const [factCheckMode, setFactCheckMode] = useState("wikipedia");

  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchHistory = async () => {
    const res = await api.get("/api/history");
    setHistory(res.data.submissions || []);
  };

  useEffect(() => {
    fetchHistory().catch(() => {});
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.post("/api/predict", { text, fact_check_mode: factCheckMode });
      setResult(res.data);
      setText("");
      await fetchHistory();
    } catch (err) {
      setError(err?.response?.data?.error || "Prediction failed");
    } finally {
      setLoading(false);
    }
  };

  const verdict = result?.final_verdict || result?.prediction;
  const confidence = result?.adjusted_confidence ?? result?.confidence;
  const verdictColor = result?.verdict_color;

  return (
    <div className="container">
      <header className="topbar">
        <div className="brand">
          <div className="logoMark">N</div>
          <div>
            <div className="brandName">NewsVeritas</div>
            <div className="brandSub">User Panel</div>
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

      <div className="layout">
        <div className="mainCol">
          <div className="card">
            <div className="cardTitle">Check a news article</div>
            <form onSubmit={submit}>
              <label className="label">Article text</label>
              <textarea
                className="textarea"
                rows={8}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste the full news text here…"
              />

              <div className="row">
                <div className="col">
                  <label className="label">Fact-check mode (optional)</label>
                  <select
                    className="input"
                    value={factCheckMode}
                    onChange={(e) => setFactCheckMode(e.target.value)}
                  >
                    <option value="wikipedia">Wikipedia mode</option>
                    <option value="google">Google Fact Check (if configured)</option>
                  </select>
                </div>
              </div>

              {error ? <div className="errorBox">{error}</div> : null}

              <button className="btn" disabled={loading}>
                {loading ? "Analyzing…" : "Analyze"}
              </button>
            </form>
          </div>

          {result ? (
            <div className="card">
              <div className="cardTitle">Result</div>
              <div className="resultRow">
                <VerdictBadge verdict={verdict} color={verdictColor} />
                <div className="confidence">
                  Confidence: <b>{typeof confidence === "number" ? confidence : "—"}%</b>
                </div>
              </div>
              <div className="muted">
                Ensemble decision: {result?.decision_type} (Fake votes: {result?.fake_votes}, Real votes:{" "}
                {result?.real_votes})
              </div>
              {result?.fact_check && result?.fact_check.warnings?.length ? (
                <div className="muted" style={{ marginTop: "8px" }}>
                  Fact-checker adjustment (mode: {result?.fact_check?.selected_mode || "wikipedia"}): final verdict was forced to{" "}
                  <b>{result?.final_verdict || verdict}</b>.
                </div>
              ) : result?.fact_check ? (
                <div className="muted" style={{ marginTop: "8px" }}>
                  Fact-checker found no issues (mode: {result?.fact_check?.selected_mode || "wikipedia"}), so the ML ensemble verdict is used.
                </div>
              ) : null}
              {result?.fact_check_reason ? (
                <div className="muted" style={{ marginTop: "8px" }}>
                  Reason for adjustment: {result?.fact_check_reason}
                </div>
              ) : null}
              {result?.final_verdict && result?.prediction && result?.final_verdict !== result?.prediction ? (
                <div className="muted" style={{ marginTop: "8px" }}>
                  ML ensemble predicted <b>{result?.prediction}</b>, but the final verdict was adjusted to <b>{result?.final_verdict}</b>.
                </div>
              ) : null}
              {result?.explanation?.summary?.narrative ? (
                <div className="section" style={{ marginTop: "10px" }}>
                  <div className="sectionLabel">Plain-language verdict</div>
                  <div className="muted">{result.explanation.summary.narrative}</div>
                </div>
              ) : null}
            </div>
          ) : null}

          <ExplainabilityCharts result={result} explanation={result?.explanation} />
          <ExplanationBlock explanation={result?.explanation} />
        </div>

        <aside className="sideCol">
          <div className="card">
            <div className="cardTitle">Your recent checks</div>
            {history.length ? (
              <div className="historyList">
                {history.map((h) => (
                  <div key={h.id} className="historyItem">
                    <div className="historyTop">
                      <VerdictBadge verdict={h.verdict} color={h.verdict_color} />
                      <div className="historyTime">{h.created_at ? h.created_at.replace("T", " ") : ""}</div>
                    </div>
                    <div className="historyText">{h.text.slice(0, 90)}{h.text.length > 90 ? "…" : ""}</div>
                    <button
                      className="linkBtn"
                      onClick={() => {
                        setResult({
                          prediction: h.prediction,
                          final_verdict: h.verdict,
                          confidence: h.ml_confidence,
                          adjusted_confidence: h.confidence,
                          verdict_color: h.verdict_color,
                          decision_type: h.decision_type,
                          fake_votes: h.fake_votes,
                          real_votes: h.real_votes,
                          individual_results: h.individual_results,
                          explanation: h.explanation,
                        });
                      }}
                    >
                      View explanation
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="muted">No checks yet.</div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

