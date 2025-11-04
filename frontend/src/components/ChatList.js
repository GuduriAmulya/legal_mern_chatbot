import React from 'react';

export default function ChatList({ chats, setActive, onDelete }) {
  if (!Array.isArray(chats)) {
    return <div>No chats available.</div>;
  }

  if (chats.length === 0) {
    return <div>No chats yet. Create a new chat.</div>;
  }
  return (
    <div>
      {chats.map((c, index) => (
        <div key={c._id} className="chat-item" onClick={() => setActive(c)}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <strong>
              {c.title === 'New Chat' ? `Chat ${chats.length - index}` : c.title}
            </strong>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className="small"
                title="Delete chat"
                onClick={e => {
                  e.stopPropagation();
                  if (onDelete) onDelete(c._id);
                }}
              >
                🗑️
              </button>
            </div>
          </div>
          <div className="meta">{new Date(c.createdAt).toLocaleString()}</div>
        </div>
      ))}
    </div>
  );
}
