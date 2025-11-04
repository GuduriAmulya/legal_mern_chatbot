import React, { useState, useEffect } from 'react';
import { get, post, del } from '../services/api';
import ChatList from '../components/ChatList';
import ChatWindow from '../components/ChatWindow';

export default function Dashboard({ token, setToken }) {
  const [chats, setChats] = useState([]);
  const [active, setActive] = useState(null);
  const [loading, setLoading] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);

  // Load chats from server
  async function loadChats() {
    setLoading(true);
    try {
      const data = await get('/chats', token);
      if (Array.isArray(data)) {
        setChats(data);
        // Set active only if none selected
        setActive(prev => {
          if (prev && data.find(c => c._id === prev._id)) {
            return prev; // keep existing active if still present
          }
          return data.length ? data[0] : null;
        });
      } else {
        console.warn('Unexpected chats response', data);
        setChats([]);
        setActive(null);
      }
    } catch (err) {
      console.error('Error loading chats:', err);
      // api helper may have already cleared token on 401 and reloaded
      alert(err.message || 'Failed to load chats');
      setChats([]);
      setActive(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadChats();
  }, [token]); // reload when token changes

  const createChat = async () => {
    if (loading) return;
    setLoading(true);
    try {
      const chatNumber = chats.length + 1;  // ← Count existing chats
      const chat = await post('/chats', { title: `Chat ${chatNumber}` }, token);
      setChats([chat, ...chats]);
      setActiveChat(chat);
    } catch (err) {
      console.error('Create chat error', err);
      alert(err.message || 'Failed to create chat');
    }
  };

  // New delete handler
  async function deleteChat(chatId) {
    if (!window.confirm('Delete this chat? This action cannot be undone.')) return;
    try {
      await del(`/chats/${chatId}`, token);
      // remove from state
      setChats(prev => prev.filter(c => c._id !== chatId));
      setActive(prev => {
        if (prev && prev._id === chatId) {
          // choose first remaining or null
          const remaining = chats.filter(c => c._id !== chatId);
          return remaining.length ? remaining[0] : null;
        }
        return prev;
      });
    } catch (err) {
      console.error('Delete chat error', err);
      alert(err.message || 'Failed to delete chat');
    }
  }

  return (
    <div className="dashboard layout">
      <div className={`sidebar-panel ${panelOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <h2>Chats</h2>
          <div className="sidebar-controls">
            <button className="small" onClick={createChat}>+ New</button>
            <button className="small" onClick={() => setPanelOpen(false)}>Hide</button>
          </div>
        </div>
        <div className="sidebar-body">
          {loading ? <div>Loading...</div> : <ChatList chats={chats} setActive={setActive} onDelete={deleteChat} />}
        </div>
      </div>

      <main className="main-panel">
        <div className="main-header">
          <button className="small" onClick={() => setPanelOpen(!panelOpen)}>
            {panelOpen ? 'Hide Chats' : 'Show Chats'}
          </button>
          <div className="spacer" />
        </div>

        <div className="main-content">
          {active ? <ChatWindow chat={active} token={token} refreshChats={loadChats} /> : <div className="empty">Select or create a chat</div>}
        </div>
      </main>
    </div>
  );
}
