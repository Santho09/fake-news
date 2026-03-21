import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

export default function Signup() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("user");
  const [adminCode, setAdminCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const payload = {
        username,
        password,
        role,
        admin_code: adminCode,
      };
      const res = await api.post("/api/auth/signup", payload);
      const data = res.data;
      if (!data.success) {
        setError(data.error || "Signup failed");
        return;
      }

      localStorage.setItem("token", data.token);
      localStorage.setItem("role", data.role);
      navigate(data.role === "admin" ? "/admin" : "/user");
    } catch (err) {
      setError(err?.response?.data?.error || "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="authCard">
        <h1 className="title">Create Account</h1>
        <p className="subtitle">Register as user or (optionally) admin.</p>

        <form className="form" onSubmit={submit}>
          <label className="label">Username</label>
          <input
            className="input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="e.g., user01"
            autoComplete="username"
          />

          <label className="label">Password</label>
          <input
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Your password"
            type="password"
            autoComplete="new-password"
          />

          <div className="row">
            <div className="col">
              <label className="label">Account Role</label>
              <select className="input" value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div className="col">
              <label className="label">Admin Code (if admin)</label>
              <input
                className="input"
                value={adminCode}
                onChange={(e) => setAdminCode(e.target.value)}
                placeholder="Required for admin signup"
                type="password"
                autoComplete="one-time-code"
              />
            </div>
          </div>

          {error ? <div className="errorBox">{error}</div> : null}

          <button className="btn" type="submit" disabled={loading}>
            {loading ? "Creating..." : "Create account"}
          </button>

          <div className="hint">
            Already have an account? <a href="/login">Sign in</a>
          </div>
        </form>
      </div>
    </div>
  );
}

