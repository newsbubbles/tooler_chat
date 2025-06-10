import React from "react";
import { Navigate } from "react-router-dom";
import { useAuthStore } from "../contexts/authStore";

export default function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuthStore();

  if (!isAuthenticated) {
    // Redirect to the login page if the user is not authenticated
    return <Navigate to="/login" replace />;
  }

  return children;
}
