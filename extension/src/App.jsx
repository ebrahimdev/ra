import { useState } from 'react';

function App() {
  const [status, setStatus] = useState(null);

  const handleClick = () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const url = tabs[0].url;

      fetch('http://localhost:8001/api/v1/ingest_paper', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, user_id: 'user_123' })
      })
        .then(res => res.json())
        .then(() => setStatus('✅ Saved!'))
        .catch(() => setStatus('❌ Failed to save.'));
    });
  };

  return (
    <div style={{ padding: 20, width: 200 }}>
      <button onClick={handleClick}>Save this paper</button>
      {status && <p>{status}</p>}
    </div>
  );
}

export default App;
