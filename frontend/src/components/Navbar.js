import React from 'react';

export default function Navbar({ token, setToken }) {
  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    window.location.hash = '/';
  };

  return (
    <nav className="site-nav">
      <div className="nav-inner">
        <div className="brand">Legal RAG Chatbot</div>
        <div className="nav-actions">
          {!token ? (
            <>
              <a href="#/" className="nav-link">Home</a>
              <a href="#/login" className="nav-link">Login</a>
              <a href="#/register" className="nav-link">Register</a>
            </>
          ) : (
            <>
              <button className="nav-cta" onClick={handleLogout}>Logout</button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
