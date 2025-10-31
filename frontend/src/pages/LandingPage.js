import React from 'react';

export default function LandingPage() {
  return (
    <div className="landing-root">
      <header className="hero">
        <div className="hero-inner">
          <h1>Legal RAG Chatbot</h1>
          <p className="subtitle">
            Multi-turn legal assistant grounded in your documents. Fast retrieval, context-aware responses, and evaluation tools for high-quality legal help.
          </p>
          <div className="hero-actions">
            <a href="#/login" className="btn btn-primary">Login</a>
            <a href="#/register" className="btn btn-secondary">Register</a>
          </div>
        </div>
      </header>

      <section id="features" className="features">
        <div className="feature">
          <h3>Document-grounded answers</h3>
          <p>Upload legal PDFs, retrieve relevant passages, and get answers backed by sources.</p>
        </div>
        <div className="feature">
          <h3>Multi-turn conversations</h3>
          <p>Maintain session-based history for follow-up questions and case-building.</p>
        </div>
        <div className="feature">
          <h3>LLM-as-a-Judge</h3>
          <p>Automated multi-dimensional evaluation for response quality and citations.</p>
        </div>
      </section>

      <footer id="contact" className="landing-footer">
        <div>© {new Date().getFullYear()} Legal RAG Chatbot — Professional legal assistant</div>
      </footer>
    </div>
  );
}
