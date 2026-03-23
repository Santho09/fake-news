import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
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

function HighlightedText({ text, spans, verdict }) {
  if (!text) return null;
  if (!spans?.length) {
    return (
      <div className="highlightedTextBlock" style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
        {text}
      </div>
    );
  }
  const parts = [];
  let lastEnd = 0;
  spans
    .slice()
    .sort((a, b) => a.start - b.start)
    .forEach((s) => {
      if (s.start > lastEnd) {
        parts.push({ type: "plain", text: text.slice(lastEnd, s.start) });
      }
      parts.push({
        type: "highlight",
        text: text.slice(s.start, s.end),
        spanType: s.type,
        keyword: s.keyword,
      });
      lastEnd = Math.max(lastEnd, s.end);
    });
  if (lastEnd < text.length) {
    parts.push({ type: "plain", text: text.slice(lastEnd) });
  }
  return (
    <div className="highlightedTextBlock" style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", lineHeight: 1.6 }}>
      {parts.map((p, i) =>
        p.type === "plain" ? (
          <span key={i}>{p.text}</span>
        ) : (
          <mark
            key={i}
            className={p.spanType === "fake" ? "highlightFake" : "highlightReal"}
            title={p.keyword ? `Model keyword: ${p.keyword}` : ""}
          >
            {p.text}
          </mark>
        )
      )}
    </div>
  );
}

function WhySentence({ verdict, whySentence }) {
  if (!whySentence) return null;
  const isFake = verdict === "FAKE NEWS";
  const isUncertain = verdict === "UNCERTAIN";
  const label = isFake ? "Why FAKE?" : isUncertain ? "Why UNCERTAIN?" : "Why REAL?";
  const boxClass = isFake ? "whyFake" : isUncertain ? "whyUncertain" : "whyReal";
  return (
    <div className={`whySentenceBox ${boxClass}`}>
      <div className="whySentenceLabel">{label}</div>
      <div className="whySentenceText">{whySentence}</div>
    </div>
  );
}

