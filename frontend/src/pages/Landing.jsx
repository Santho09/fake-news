import React from "react";
import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <div className="lp">
      <div className="lpBg" />
      <nav className="lpNav">
        <div className="lpNavLeft">
          <div className="lpLogo">
            <span className="lpLogoMark">N</span>
            <div>
              <div className="lpLogoName">NewsVeritas</div>
              <div className="lpLogoSub">AI-powered fake news detection</div>
            </div>
          </div>
          <span className="lpBadge">AI Powered</span>
        </div>
        <div className="lpNavRight">
          <Link to="/login" className="lpBtn lpBtnGhost">
            Login
          </Link>
          <Link to="/signup" className="lpBtn lpBtnPrimary">
            Sign Up
          </Link>
        </div>
      </nav>

      <section className="lpHero">
        <div className="lpHeroInner">
          <div className="lpHeroLeft">
            <span className="lpLabel">INTELLIGENT NEWS VERIFICATION</span>
            <h1 className="lpHeroTitle">Analyze, verify, and trust your news.</h1>
            <p className="lpHeroHighlight">AI-powered fake news detection</p>
            <p className="lpHeroDesc">
              NewsVeritas combines machine learning, fact-checking, and explainable AI to help you
              understand whether news content is real or fake.
            </p>
            <div className="lpHeroActions">
              <Link to="/signup" className="lpBtn lpBtnPrimary lpBtnLg">
                Analyze News
              </Link>
              <Link to="/login" className="lpBtn lpBtnSecondary lpBtnLg">
                View Demo
              </Link>
            </div>
            <div className="lpHeroTags">
              <span className="lpTag">ML Ensemble</span>
              <span className="lpTag">Fact-Checked</span>
              <span className="lpTag">Explainable AI</span>
            </div>
          </div>
          <div className="lpHeroRight">
            <div className="lpFloatingCards">
              <div className="lpFloatCard lpFloat1">
                <span className="lpFloatLabel">Fake News Detected</span>
                <span className="lpFloatVal">Analyzed</span>
              </div>
              <div className="lpFloatCard lpFloat2">
                <span className="lpFloatLabel">Confidence</span>
                <span className="lpFloatVal">82%</span>
              </div>
              <div className="lpFloatCard lpFloat3">
                <span className="lpFloatLabel">Verified Sources</span>
                <span className="lpFloatVal">Found</span>
              </div>
              <div className="lpFloatCard lpFloat4">
                <span className="lpFloatLabel">Explainability</span>
                <span className="lpFloatVal">Insights</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="lpSection">
        <h2 className="lpSectionTitle">What NewsVeritas Delivers</h2>
        <div className="lpFeatureGrid">
          <div className="lpFeatureCard">
            <div className="lpFeatureIcon">🤖</div>
            <h3 className="lpFeatureTitle">AI Detection</h3>
            <p className="lpFeatureDesc">TF-IDF + Logistic Regression, Random Forest, SVM, Naive Bayes</p>
          </div>
          <div className="lpFeatureCard">
            <div className="lpFeatureIcon">✓</div>
            <h3 className="lpFeatureTitle">Fact Checking</h3>
            <p className="lpFeatureDesc">Wikipedia + Google Fact Check API</p>
          </div>
          <div className="lpFeatureCard">
            <div className="lpFeatureIcon">📊</div>
            <h3 className="lpFeatureTitle">Explainability</h3>
            <p className="lpFeatureDesc">SHAP + keyword highlights + why-sentence reasoning</p>
          </div>
          <div className="lpFeatureCard">
            <div className="lpFeatureIcon">📥</div>
            <h3 className="lpFeatureTitle">Multi-source Input</h3>
            <p className="lpFeatureDesc">Text, URL, YouTube, RSS, File upload</p>
          </div>
        </div>
      </section>

      <section className="lpSection">
        <h2 className="lpSectionTitle">Core Capabilities</h2>
        <div className="lpCapGrid">
          <div className="lpCapCard">
            <h3 className="lpCapTitle">Upload & Analyze</h3>
            <p className="lpCapDesc">Paste text, paste links, or upload files. Multiple input formats for your workflow.</p>
          </div>
          <div className="lpCapCard">
            <h3 className="lpCapTitle">Smart Prediction</h3>
            <p className="lpCapDesc">Ensemble-based decision: FAKE, REAL, or UNCERTAIN with confidence scores.</p>
          </div>
          <div className="lpCapCard">
            <h3 className="lpCapTitle">Explain & Verify</h3>
            <p className="lpCapDesc">Clear reasoning, fact-check results, and highlighted evidence for every verdict.</p>
          </div>
        </div>
      </section>

      <section className="lpSection">
        <h2 className="lpSectionTitle">Dashboard Preview</h2>
        <div className="lpPreviewCard">
          <div className="lpPreviewInput">
            <span className="lpPreviewPlaceholder">Paste article or paste URL…</span>
          </div>
          <div className="lpPreviewOutput">
            <div className="lpPreviewRow">
              <span className="lpPreviewBadge lpPreviewFake">FAKE</span>
              <span className="lpPreviewConf">Confidence: 78%</span>
            </div>
            <p className="lpPreviewExplain">
              This news is predicted as FAKE because it contains exaggerated claims and lacks verifiable entities.
            </p>
            <div className="lpPreviewBars">
              <div className="lpPreviewBar">
                <span>Fake</span>
                <div className="lpBarTrack"><div className="lpBarFill lpBarFake" style={{ width: "78%" }} /></div>
              </div>
              <div className="lpPreviewBar">
                <span>Real</span>
                <div className="lpBarTrack"><div className="lpBarFill lpBarReal" style={{ width: "22%" }} /></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer className="lpFooter">
        <div className="lpFooterLogo">NewsVeritas</div>
        <p className="lpFooterTagline">Built for AI-powered misinformation detection</p>
      </footer>
    </div>
  );
}
