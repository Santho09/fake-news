import React, { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";

export default function ForgotPassword() {
  const [searchParams] = useSearchParams();
  const token = (searchParams.get("token") || "").trim();
  const isResetMode = Boolean(token);

  const [email, setEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const requestResetLink = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      const res = await api.post("/api/auth/forgot-password", { email: email.trim() });
      setSuccess(res.data?.message || "If this email exists, a reset link has been sent.");
    } catch (err) {
      setError(err?.response?.data?.error || "Failed to request reset link");
    } finally {
      setLoading(false);
    }
  };

  const submitNewPassword = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      const res = await api.post("/api/auth/reset-password", {
        token,
        new_password: newPassword,
      });
      setSuccess(res.data?.message || "Password reset successful. Please sign in.");
    } catch (err) {
      setError(err?.response?.data?.error || "Failed to reset password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="authCard">
        <div className="authBackRow">
          <Link to="/login" className="authBackLink">
            ← Back to Login
          </Link>
        </div>
        <h1 className="title">{isResetMode ? "Set New Password" : "Forgot Password"}</h1>
        <p className="subtitle">
          {isResetMode
            ? "Enter a new password for your account."
            : "Enter your account email and we will send a reset link."}
        </p>

        <form className="form" onSubmit={isResetMode ? submitNewPassword : requestResetLink}>
          {!isResetMode ? (
            <>
              <label className="label">Email</label>
              <input
                className="input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="e.g., user@example.com"
                type="email"
                autoComplete="email"
              />
            </>
          ) : (
            <>
              <label className="label">New Password</label>
              <input
                className="input"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="At least 6 characters"
                type="password"
                autoComplete="new-password"
              />
              <label className="label">Confirm Password</label>
              <input
                className="input"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Repeat your password"
                type="password"
                autoComplete="new-password"
              />
            </>
          )}

          {error ? <div className="errorBox">{error}</div> : null}
          {success ? <div className="successBox">{success}</div> : null}

          <button
            className="btn"
            type="submit"
            disabled={loading || (!isResetMode && !email.trim()) || (isResetMode && !newPassword)}
          >
            {loading
              ? isResetMode
                ? "Updating..."
                : "Sending..."
              : isResetMode
              ? "Update Password"
              : "Send Reset Link"}
          </button>
        </form>
      </div>
    </div>
  );
}
