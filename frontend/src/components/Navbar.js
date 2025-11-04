import React from 'react';
import { Link, useNavigate } from 'react-router-dom';

export default function Navbar({ token, setToken }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');     // ← NEW LINE ADDED
    setToken(null);
    navigate('/'); // Redirect to home after logout
  };

  // Helper function to get user name
  const getUserName = () => {
    try {
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      return user.name || user.email || 'User';
    } catch (e) {
      return 'User';
    }
  };

  return (
    <nav className="site-nav">
      <div className="nav-inner">
        <div className="brand">Legal RAG Chatbot</div>
        <div className="nav-actions">
          {!token ? (
            <>
              <Link to="/" className="nav-link">Home</Link>
              <Link to="/login" className="nav-link">Login</Link>
              <Link to="/register" className="nav-link">Register</Link>
            </>
          ) : (
            <>
              <p>Hello {getUserName()}</p>
              <Link to="/evaluations" className="nav-link">📊 Evaluations</Link>
              <button className="nav-cta" onClick={handleLogout}>Logout</button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
