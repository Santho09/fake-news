import React, { useEffect, useMemo, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { api } from "./api/client";

import Login from "./pages/Login.jsx";
import Signup from "./pages/Signup.jsx";
import UserDashboard from "./pages/UserDashboard.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";
import Landing from "./pages/Landing.jsx";
import ForgotPassword from "./pages/ForgotPassword.jsx";

function RequireAuth({ role, children }) {
  const storedRole = localStorage.getItem("role");
  const token = localStorage.getItem("token");
  const allowed = role ? storedRole === role : true;

  if (!token) return <Navigate to="/login" replace />;
  if (role && !allowed) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const location = useLocation();
  const [bootOk, setBootOk] = useState(false);
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem("theme");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  });

  useEffect(() => {
    document.body.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  // Lightweight boot: if token exists, keep app running; backend role comes from stored role.
  useEffect(() => {
    const t = localStorage.getItem("token");
    if (!t) {
      setBootOk(true);
      return;
    }
    // Optionally verify token in background; avoid blocking UI.
    api
      .get("/api/auth/me")
      .then(() => setBootOk(true))
      .catch(() => {
        localStorage.removeItem("token");
        localStorage.removeItem("role");
        setBootOk(true);
      });
  }, []);

  if (!bootOk) {
    return (
      <div className="page">
        <div className="centerCard">Loading…</div>
      </div>
    );
  }

  return (
    <div className="appShell">
      <button
        type="button"
        className="themeToggle"
        onClick={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))}
        aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
        title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      >
        {theme === "dark" ? "Light mode" : "Dark mode"}
      </button>
      <Routes location={location} key={location.pathname}>
        <Route
          path="/"
          element={
            localStorage.getItem("token") ? (
              localStorage.getItem("role") === "admin" ? (
                <Navigate to="/admin" replace />
              ) : (
                <Navigate to="/user" replace />
              )
            ) : (
              <Landing />
            )
          }
        />
        <Route path="/home" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ForgotPassword />} />
        <Route
          path="/user"
          element={
            <RequireAuth role="user">
              <UserDashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/admin"
          element={
            <RequireAuth role="admin">
              <AdminDashboard />
            </RequireAuth>
          }
        />
      </Routes>
    </div>
  );
}

