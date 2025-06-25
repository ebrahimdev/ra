const root = document.getElementById('chat-root');

root.innerHTML = `
  <style>
    body { font-family: sans-serif; margin: 1em; }
    #output { white-space: pre-wrap; border: 1px solid #ccc; padding: 1em; margin-top: 1em; height: 300px; overflow-y: auto; }
    #input { width: 100%; padding: 0.5em; }
    #send { margin-top: 0.5em; }
  </style>
  <textarea id="input" rows="3" placeholder="Ask the assistant something..."></textarea><br/>
  <button id="send">Send</button>
  <div id="output"></div>
`;

document.getElementById('send').onclick = async () => {
  const query = document.getElementById('input').value;
  const output = document.getElementById('output');
  output.innerText = "Assistant: ";

  const res = await fetch('http://localhost:8000/chat_stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      user_id: "vscode_user",
      chat_history: []
    })
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    output.innerText += decoder.decode(value);
  }
};