function ExplanationBlock({ explanation, analyzedText, verdict }) {
  if (!explanation) return null;

  const summary = explanation.summary || {};
  const humanReasons = explanation.human_reasons || [];
  const style = explanation.writing_style_signals?.signals || [];
  const factWarnings = explanation.fact_check?.warnings || [];

  const fakeDrivers = explanation.model_keyword_evidence?.fake_drivers || [];
  const realDrivers = explanation.model_keyword_evidence?.real_drivers || [];
  const v = verdict || summary?.verdict || "UNKNOWN";
  const confidence = summary?.confidence;
  const narrative = summary?.narrative;
  const fakeKeywordCount = fakeDrivers.length;
  const realKeywordCount = realDrivers.length;
  const modelLeansReal = realKeywordCount >= fakeKeywordCount;
  const whySentence = explanation.why_sentence;
  const highlightedSpans = explanation.highlighted_spans || [];
  const shap = explanation.shap_attribution || {};
  const shapFake = shap.toward_fake || [];
  const shapReal = shap.toward_real || [];

  return (
    <div className="card">
      <div className="cardTitle">Why this verdict was given</div>

      {whySentence ? <WhySentence verdict={v} whySentence={whySentence} /> : null}

      {analyzedText ? (
        <div className="section">
          <div className="sectionLabel">Words that influenced this verdict</div>
          <div className="highlightLegend">
            <span className="legendItem">
              <mark className="highlightFake legendMark" /> Fake-leaning
            </span>
            <span className="legendItem">
              <mark className="highlightReal legendMark" /> Real-leaning
            </span>
          </div>
          <HighlightedText text={analyzedText} spans={highlightedSpans} verdict={v} />
        </div>
      ) : null}

      <div className="section">
        <div className="sectionLabel">Simple explanation</div>
        <div className="plainExplain">
          {narrative ? (
            narrative
          ) : (
            <>
              This article is currently judged as <b>{v}</b>
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

      <div className="section">
        <div className="sectionLabel">SHAP attribution (Logistic Regression)</div>
        {shap.available ? (
          <>
            <p className="smallNote" style={{ marginTop: 0 }}>
              Game-theoretic feature contributions toward fake vs real (LinearExplainer). {shap.note || ""}
            </p>
            <div className="grid2" style={{ marginTop: "10px" }}>
              <div className="miniCard">
                <div className="miniTitle">SHAP → fake (higher risk)</div>
                {shapFake.length ? (
                  <ul className="list">
                    {shapFake.map((row, i) => (
                      <li key={i}>
                        <b>{row.feature}</b>{" "}
                        <span className="muted">
                          ({row.shap > 0 ? "+" : ""}
                          {row.shap})
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="muted">No strong fake-leaning terms in this text.</div>
                )}
              </div>
              <div className="miniCard">
                <div className="miniTitle">SHAP → real (lower risk)</div>
                {shapReal.length ? (
                  <ul className="list">
                    {shapReal.map((row, i) => (
                      <li key={i}>
                        <b>{row.feature}</b>{" "}
                        <span className="muted">({row.shap})</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="muted">No strong real-leaning terms in this text.</div>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="muted">
            {shap.reason ||
              "SHAP is not available. Run `python -m backend.build_shap_background` after training, or retrain so shap_background.joblib is created."}
          </div>
        )}
      </div>
    </div>
  );
}

function ExplainabilityCharts({ result, explanation }) {
  if (!result) return null;
  const isLightTheme =
    typeof document !== "undefined" && document.body.getAttribute("data-theme") === "light";
  const chartLegendColor = isLightTheme ? "#14081f" : "rgba(255,255,255,0.85)";
  const chartTickColor = isLightTheme ? "#3e2860" : "rgba(255,255,255,0.75)";
  const chartGridColor = isLightTheme ? "rgba(20,8,31,0.16)" : "rgba(255,255,255,0.08)";

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
        labels: { color: chartLegendColor },
      },
    },
    scales: {
      x: {
        ticks: { color: chartTickColor },
        grid: { color: chartGridColor },
      },
      y: {
        beginAtZero: true,
        ticks: { color: chartTickColor },
        grid: { color: chartGridColor },
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
                  legend: { labels: { color: chartLegendColor } },
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

const INPUT_TYPES = [
  { id: "text", label: "Text", desc: "Paste article" },
  { id: "url", label: "URL", desc: "Fetch from link" },
  { id: "youtube", label: "YouTube", desc: "Video title & desc" },
  { id: "rss", label: "RSS", desc: "Latest from feed" },
  { id: "file", label: "File", desc: "Upload .txt" },
];

export default function UserDashboard() {
  const [inputType, setInputType] = useState("text");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [rssUrl, setRssUrl] = useState("");
  const [file, setFile] = useState(null);
  const [factCheckMode, setFactCheckMode] = useState("wikipedia");

  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

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
      let res;
      if (inputType === "file" && file) {
        const fd = new FormData();
        fd.append("file", file);
        fd.append("fact_check_mode", factCheckMode);
        res = await api.post("/api/predict", fd);
      } else if (inputType === "url" && url.trim()) {
        res = await api.post("/api/predict", { url: url.trim(), fact_check_mode: factCheckMode });
      } else if (inputType === "youtube" && youtubeUrl.trim()) {
        res = await api.post("/api/predict", { youtube_url: youtubeUrl.trim(), fact_check_mode: factCheckMode });
      } else if (inputType === "rss" && rssUrl.trim()) {
        res = await api.post("/api/predict", { rss_url: rssUrl.trim(), fact_check_mode: factCheckMode });
      } else {
        res = await api.post("/api/predict", { text: text.trim(), fact_check_mode: factCheckMode });
      }
      setResult(res.data);
      setText("");
      setUrl("");
      setYoutubeUrl("");
      setRssUrl("");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
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
          <Link to="/home" className="btnSecondary" style={{ textDecoration: "none", display: "inline-flex", alignItems: "center" }}>
            Home
          </Link>
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
            <p className="inputTypeHint">System supports text, article URL, YouTube video, RSS feed, and .txt upload.</p>
            <div className="inputTypeTabs">
              {INPUT_TYPES.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className={`inputTypeTab ${inputType === t.id ? "active" : ""}`}
                  onClick={() => setInputType(t.id)}
                >
                  <span className="tabLabel">{t.label}</span>
                  <span className="tabDesc">{t.desc}</span>
                </button>
              ))}
            </div>
            <form onSubmit={submit}>
              {inputType === "text" ? (
                <>
                  <label className="label">Article text</label>
                  <textarea
                    className="textarea"
                    rows={8}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Paste the full news text here…"
                  />
                </>
              ) : inputType === "url" ? (
                <>
                  <label className="label">Article URL</label>
                  <input
                    type="url"
                    className="input"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://example.com/article…"
                  />
                  <p className="smallNote">We will fetch the article content from this URL.</p>
                </>
              ) : inputType === "youtube" ? (
                <>
                  <label className="label">YouTube video URL</label>
                  <input
                    type="url"
                    className="input"
                    value={youtubeUrl}
                    onChange={(e) => setYoutubeUrl(e.target.value)}
                    placeholder="https://www.youtube.com/watch?v=…"
                  />
                  <p className="smallNote">
                    We analyze the video <b>title and description</b> via YouTube Data API. Requires YOUTUBE_API_KEY.
                  </p>
                </>
              ) : inputType === "rss" ? (
                <>
                  <label className="label">RSS or Atom feed URL</label>
                  <input
                    type="url"
                    className="input"
                    value={rssUrl}
                    onChange={(e) => setRssUrl(e.target.value)}
                    placeholder="https://feeds.bbci.co.uk/news/rss.xml"
                  />
                  <p className="smallNote">
                    We use the <b>latest</b> item in the feed: fetch its article page when possible, otherwise the feed
                    summary.
                  </p>
                </>
              ) : (
                <>
                  <label className="label">Upload .txt file</label>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".txt"
                    className="fileInput"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                  />
                  {file ? <p className="smallNote">Selected: {file.name}</p> : null}
                </>
              )}

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

              <button
                className="btn"
                disabled={
                  loading ||
                  (inputType === "text" && !text.trim()) ||
                  (inputType === "url" && !url.trim()) ||
                  (inputType === "youtube" && !youtubeUrl.trim()) ||
                  (inputType === "rss" && !rssUrl.trim()) ||
                  (inputType === "file" && !file)
                }
              >
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
              {result?.input_meta?.input_type === "rss" ? (
                <div className="muted" style={{ marginTop: "10px", lineHeight: 1.5 }}>
                  <div className="sectionLabel" style={{ marginBottom: "4px" }}>
                    Source (RSS)
                  </div>
                  {result.input_meta.feed_title ? <div>Feed: {result.input_meta.feed_title}</div> : null}
                  {result.input_meta.item_title ? <div>Item: {result.input_meta.item_title}</div> : null}
                  {result.input_meta.item_link ? (
                    <div>
                      Link:{" "}
                      <a href={result.input_meta.item_link} target="_blank" rel="noopener noreferrer">
                        {result.input_meta.item_link}
                      </a>
                    </div>
                  ) : null}
                  {result.input_meta.text_source ? (
                    <div>Text from: {result.input_meta.text_source === "feed_summary" ? "feed summary" : "article page"}</div>
                  ) : null}
                </div>
              ) : result?.input_meta?.input_type === "youtube" ? (
                <div className="muted" style={{ marginTop: "10px", lineHeight: 1.5 }}>
                  <div className="sectionLabel" style={{ marginBottom: "4px" }}>
                    Source (YouTube)
                  </div>
                  {result.input_meta.video_title ? <div>Title: {result.input_meta.video_title}</div> : null}
                  {result.input_meta.channel_title ? <div>Channel: {result.input_meta.channel_title}</div> : null}
                  {result.input_meta.video_id ? (
                    <div>
                      Video:{" "}
                      <a
                        href={`https://www.youtube.com/watch?v=${result.input_meta.video_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        youtube.com/watch?v={result.input_meta.video_id}
                      </a>
                    </div>
                  ) : null}
                </div>
              ) : null}
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
          <ExplanationBlock
            explanation={result?.explanation}
            analyzedText={result?.analyzed_text}
            verdict={verdict}
          />
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
                          analyzed_text: h.text,
                          input_meta: h.input_meta,
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

