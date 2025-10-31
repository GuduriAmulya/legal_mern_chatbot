import React, { useEffect, useState } from 'react';
import { get } from '../services/api';

export default function EvaluationDashboard({ token }) {
  const [stats, setStats] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [sessionEvals, setSessionEvals] = useState([]);

  useEffect(() => {
    loadStats();
    loadSessions();
  }, []);

  const loadStats = async () => {
    try {
      // Get all conversations with evaluations
      const chats = await get('/chats', token);
      
      let totalEvals = 0;
      let sumScores = { factual: 0, reasoning: 0, citation: 0, clarity: 0, completeness: 0, overall: 0 };
      
      for (const chat of chats) {
        const chatData = await get(`/chats/${chat._id}`, token);
        const evalMessages = chatData.messages.filter(m => m.evaluation);
        
        evalMessages.forEach(m => {
          if (m.evaluation?.evaluation) {
            totalEvals++;
            const e = m.evaluation.evaluation;
            sumScores.factual += e.factual_accuracy?.score || 0;
            sumScores.reasoning += e.legal_reasoning?.score || 0;
            sumScores.citation += e.citation_quality?.score || 0;
            sumScores.clarity += e.clarity?.score || 0;
            sumScores.completeness += e.completeness?.score || 0;
            sumScores.overall += e.overall_score || 0;
          }
        });
      }
      
      setStats({
        total: totalEvals,
        avg: {
          factual: (sumScores.factual / totalEvals).toFixed(2),
          reasoning: (sumScores.reasoning / totalEvals).toFixed(2),
          citation: (sumScores.citation / totalEvals).toFixed(2),
          clarity: (sumScores.clarity / totalEvals).toFixed(2),
          completeness: (sumScores.completeness / totalEvals).toFixed(2),
          overall: (sumScores.overall / totalEvals).toFixed(2)
        }
      });
    } catch (err) {
      console.error(err);
    }
  };

  const loadSessions = async () => {
    const chats = await get('/chats', token);
    setSessions(chats);
  };

  const loadSessionEvals = async (chatId) => {
    const chat = await get(`/chats/${chatId}`, token);
    const evals = chat.messages.filter(m => m.sender === 'assistant' && m.evaluation);
    setSessionEvals(evals);
    setSelectedSession(chatId);
  };

  if (!stats) return <div style={{ padding: 40 }}>Loading...</div>;

  return (
    <div style={{ padding: 40, maxWidth: 1200, margin: '0 auto' }}>
      <h1>⚖️ LLM-as-a-Judge Evaluation Dashboard</h1>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20, marginTop: 20 }}>
        <div style={{ padding: 20, background: '#f0f9ff', borderRadius: 8 }}>
          <h3>Total Evaluations</h3>
          <div style={{ fontSize: 32, fontWeight: 'bold', color: '#1e6fb8' }}>{stats.total}</div>
        </div>
        <div style={{ padding: 20, background: '#f0f9ff', borderRadius: 8 }}>
          <h3>Avg Overall Score</h3>
          <div style={{ fontSize: 32, fontWeight: 'bold', color: '#1e6fb8' }}>{stats.avg.overall}/5.0</div>
        </div>
        <div style={{ padding: 20, background: '#f0f9ff', borderRadius: 8 }}>
          <h3>System Health</h3>
          <div style={{ fontSize: 24, fontWeight: 'bold' }}>
            {stats.avg.overall >= 4 ? '🟢 Excellent' : stats.avg.overall >= 3 ? '🟡 Good' : '🔴 Poor'}
          </div>
        </div>
      </div>

      <h2 style={{ marginTop: 40 }}>Dimension Breakdown</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16, marginTop: 16 }}>
        {[
          { label: 'Factual Accuracy', value: stats.avg.factual },
          { label: 'Legal Reasoning', value: stats.avg.reasoning },
          { label: 'Citation Quality', value: stats.avg.citation },
          { label: 'Clarity', value: stats.avg.clarity },
          { label: 'Completeness', value: stats.avg.completeness }
        ].map(dim => (
          <div key={dim.label} style={{ padding: 16, background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8 }}>
            <div style={{ fontWeight: 600 }}>{dim.label}</div>
            <div style={{ fontSize: 24, color: '#1e6fb8' }}>{dim.value}/5</div>
          </div>
        ))}
      </div>

      <h2 style={{ marginTop: 40 }}>Session Evaluations</h2>
      <select onChange={(e) => loadSessionEvals(e.target.value)} style={{ padding: 8, width: '100%' }}>
        <option>Select a session...</option>
        {sessions.map(s => (
          <option key={s._id} value={s._id}>{s.title}</option>
        ))}
      </select>

      {sessionEvals.length > 0 && (
        <div style={{ marginTop: 20 }}>
          {sessionEvals.map((m, i) => (
            <div key={i} style={{ padding: 16, background: '#f8fafc', borderRadius: 8, marginBottom: 12 }}>
              <strong>Q: {m.text.substring(0, 100)}...</strong>
              {m.evaluation?.evaluation && (
                <div style={{ marginTop: 8, fontSize: 14 }}>
                  Overall: {m.evaluation.evaluation.overall_score}/5 | 
                  Accuracy: {m.evaluation.evaluation.factual_accuracy?.score}/5 | 
                  Reasoning: {m.evaluation.evaluation.legal_reasoning?.score}/5
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
