import React, { useState, useEffect } from 'react';
import { get, post, del } from '../services/api';
import ChatList from '../components/ChatList';
import ChatWindow from '../components/ChatWindow';

export default function Dashboard({ token, setToken }) {
  const [chats, setChats] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);

  // Load user from localStorage on mount
  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (e) {
        console.error('Failed to parse user:', e);
      }
    }
  }, []);

  // Load chats from server
  async function loadChats() {
    setLoading(true);
    try {
      const data = await get('/chats', token);
      setChats(data);
      // Auto-select first chat if none selected
      if (data.length > 0 && !activeChat) {
        setActiveChat(data[0]);
      }
    } catch (err) {
      console.error('Load chats error', err);
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
    } finally {
      setLoading(false);
    }
  };

  const deleteChat = async (id) => {
    if (!window.confirm('Delete this chat? This action cannot be undone.')) return;
    try {
      await del(`/chats/${id}`, token);
      const newChats = chats.filter(c => c._id !== id);
      setChats(newChats);
      
      // If deleted chat was active, switch to another
      if (activeChat && activeChat._id === id) {
        setActiveChat(newChats.length > 0 ? newChats[0] : null);
      }
    } catch (err) {
      console.error('Delete chat error', err);
      alert(err.message || 'Failed to delete chat');
    }
  };

  return (
    <div className="dashboard">
      {/* {user && (
        <div className="dashboard-header">
          <h3>Welcome back, {user.name || user.email}!</h3>
        </div>
      )} */}
      
      <div className="dashboard-content">
        <div className="sidebar">
          <button className="new-chat-btn" onClick={createChat} disabled={loading}>
            + New Chat
          </button>
          {loading ? (
            <div style={{ padding: 16, color: '#64748b' }}>Loading...</div>
          ) : (
            <ChatList chats={chats} setActive={setActiveChat} onDelete={deleteChat} />
          )}
        </div>

        <div className="main">
          {activeChat ? (
            <ChatWindow chat={activeChat} token={token} refreshChats={loadChats} />
          ) : (
            <div className="no-chat">
              {loading ? 'Loading...' : 'Select a chat or create a new one'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
