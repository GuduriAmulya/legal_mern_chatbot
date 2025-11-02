import React, { useState, useEffect } from 'react';
import { get, post } from '../services/api';

// Helper to format assistant responses: convert lists, bold, line breaks
function formatAssistantResponse(text) {
  if (!text) return text;
  
  // Replace double asterisks for bold (Markdown-like **text**)
  let formatted = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  
  // Remove newline immediately after colon (e.g., "Rights:\n\n- item" → "Rights:\n- item")
  formatted = formatted.replace(/:\s*\n+/g, ':\n');
  
  // Collapse multiple consecutive newlines into single newline
  formatted = formatted.replace(/\n\s*\n/g, '\n');
  
  // Split by actual newlines in the text (preserves LLM formatting)
  const lines = formatted.split('\n');
  
  return lines.map((line, i) => {
    return (
      <React.Fragment key={i}>
        <span dangerouslySetInnerHTML={{ __html: line }} />
        {i < lines.length - 1 && <br />}
      </React.Fragment>
    );
  });
}

export default function ChatWindow({ chat, token, refreshChats }) {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState('');
  const [enableEval, setEnableEval] = useState(false);

  const load = async () => {
    const data = await get(`/chats/${chat._id}`, token);
    setMessages(data.messages || []);
  };

  useEffect(() => { load(); }, [chat._id]);

  const send = async (e) => {
    e.preventDefault();
    if (!text) return;
    const res = await post(`/chats/${chat._id}/messages`, { 
      text, 
      evaluate: enableEval  // ← Ensure this is sent
    }, token);
    setMessages(res.conversation.messages);
    setText('');
    if (refreshChats) refreshChats();
  };

  const clearHistory = async () => {
    if (!window.confirm('Clear all messages in this chat?')) return;
    
    try {
      // Call backend reset endpoint (which forwards to rag_service)
      await post(`/chats/${chat._id}/reset`, {}, token);
      setMessages([]);
    } catch (error) {
      console.error('Failed to clear history:', error);
      alert('Failed to clear chat history. Please try again.');
    }
  };

  return (
    <div className="chat-window">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>{chat.title}</h3>
        <button className="small" onClick={clearHistory}>🗑️ Clear</button>
      </div>
      
      <label style={{ fontSize: 13, marginBottom: 8, display: 'block' }}>
        <input type="checkbox" checked={enableEval} onChange={e => setEnableEval(e.target.checked)} />
        {' '}Enable LLM-as-a-Judge Evaluation
      </label>

      <div className="messages">
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.sender}`}>
            <div className="text">
              {m.sender === 'assistant' ? formatAssistantResponse(m.text) : m.text}
            </div>
            <div className="time">{new Date(m.createdAt).toLocaleTimeString()}</div>
            {m.sender === 'assistant' && m.debug && (
              <details style={{ marginTop: 6 }}>
                <summary style={{ cursor: 'pointer', color: '#0f1724' }}>🔍 Debug</summary>
                <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, color: '#334155', marginTop: 8 }}>
                  
                  {/* ADD: Token usage info */}
                  {m.debug.tokens_estimate && (
                    <>
                      <strong>Token Usage:</strong>
                      <div style={{ fontSize: 12, marginTop: 4 }}>
                        • Conversation: {m.debug.tokens_estimate.conversation} tokens<br/>
                        • Retrieved Docs: {m.debug.tokens_estimate.retrieved} tokens<br/>
                        • Query: {m.debug.tokens_estimate.query} tokens<br/>
                        • Total: {m.debug.tokens_estimate.conversation + m.debug.tokens_estimate.retrieved + m.debug.tokens_estimate.query} / {m.debug.tokens_estimate.total_context_allowed}
                      </div>
                      <hr />
                    </>
                  )}
                  
                  {/* ADD: Query rewriting info */}
                  {m.debug.query_rewritten && (
                    <>
                      <strong>Query Rewritten:</strong>
                      <div style={{ fontSize: 12, marginTop: 4 }}>
                        Original: "{m.debug.original_query}"<br/>
                        Rewritten: "{m.debug.rewritten_query}"
                      </div>
                      <hr />
                    </>
                  )}
                  
                  {m.debug.conversation_context_preview && (
                    <>
                      <strong>Conversation context (preview):</strong>
                      <div>{m.debug.conversation_context_preview}</div>
                      <hr />
                    </>
                  )}
                  {m.debug.retrieved_context_preview && (
                    <>
                      <strong>Retrieved context (preview):</strong>
                      <div>{m.debug.retrieved_context_preview}</div>
                      <hr />
                    </>
                  )}
                </div>
              </details>
            )}
            
            {/* NEW: Show LLM-as-a-Judge evaluation if available */}
            {m.sender === 'assistant' && m.evaluation && (
              <details style={{ marginTop: 6, borderTop: '1px solid #e5e7eb', paddingTop: 8 }}>
                <summary style={{ cursor: 'pointer', color: '#1e6fb8', fontWeight: 600 }}>
                  ⚖️ LLM Judge Evaluation
                </summary>
                <div style={{ marginTop: 8, fontSize: 13 }}>
                  {m.evaluation.evaluation && (
                    <>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8, marginBottom: 12 }}>
                        {m.evaluation.evaluation.factual_accuracy && (
                          <div style={{ padding: 8, background: '#f0f9ff', borderRadius: 6 }}>
                            <strong>Factual Accuracy:</strong> {m.evaluation.evaluation.factual_accuracy.score}/5
                            <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                              {m.evaluation.evaluation.factual_accuracy.reason}
                            </div>
                          </div>
                        )}
                        {m.evaluation.evaluation.legal_reasoning && (
                          <div style={{ padding: 8, background: '#f0f9ff', borderRadius: 6 }}>
                            <strong>Legal Reasoning:</strong> {m.evaluation.evaluation.legal_reasoning.score}/5
                            <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                              {m.evaluation.evaluation.legal_reasoning.reason}
                            </div>
                          </div>
                        )}
                        {m.evaluation.evaluation.citation_quality && (
                          <div style={{ padding: 8, background: '#f0f9ff', borderRadius: 6 }}>
                            <strong>Citation Quality:</strong> {m.evaluation.evaluation.citation_quality.score}/5
                            <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                              {m.evaluation.evaluation.citation_quality.reason}
                            </div>
                          </div>
                        )}
                        {m.evaluation.evaluation.clarity && (
                          <div style={{ padding: 8, background: '#f0f9ff', borderRadius: 6 }}>
                            <strong>Clarity:</strong> {m.evaluation.evaluation.clarity.score}/5
                            <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                              {m.evaluation.evaluation.clarity.reason}
                            </div>
                          </div>
                        )}
                        {m.evaluation.evaluation.completeness && (
                          <div style={{ padding: 8, background: '#f0f9ff', borderRadius: 6 }}>
                            <strong>Completeness:</strong> {m.evaluation.evaluation.completeness.score}/5
                            <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                              {m.evaluation.evaluation.completeness.reason}
                            </div>
                          </div>
                        )}
                      </div>
                      
                      {m.evaluation.evaluation.overall_score && (
                        <div style={{ padding: 12, background: '#1e6fb8', color: 'white', borderRadius: 8, textAlign: 'center' }}>
                          <strong>Overall Score: {m.evaluation.evaluation.overall_score}/5.0</strong>
                        </div>
                      )}
                      
                      {m.evaluation.evaluation.summary && (
                        <div style={{ marginTop: 12, padding: 10, background: '#f8fafc', borderRadius: 6, fontSize: 13 }}>
                          <strong>Summary:</strong> {m.evaluation.evaluation.summary}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </details>
            )}
          </div>
        ))}
      </div>

      <form onSubmit={send} className="composer">
        <input className="composer-input" value={text} onChange={e=>setText(e.target.value)} placeholder="Ask your legal question..." />
        <button className="composer-btn" type="submit">Send</button>
      </form>
    </div>
  );
}
