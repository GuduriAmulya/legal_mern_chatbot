const express = require('express');
const router = express.Router();
const auth = require('../middleware/auth');
const chatCtrl = require('../controllers/chatController');

const { 
  listChats, 
  createChat, 
  getChat, 
  addMessage, 
  deleteChat,
  resetChat 
} = chatCtrl;

router.get('/', auth, listChats);
router.post('/', auth, createChat);
router.get('/:id', auth, getChat);
router.post('/:id/messages', auth, addMessage);
router.post('/:id/reset', auth, resetChat);

// Delete chat
router.delete('/:id', auth, deleteChat);

module.exports = router;
