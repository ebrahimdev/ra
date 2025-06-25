const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

let chatID = null;

function appendMessage(content, sender) {
  const row = document.createElement('div');
  row.className = 'message-row';

  if (sender === 'assistant') {
    // Add avatar for assistant
    const avatar = document.createElement('div');
    avatar.className = 'assistant-avatar';
    avatar.innerText = '🤖';
    row.appendChild(avatar);
  }

  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${sender}`;
  msgDiv.innerText = content;
  row.appendChild(msgDiv);

  if (sender === 'user') {
    // For user, push message to the right
    row.style.justifyContent = 'flex-end';
  }

  chatContainer.appendChild(row);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function send() {
  const input = userInput.value.trim();
  if (!input) return;

  // Send message to extension
  vscode.postMessage({
    type: 'sendMessage',
    message: input
  });

  userInput.value = '';
  userInput.focus();
}

function clearChat() {
  vscode.postMessage({
    type: 'clearChat'
  });
}

// Handle messages from the extension
window.addEventListener('message', event => {
  const message = event.data;
  switch (message.type) {
    case 'addMessage':
      appendMessage(message.message, message.sender);
      break;
    case 'removeLastMessage':
      const messages = chatContainer.querySelectorAll('.message-row');
      if (messages.length > 0) {
        messages[messages.length - 1].remove();
      }
      break;
    case 'clearChat':
      chatContainer.innerHTML = '';
      appendMessage('Chat cleared. How can I help you?', 'assistant');
      break;
  }
});

userInput.addEventListener('keydown', function (e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    send();
  }
});
sendBtn.addEventListener('click', send);

// Initialize with welcome message
appendMessage('Welcome to Laitex! I can help you execute commands in your terminal. Just describe what you want to do.', 'assistant');
