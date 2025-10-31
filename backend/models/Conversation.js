const mongoose = require('mongoose');

const MessageSchema = new mongoose.Schema({
  sender: { type: String, enum: ['user','assistant'], required: true },
  text: { type: String, required: true },
  createdAt: { type: Date, default: Date.now },
  debug: { type: Object, default: null }, // optional debug info
  evaluation: { type: Object, default: null }  // ← Add this field
});

const ConversationSchema = new mongoose.Schema({
  userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  title: { type: String, default: 'New Chat' },
  ragSessionId: { type: String, default: null }, // <-- new field
  messages: [MessageSchema],
  createdAt: { type: Date, default: Date.now }
});

module.exports = mongoose.model('Conversation', ConversationSchema);
