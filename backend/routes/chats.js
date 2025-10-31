const express = require('express');
const router = express.Router();
const auth = require('../middleware/auth');
const chatCtrl = require('../controllers/chatController');

router.get('/', auth, chatCtrl.listChats);
router.post('/', auth, chatCtrl.createChat);
router.get('/:id', auth, chatCtrl.getChat);
router.post('/:id/messages', auth, chatCtrl.addMessage);

// Delete chat
router.delete('/:id', auth, chatCtrl.deleteChat);

module.exports = router;
