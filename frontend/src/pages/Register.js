import React, { useState } from 'react';
import { post } from '../services/api';

export default function Register() {
  const [name, setName] = useState('');
  const [email,setEmail] = useState('');
  const [password,setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await post('/auth/register', { name, email, password });
      if (res.message) {
        alert('Registered successfully. Please login.');
        window.location.hash = '#/login';
      } else {
        alert(res.message || 'Registration failed');
      }
    } catch (err) {
      alert(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-panel">
        <div className="auth-brand">
          <h2>Create account</h2>
          <p className="auth-sub">Start secure, document-grounded legal conversations</p>
        </div>

        <form onSubmit={submit} className="auth-form">
          <label className="auth-label">Full name</label>
          <input
            className="auth-input"
            placeholder="Your full name"
            value={name}
            onChange={e=>setName(e.target.value)}
            required
          />

          <label className="auth-label">Email</label>
          <input
            className="auth-input"
            placeholder="you@domain.com"
            value={email}
            onChange={e=>setEmail(e.target.value)}
            required
            type="email"
          />

          <label className="auth-label">Password</label>
          <input
            className="auth-input"
            placeholder="Create a password"
            value={password}
            onChange={e=>setPassword(e.target.value)}
            required
            type="password"
          />

          <div className="auth-actions">
            <button className="auth-submit" type="submit" disabled={loading}>
              {loading ? 'Registering...' : 'Create Account'}
            </button>
            <a className="auth-link" href="#/login">Already have an account?</a>
          </div>
        </form>
      </div>
    </div>
  );
}
