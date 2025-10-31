import React, { useState, useEffect } from 'react';
import Dashboard from './pages/Dashboard';
import LandingPage from './pages/LandingPage';
import Login from './pages/Login';
import Register from './pages/Register';
import Navbar from './components/Navbar';
import EvaluationDashboard from './pages/EvaluationDashboard';

function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [route, setRoute] = useState(window.location.hash.replace('#', '') || '/');
  const [showDashboard, setShowDashboard] = useState(false);

  useEffect(() => {
    function onHashChange() {
      setRoute(window.location.hash.replace('#', '') || '/');
    }
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  useEffect(() => {
    if (token) localStorage.setItem('token', token);
    else localStorage.removeItem('token');
  }, [token]);

  // If logged in, always show dashboard regardless of hash
  if (token && showDashboard) {
    return (
      <>
        <Navbar token={token} setToken={setToken} />
        <button onClick={() => setShowDashboard(false)} style={{ margin: 20 }}>← Back to Chat</button>
        <EvaluationDashboard token={token} />
      </>
    );
  }

  if (token) {
    return (
      <>
        <Navbar token={token} setToken={setToken} />
        <button onClick={() => setShowDashboard(true)} style={{ position: 'fixed', top: 80, right: 20, zIndex: 50 }}>
          📊 Evaluations
        </button>
        <Dashboard token={token} setToken={setToken} />
      </>
    );
  }

  // Not logged in: route between landing, login, register
  return (
    <>
      <Navbar token={token} setToken={setToken} />
      {route === '/login' && <Login setToken={setToken} />}
      {route === '/register' && <Register />}
      {(route === '/' || route === '') && <LandingPage />}
      {/* fallback */}
      {route !== '/' && route !== '/login' && route !== '/register' && <LandingPage />}
    </>
  );
}

export default App;
