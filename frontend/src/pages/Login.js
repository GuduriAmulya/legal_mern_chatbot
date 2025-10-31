import React, { useState } from 'react';
import { post } from '../services/api';

export default function Login({ setToken }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await post('/auth/login', { email, password });
      if (res.token) {
        setToken(res.token);
        window.location.hash = '/';
      } else {
        alert(res.message || 'Login failed');
      }
    } catch (err) {
      alert(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-panel">
        <div className="auth-brand">
          <h2>Welcome back</h2>
          <p className="auth-sub">Sign in to access your legal chats and documents</p>
        </div>

        <form onSubmit={submit} className="auth-form">
          <label className="auth-label">Email</label>
          <input
            className="auth-input"
            placeholder="you@domain.com"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            type="email"
          />

          <label className="auth-label">Password</label>
          <input
            className="auth-input"
            placeholder="Your password"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />

          <div className="auth-actions">
            <button className="auth-submit" type="submit" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
            <a className="auth-link" href="#/register">Create account</a>
          </div>
        </form>
      </div>
    </div>
  );
}
