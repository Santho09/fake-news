import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.post("/api/auth/login", { username, password });
      const data = res.data;
      if (!data.success) {
        setError(data.error || "Login failed");
        return;
      }
      localStorage.setItem("token", data.token);
      localStorage.setItem("role", data.role);
      navigate(data.role === "admin" ? "/admin" : "/user");
    } catch (err) {
      setError(err?.response?.data?.error || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="authCard">
        <div className="authBackRow">
          <Link to="/home" className="authBackLink">
            ← Home
          </Link>
        </div>
        <h1 className="title">NewsVeritas</h1>
        <p className="subtitle">Sign in to verify news with human-readable clarity.</p>

        <form className="form" onSubmit={onSubmit}>
          <label className="label">Username</label>
          <input
            className="input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="e.g., admin1"
            autoComplete="username"
          />

          <label className="label">Password</label>
          <input
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Your password"
            type="password"
            autoComplete="current-password"
          />

          {error ? <div className="errorBox">{error}</div> : null}

          <button className="btn" type="submit" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
          </button>

          <div className="hint">
            No account? <a href="/signup">Create one</a>
          </div>
          <div className="hint">
            Forgot password? <a href="/forgot-password">Reset it</a>
          </div>
        </form>
      </div>
    </div>
  );
}

