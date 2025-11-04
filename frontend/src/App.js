import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import LandingPage from './pages/LandingPage';
import Login from './pages/Login';
import Register from './pages/Register';
import Navbar from './components/Navbar';
import EvaluationDashboard from './pages/EvaluationDashboard';

function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || null);

  // Sync token with localStorage
  useEffect(() => {
    if (token) localStorage.setItem('token', token);
    else localStorage.removeItem('token');
  }, [token]);

  return (
    <BrowserRouter>
      <Navbar token={token} setToken={setToken} />
      
      <Routes>
        {/* Public routes (only accessible when NOT logged in) */}
        <Route 
          path="/" 
          element={!token ? <LandingPage /> : <Navigate to="/dashboard" replace />} 
        />
        <Route 
          path="/login" 
          element={!token ? <Login setToken={setToken} /> : <Navigate to="/dashboard" replace />} 
        />
        <Route 
          path="/register" 
          element={!token ? <Register /> : <Navigate to="/dashboard" replace />} 
        />

        {/* Protected routes (only accessible when logged in) */}
        <Route 
          path="/dashboard" 
          element={token ? <Dashboard token={token} setToken={setToken} /> : <Navigate to="/login" replace />} 
        />
        <Route 
          path="/evaluations" 
          element={token ? <EvaluationDashboard token={token} /> : <Navigate to="/login" replace />} 
        />

        {/* Fallback for unknown routes */}
        <Route path="*" element={<Navigate to={token ? "/dashboard" : "/"} replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
