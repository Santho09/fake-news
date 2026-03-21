import React, { useEffect, useMemo, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { api } from "./api/client";

import Login from "./pages/Login.jsx";
import Signup from "./pages/Signup.jsx";
import UserDashboard from "./pages/UserDashboard.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";

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
              <Navigate to="/login" replace />
            )
          }
        />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
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

